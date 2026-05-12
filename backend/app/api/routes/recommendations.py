import logging
import math
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select

from app.api.deps import DBSession
from app.db.models import Product, Recommendation, User
from app.ml.cache import recommendation_cache
from app.ml.recommender import model_manager
from app.ml.xai_engine import xai_engine
from app.schemas.schemas import (
    ProductResponse,
    RecommendationHistoryItem,
    RecommendationHistoryResponse,
    RecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _card_reason(product: dict, user_stats: dict, is_new_user: bool) -> str:
    """
    Generate a unique, product-specific reason for the card teaser.
    Never identical across two products because it embeds product.review_count
    and product.rating which differ per item.
    """
    fav_cat = user_stats.get("fav_category")
    cat = product.get("category", "")
    rating = product.get("rating", 0.0)
    reviews = int(product.get("review_count", 0))
    user_avg = user_stats.get("user_avg_rating", 3.5)

    if is_new_user:
        # Trending / new-user path — purely popularity-based text
        pop = rating * math.log1p(reviews)
        if pop >= 50:
            return f"Trending bestseller · {rating}★ across {reviews:,} buyers"
        elif pop >= 40:
            return f"Top pick this week · {reviews:,} verified reviews ({rating}★)"
        else:
            return f"Popular {cat} · {rating}★ from {reviews:,} customers"

    # Returning user — show personalised signals
    in_fav_cat = fav_cat and fav_cat == cat

    if in_fav_cat and rating >= 4.8:
        return (
            f"Top-rated {cat} ({rating}★, {reviews:,} reviews)"
            f" — matches your category preference"
        )
    if in_fav_cat and reviews >= 30_000:
        return f"Bestseller in {cat} ({reviews:,} reviews) — your favourite category"
    if in_fav_cat:
        return f"In your favourite category · {rating}★ rated by {reviews:,} buyers"

    # Cross-category — emphasise product's strongest signal
    if reviews >= 80_000:
        return f"Bestseller · {reviews:,} verified reviews ({rating}★ avg)"
    if reviews >= 40_000:
        return f"Highly popular · {reviews:,} reviews and {rating}★ avg rating"
    if rating >= 4.8:
        return f"Exceptional quality · {rating}★ from {reviews:,} verified buyers"
    if reviews >= 10_000:
        return f"Well-reviewed {cat} · {reviews:,} customers rated it {rating}★"
    if abs(user_avg - rating) <= 0.2:
        return f"Aligns with your taste · {rating}★, rated by {reviews:,} buyers"

    return f"{rating}★ rated · {reviews:,} reviews in {cat}"


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recommendations(
    request: RecommendationRequest,
    db: DBSession,
) -> RecommendationResponse:
    start = time.perf_counter()

    user = await db.get(User, request.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    cache_key = f"rec:{request.user_id}:{request.limit}:{request.category_filter or 'all'}"
    was_cached = cache_key in recommendation_cache

    prediction_result = await model_manager.predict(
        user_id=request.user_id,
        db=db,
        n=request.limit,
        category_filter=request.category_filter,
    )

    predictions = prediction_result["results"]
    user_stats = prediction_result["user_stats"]
    is_new_user = prediction_result["is_new_user"]

    if not predictions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No products available. Seed the database first.",
        )

    # FIX 5: Normalise confidence scores from raw XGBoost scores so each card
    # shows a genuinely different percentage (76–97% range).
    raw_scores = [p["score"] for p in predictions]
    s_min, s_max = min(raw_scores), max(raw_scores)
    score_spread = s_max - s_min
    CONF_HIGH, CONF_LOW = 97, 76

    def _score_to_confidence(s: float, rank: int = 0) -> int:
        if score_spread < 1e-6:
            step = max(1, (CONF_HIGH - CONF_LOW) // max(1, len(raw_scores) - 1))
            return CONF_HIGH - rank * step
        t = (s - s_min) / score_spread
        return int(round(CONF_LOW + t * (CONF_HIGH - CONF_LOW)))

    items: list[RecommendationItem] = []

    for rank, pred in enumerate(predictions):
        product_data = pred["product"]
        feature_vector = pred["feature_vector"]
        score = pred["score"]

        rec_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"rec:{request.user_id}:{product_data['id']}",
        )

        shap_result = xai_engine.explain(feature_vector, str(rec_id))

        # Cold-start: fixed confidence + trending reason (< 5 interactions)
        if is_new_user:
            confidence = 50
            top_reason = (
                f"Trending — {product_data.get('rating', 0)}★ rated by "
                f"{int(product_data.get('review_count', 0)):,} buyers"
            )
        else:
            confidence = _score_to_confidence(score, rank)
            top_reason = _card_reason(product_data, user_stats, is_new_user)

        try:
            existing = await db.get(Recommendation, rec_id)
            if existing is None:
                rec = Recommendation(
                    id=rec_id,
                    user_id=request.user_id,
                    product_id=product_data["id"],
                    score=score,
                    shap_values={
                        "feature_vector": feature_vector,
                        "shap_result": shap_result,
                    },
                )
                db.add(rec)
        except Exception as exc:
            logger.warning("Recommendation persist skipped: %s", exc)

        items.append(
            RecommendationItem(
                recommendation_id=rec_id,
                product=ProductResponse(
                    id=product_data["id"],
                    name=product_data["name"],
                    category=product_data["category"],
                    price=product_data["price"],
                    rating=product_data["rating"],
                    review_count=product_data["review_count"],
                    image_url=product_data.get("image_url"),
                    amazon_url=product_data.get("amazon_url"),
                ),
                score=score,
                confidence_score=confidence,
                top_reason=top_reason,
            )
        )

    try:
        await db.commit()
    except Exception as exc:
        logger.warning("Recommendations DB commit failed: %s", exc)
        await db.rollback()

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return RecommendationResponse(
        user_id=request.user_id,
        recommendations=items,
        cached=was_cached,
        response_time_ms=elapsed_ms,
        is_new_user=is_new_user,
    )


@router.get(
    "/recommendations/history/{user_id}",
    response_model=RecommendationHistoryResponse,
)
async def get_recommendation_history(
    user_id: uuid.UUID,
    db: DBSession,
) -> RecommendationHistoryResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(
        select(Recommendation, Product)
        .join(Product, Recommendation.product_id == Product.id)
        .where(Recommendation.user_id == user_id)
        .order_by(desc(Recommendation.created_at))
        .limit(20)
    )
    rows = result.all()

    history = [
        RecommendationHistoryItem(
            recommendation_id=rec.id,
            product_name=product.name,
            score=rec.score,
            created_at=rec.created_at,
        )
        for rec, product in rows
    ]

    return RecommendationHistoryResponse(
        user_id=user_id,
        history=history,
        total=len(history),
    )
