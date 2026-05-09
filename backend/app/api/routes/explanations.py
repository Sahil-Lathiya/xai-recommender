import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.db.models import Explanation, Product, Recommendation, UserInteraction
from app.ml.llm_explainer import llm_explainer
from app.ml.xai_engine import FEATURE_LABELS, xai_engine
from app.schemas.schemas import (
    ExplanationResponse,
    FeatureContribution,
    GlobalFeatureImportanceResponse,
    GlobalFeatureItem,
    ProductResponse,
    SHAPValues,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/explain/{recommendation_id}",
    response_model=ExplanationResponse,
)
async def get_explanation(
    recommendation_id: uuid.UUID,
    db: DBSession,
) -> ExplanationResponse:
    # Fetch recommendation + product in one query
    result = await db.execute(
        select(Recommendation, Product)
        .join(Product, Recommendation.product_id == Product.id)
        .where(Recommendation.id == recommendation_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found. Request recommendations first.",
        )

    rec, product = row

    # Extract stored feature vector + pre-computed SHAP (saved when recommendation was made)
    stored = rec.shap_values or {}
    feature_vector: list[float] = stored.get(
        "feature_vector",
        [3.5, 5.0, float(product.rating), float(product.review_count), 0.0, 0.5, 0.5, 0.5],
    )
    shap_result: dict = stored.get("shap_result") or xai_engine.explain(
        feature_vector, str(recommendation_id)
    )

    # Check if LLM explanation already exists in DB
    existing_exp = await db.execute(
        select(Explanation).where(Explanation.recommendation_id == recommendation_id)
    )
    existing = existing_exp.scalar_one_or_none()

    if existing:
        llm_text = existing.llm_explanation
        counterfactual = existing.counterfactual or shap_result.get("counterfactual", "")
    else:
        # Build user summary from interaction history
        stats_result = await db.execute(
            select(
                func.avg(UserInteraction.rating).label("avg_rating"),
                func.count(UserInteraction.id).label("cnt"),
            ).where(UserInteraction.user_id == rec.user_id)
        )
        stats_row = stats_result.one_or_none()
        avg_rating = float(stats_row.avg_rating) if stats_row and stats_row.avg_rating else 3.5
        review_count_user = int(stats_row.cnt) if stats_row and stats_row.cnt else 0

        # Get user's favourite category for summary
        fav_cat_result = await db.execute(
            select(Product.category, func.count().label("cnt"))
            .join(UserInteraction, UserInteraction.product_id == Product.id)
            .where(UserInteraction.user_id == rec.user_id)
            .group_by(Product.category)
            .order_by(func.count().desc())
            .limit(1)
        )
        fav_cat_row = fav_cat_result.first()
        favourite_category = fav_cat_row[0] if fav_cat_row else None

        user_summary = await llm_explainer.generate_user_summary(
            favourite_category=favourite_category,
            avg_rating=avg_rating,
            review_count=review_count_user,
        )

        top_3 = shap_result.get("top_3_reasons", [])
        llm_text = await llm_explainer.explain(
            product_name=product.name,
            price=product.price,
            rating=product.rating,
            review_count=product.review_count,
            top_3_reasons=top_3,
            user_summary=user_summary,
            product_id=str(product.id),
        )
        counterfactual = shap_result.get("counterfactual", "")

        # Persist explanation
        try:
            new_exp = Explanation(
                recommendation_id=recommendation_id,
                shap_json=shap_result,
                llm_explanation=llm_text,
                counterfactual=counterfactual,
            )
            db.add(new_exp)
            await db.commit()
        except Exception as exc:
            logger.warning("Explanation persist failed: %s", exc)
            await db.rollback()

    # Build Pydantic response
    contributions_raw = shap_result.get("feature_contributions", [])
    feature_contributions = [
        FeatureContribution(
            feature=c["feature"],
            raw_value=float(c["raw_value"]),
            shap_value=float(c["shap_value"]),
            direction=c["direction"],
            human_label=FEATURE_LABELS.get(c["feature"], c["human_label"]),
        )
        for c in contributions_raw
    ]

    return ExplanationResponse(
        recommendation_id=recommendation_id,
        product=ProductResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=product.price,
            rating=product.rating,
            review_count=product.review_count,
            image_url=product.image_url,
            amazon_url=product.amazon_url,
        ),
        shap_values=SHAPValues(
            base_value=float(shap_result.get("base_value", 0.5)),
            feature_contributions=feature_contributions,
            top_3_reasons=shap_result.get("top_3_reasons", []),
        ),
        llm_explanation=llm_text,
        counterfactual=counterfactual,
        confidence_score=int(shap_result.get("confidence_score", 65)),
        powered_by="XGBoost + SHAP + GPT-4o-mini",
    )


@router.get(
    "/explain/global/feature-importance",
    response_model=GlobalFeatureImportanceResponse,
)
async def get_global_feature_importance() -> GlobalFeatureImportanceResponse:
    features_data = xai_engine.global_importance()

    features = [
        GlobalFeatureItem(
            feature_name=f["feature_name"],
            importance_score=f["importance_score"],
            rank=f["rank"],
            description=f["description"],
        )
        for f in features_data
    ]

    cached_until = datetime.now(timezone.utc) + timedelta(hours=24)

    return GlobalFeatureImportanceResponse(
        features=features,
        cached_until=cached_until,
    )
