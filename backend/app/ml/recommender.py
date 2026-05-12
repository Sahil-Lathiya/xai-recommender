"""
Production inference engine — NO dataset loading, NO sentence-transformers.
Loads saved XGBoost model from disk once at startup and serves predictions.
"""
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

import joblib
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.cache import recommendation_cache

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "user_avg_rating",
    "user_review_count",
    "product_avg_rating",
    "product_review_count",
    "category_match",
    "price_percentile",
    "semantic_similarity",
    "recency_score",
]

FEATURE_LABELS = {
    "user_avg_rating": "Your average rating",
    "user_review_count": "Your reviewing activity",
    "product_avg_rating": "Product quality score",
    "product_review_count": "Product popularity",
    "category_match": "Category preference match",
    "price_percentile": "Price fit",
    "semantic_similarity": "Taste alignment",
    "recency_score": "Shopping recency",
}

# Category boost applied post-scoring so user's preferred category always surfaces
CATEGORY_BOOST = 3.0


class ModelManager:
    """
    Singleton that owns the XGBoost model for the lifetime of the process.
    load() is called once during FastAPI lifespan startup.
    predict() is called per request — fast, stateless inference only.
    """

    def __init__(self) -> None:
        self.model = None
        self.feature_columns: list[str] = FEATURE_COLUMNS
        self._loaded: bool = False

    def load(self) -> None:
        self.model = joblib.load(settings.MODEL_PATH)

        try:
            loaded_cols = joblib.load(settings.FEATURE_COLUMNS_PATH)
            self.feature_columns = loaded_cols
        except FileNotFoundError:
            logger.warning("feature_columns.pkl not found — using default column order")
            self.feature_columns = FEATURE_COLUMNS

        self._loaded = True
        logger.info(
            "XGBoost model loaded from %s  |  features: %s",
            settings.MODEL_PATH,
            self.feature_columns,
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    # ── Public API ──────────────────────────────────────────────────────────────

    async def predict(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        n: int = 5,
        category_filter: Optional[str] = None,
    ) -> dict:
        """
        Returns {"results": [...], "user_stats": {...}, "is_new_user": bool}

        Each result item: {product: dict, score: float, feature_vector: list[float]}
        """
        cache_key = f"rec:{user_id}:{n}:{category_filter or 'all'}"
        cached = recommendation_cache.get(cache_key)
        if cached is not None:
            return cached

        user_stats = await self._get_user_stats(user_id, db)
        products = await self._get_candidate_products(db, category_filter, limit=50)

        if not products:
            payload = {"results": [], "user_stats": user_stats, "is_new_user": False}
            recommendation_cache[cache_key] = payload
            return payload

        is_new_user = user_stats["user_review_count"] < 5

        if is_new_user:
            results = self._trending_fallback(products, n)
            payload = {"results": results, "user_stats": user_stats, "is_new_user": True}
            recommendation_cache[cache_key] = payload
            return payload

        if not self.is_loaded:
            results = self._popularity_fallback(products, n)
            payload = {"results": results, "user_stats": user_stats, "is_new_user": False}
            recommendation_cache[cache_key] = payload
            return payload

        feature_vectors = [
            self._build_feature_vector(user_stats, p)
            for p in products
        ]
        X = np.array(feature_vectors, dtype=np.float32)
        scores = self.model.predict(X).astype(np.float64)

        # Apply category preference boost — ensures user's favourite category surfaces
        # in the top-5 even when cross-category items have high review counts.
        fav_cat = user_stats.get("fav_category")
        if fav_cat:
            for i, product in enumerate(products):
                if product["category"] == fav_cat:
                    scores[i] *= CATEGORY_BOOST

        top_indices = np.argsort(scores)[::-1][:n]
        results = [
            {
                "product": products[idx],
                "score": float(np.clip(scores[idx] / (CATEGORY_BOOST if fav_cat and products[idx]["category"] == fav_cat else 1.0), 0.0, 1.0)),
                "feature_vector": feature_vectors[idx],
            }
            for idx in top_indices
        ]

        payload = {"results": results, "user_stats": user_stats, "is_new_user": False}
        recommendation_cache[cache_key] = payload
        return payload

    # ── Internal helpers ────────────────────────────────────────────────────────

    async def _get_user_stats(self, user_id: uuid.UUID, db: AsyncSession) -> dict:
        from app.db.models import Product, UserInteraction

        agg = await db.execute(
            select(
                func.avg(UserInteraction.rating).label("avg_rating"),
                func.count(UserInteraction.id).label("review_count"),
                func.max(UserInteraction.timestamp).label("last_ts"),
            ).where(UserInteraction.user_id == user_id)
        )
        row = agg.one_or_none()
        avg_rating = float(row.avg_rating) if row and row.avg_rating else 3.5
        review_count = int(row.review_count) if row and row.review_count else 0
        last_ts = row.last_ts if row else None

        # Determine favourite category from interaction history
        fav_category: Optional[str] = None
        interactions = await db.execute(
            select(UserInteraction.product_id)
            .where(UserInteraction.user_id == user_id)
            .limit(200)
        )
        product_ids = [r[0] for r in interactions.fetchall()]

        if product_ids:
            cat_query = await db.execute(
                select(Product.category, func.count().label("cnt"))
                .where(Product.id.in_(product_ids))
                .group_by(Product.category)
                .order_by(func.count().desc())
                .limit(1)
            )
            cat_row = cat_query.first()
            if cat_row:
                fav_category = cat_row[0]

        return {
            "user_avg_rating": avg_rating,
            "user_review_count": review_count,
            "last_ts": last_ts,
            "fav_category": fav_category,
        }

    async def _get_candidate_products(
        self,
        db: AsyncSession,
        category_filter: Optional[str],
        limit: int = 50,
    ) -> list[dict]:
        from app.db.models import Product

        query = select(Product).where(
            Product.image_url.isnot(None),
            Product.amazon_url.isnot(None),
        )
        if category_filter:
            query = query.where(Product.category == category_filter)
        query = query.order_by(Product.review_count.desc()).limit(limit)

        result = await db.execute(query)
        products = result.scalars().all()

        if not products:
            return []

        prices = [p.price for p in products]
        p_min, p_max = min(prices), max(prices)
        price_range = p_max - p_min if p_max > p_min else 1.0

        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "rating": p.rating,
                "review_count": p.review_count,
                "image_url": p.image_url,
                "amazon_url": p.amazon_url,
                "price_percentile": (p.price - p_min) / price_range,
            }
            for p in products
        ]

    def _build_feature_vector(self, user_stats: dict, product: dict) -> list[float]:
        now = datetime.now(timezone.utc)

        last_ts = user_stats.get("last_ts")
        if last_ts is not None:
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            days_since = max(0, (now - last_ts).days)
            recency = float(np.exp(-0.05 * days_since))
        else:
            recency = 0.3

        user_rating = user_stats["user_avg_rating"]
        product_rating = product["rating"]
        semantic_sim = float(1.0 - abs(user_rating - product_rating) / 4.0)
        semantic_sim = max(0.0, min(1.0, semantic_sim))

        category_match = 1.0 if (
            user_stats.get("fav_category") is not None
            and user_stats["fav_category"] == product["category"]
        ) else 0.0

        return [
            user_stats["user_avg_rating"],
            float(user_stats["user_review_count"]),
            float(product["rating"]),
            float(product["review_count"]),
            category_match,
            float(product["price_percentile"]),
            semantic_sim,
            recency,
        ]

    def _trending_fallback(self, products: list[dict], n: int) -> list[dict]:
        """Popularity-ranked products for new users (0 interactions)."""
        scored = sorted(
            products,
            key=lambda p: p["rating"] * math.log1p(p["review_count"]),
            reverse=True,
        )[:n]
        return [
            {
                "product": p,
                "score": min(1.0, p["rating"] * math.log1p(p["review_count"]) / 55.0),
                "feature_vector": [3.5, 0.0, p["rating"], float(p["review_count"]), 0.0,
                                   p["price_percentile"], 0.5, 0.3],
            }
            for p in scored
        ]

    def _popularity_fallback(self, products: list[dict], n: int) -> list[dict]:
        """Used when model is not loaded — same as trending."""
        return self._trending_fallback(products, n)


# Module-level singleton — imported by main.py lifespan and route handlers
model_manager = ModelManager()
