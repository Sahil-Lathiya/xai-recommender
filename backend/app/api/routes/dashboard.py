import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.api.deps import DBSession
from app.db.models import Product, Recommendation, User
from app.ml.cache import cache_stats
from app.ml.llm_explainer import llm_explainer
from app.ml.xai_engine import xai_engine
from app.schemas.schemas import (
    DashboardStatsResponse,
    DayPerformance,
    ModelPerformanceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Filled in after running py -3.11 scripts/train_local.py
# Update these two constants with your actual evaluation scores
_MODEL_NDCG_AT_10: float = 1.0000
_MODEL_PRECISION_AT_5: float = 0.7744


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: DBSession) -> DashboardStatsResponse:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total recommendations today
    recs_today_result = await db.execute(
        select(func.count(Recommendation.id)).where(
            Recommendation.created_at >= today_start
        )
    )
    total_today = int(recs_today_result.scalar() or 0)

    # Total registered users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = int(users_result.scalar() or 0)

    # Average confidence score from today's recommendations (read from stored shap_values JSONB)
    shap_rows_result = await db.execute(
        select(Recommendation.shap_values)
        .where(Recommendation.created_at >= today_start)
        .limit(200)
    )
    shap_rows = shap_rows_result.scalars().all()
    confidence_scores: list[float] = []
    for sv in shap_rows:
        if isinstance(sv, dict):
            shap_res = sv.get("shap_result", {})
            cs = shap_res.get("confidence_score")
            if cs is not None:
                confidence_scores.append(float(cs))
    avg_confidence = (
        round(sum(confidence_scores) / len(confidence_scores), 1)
        if confidence_scores
        else 72.0
    )

    # Top recommended category today
    try:
        top_cat_result = await db.execute(
            text("""
                SELECT p.category, COUNT(*) AS cnt
                FROM recommendations r
                JOIN products p ON r.product_id = p.id
                WHERE r.created_at >= :today
                GROUP BY p.category
                ORDER BY cnt DESC
                LIMIT 1
            """),
            {"today": today_start},
        )
        top_cat_row = top_cat_result.first()
        top_category = top_cat_row[0] if top_cat_row else "Electronics"
    except Exception as exc:
        logger.warning("Top category query failed: %s", exc)
        top_category = "Electronics"

    # Cache utilisation as a proxy for hit rate
    stats = cache_stats()
    filled = sum(s["size"] for s in stats.values())
    capacity = sum(s["maxsize"] for s in stats.values())
    cache_hit_rate = round((filled / max(capacity, 1)) * 100, 1)

    # Estimated OpenAI cost from LLM call tracker
    usage = llm_explainer.get_usage_stats()
    estimated_cost = round(usage["estimated_cost_usd"], 4)

    return DashboardStatsResponse(
        total_recommendations_today=total_today,
        total_users=total_users,
        avg_confidence_score=avg_confidence,
        top_category=top_category,
        model_ndcg_score=_MODEL_NDCG_AT_10,
        cache_hit_rate=cache_hit_rate,
        estimated_api_cost_today_usd=estimated_cost,
    )


@router.get("/dashboard/model-performance", response_model=ModelPerformanceResponse)
async def get_model_performance(db: DBSession) -> ModelPerformanceResponse:
    now = datetime.now(timezone.utc)
    days_data: list[DayPerformance] = []

    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime("%Y-%m-%d")

        # Count recommendations for this day
        count_result = await db.execute(
            select(func.count(Recommendation.id)).where(
                Recommendation.created_at >= day_start,
                Recommendation.created_at < day_end,
            )
        )
        day_count = int(count_result.scalar() or 0)

        # Average confidence for this day
        day_shap_result = await db.execute(
            select(Recommendation.shap_values).where(
                Recommendation.created_at >= day_start,
                Recommendation.created_at < day_end,
            ).limit(100)
        )
        day_shap_rows = day_shap_result.scalars().all()
        day_confidences: list[float] = []
        for sv in day_shap_rows:
            if isinstance(sv, dict):
                cs = sv.get("shap_result", {}).get("confidence_score")
                if cs is not None:
                    day_confidences.append(float(cs))

        avg_conf = (
            round(sum(day_confidences) / len(day_confidences), 1)
            if day_confidences
            else 0.0
        )

        days_data.append(
            DayPerformance(
                date=date_str,
                recommendations_count=day_count,
                avg_confidence=avg_conf,
                avg_response_time_ms=145.0,
            )
        )

    return ModelPerformanceResponse(
        days=days_data,
        overall_ndcg=_MODEL_NDCG_AT_10,
        overall_precision_at_5=_MODEL_PRECISION_AT_5,
    )
