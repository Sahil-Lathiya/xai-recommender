"""
SHAP-based explainability engine — production only.
Uses TreeExplainer (fast, exact) on the saved XGBoost model.
No LIME, no sentence-transformers, no dataset loading.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import joblib
import numpy as np

from app.core.config import settings
from app.ml.cache import explanation_cache, global_importance_cache

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
    "user_avg_rating": "Your Rating History",
    "user_review_count": "Your Activity",
    "product_avg_rating": "Product Rating",
    "product_review_count": "Number of Reviews",
    "category_match": "Category Match",
    "price_percentile": "Price Point",
    "semantic_similarity": "Taste Alignment",
    "recency_score": "How Recent",
}

FEATURE_REASONS = {
    "user_avg_rating": (
        "you typically enjoy highly-rated products (your avg: {value:.1f}/5)"
    ),
    "user_review_count": (
        "you're an experienced reviewer with {value:.0f} ratings"
    ),
    "product_avg_rating": (
        "this product is highly rated at {value:.1f}/5 by other buyers"
    ),
    "product_review_count": (
        "this is a popular product with {value:,.0f} reviews"
    ),
    "category_match": (
        "this is in your favourite product category"
    ),
    "price_percentile": (
        "the price fits your usual spending range ({pct:.0f}th percentile)"
    ),
    "semantic_similarity": (
        "your taste aligns strongly with this product ({pct:.0f}% match)"
    ),
    "recency_score": (
        "your recent browsing history points to this product"
    ),
}

COUNTERFACTUAL_TEMPLATES = {
    "product_avg_rating": (
        "If this product's rating improved to {threshold:.1f}/5, "
        "your match score would increase by ~{delta:.0f}%."
    ),
    "product_review_count": (
        "If this product had {threshold:,.0f}+ reviews, "
        "confidence would rise by ~{delta:.0f}%."
    ),
    "category_match": (
        "Products in your preferred category would score ~{delta:.0f}% higher."
    ),
    "semantic_similarity": (
        "Products more closely aligned with your taste would score ~{delta:.0f}% higher."
    ),
    "price_percentile": (
        "A product priced at your typical range would score ~{delta:.0f}% higher."
    ),
    "user_review_count": (
        "The more you interact with products, the better your recommendations get "
        "(potential gain: ~{delta:.0f}%)."
    ),
    "recency_score": (
        "Browsing more frequently would improve recommendation accuracy by ~{delta:.0f}%."
    ),
}


class XAIEngine:
    """
    Singleton SHAP explainer.
    initialize() is called once during FastAPI lifespan, after the model loads.
    explain() is called per-recommendation request — ~5ms per call.
    """

    def __init__(self) -> None:
        self.explainer = None
        self.model = None
        self._initialized: bool = False

    def initialize(self, model) -> None:
        import shap

        try:
            background = joblib.load(settings.SHAP_BACKGROUND_PATH)
            # shap.kmeans() returns DenseData; extract numpy array for Python 3.12 compat
            if hasattr(background, "data"):
                background = background.data
            self.explainer = shap.TreeExplainer(model, data=background)
            logger.info("SHAP TreeExplainer initialised with kmeans background (k=50)")
        except FileNotFoundError:
            self.explainer = shap.TreeExplainer(model)
            logger.warning(
                "shap_background.pkl not found — TreeExplainer using model-only mode"
            )

        self.model = model
        self._initialized = True

    # ── Public API ──────────────────────────────────────────────────────────────

    def explain(self, feature_vector: list[float], recommendation_id: str) -> dict:
        """
        Compute SHAP explanation for a single feature vector.
        Result is cached by recommendation_id (TTL 3600s).
        """
        cached = explanation_cache.get(str(recommendation_id))
        if cached is not None:
            return cached

        if not self._initialized or self.explainer is None:
            result = self._fallback_explanation(feature_vector)
            explanation_cache[str(recommendation_id)] = result
            return result

        X = np.array(feature_vector, dtype=np.float64).reshape(1, -1)

        try:
            raw_shap = self.explainer.shap_values(X)

            # TreeExplainer on a ranker returns a single array (not list)
            if isinstance(raw_shap, list):
                sv = np.array(raw_shap[0][0], dtype=np.float64)
            else:
                sv = np.array(raw_shap[0], dtype=np.float64)

            base_value = self.explainer.expected_value
            if isinstance(base_value, (list, np.ndarray)):
                base_value = float(base_value[0])
            else:
                base_value = float(base_value)

        except Exception as exc:
            logger.error("SHAP computation error: %s", exc)
            result = self._fallback_explanation(feature_vector)
            explanation_cache[str(recommendation_id)] = result
            return result

        contributions = self._build_contributions(sv, feature_vector)
        top_3 = self._top_3_reasons(contributions, feature_vector)
        confidence = self._confidence_score(sv)
        counterfactual = self._counterfactual(contributions, feature_vector)

        result = {
            "base_value": base_value,
            "feature_contributions": contributions,
            "top_3_reasons": top_3,
            "confidence_score": confidence,
            "counterfactual": counterfactual,
        }

        explanation_cache[str(recommendation_id)] = result
        return result

    def global_importance(self) -> list[dict]:
        """
        Return global XGBoost feature importances.
        Cached for 24 hours — only changes when model is retrained.
        """
        cached = global_importance_cache.get("global")
        if cached is not None:
            return cached

        if self.model is None:
            result = self._fallback_global_importance()
            global_importance_cache["global"] = result
            return result

        try:
            importances = self.model.feature_importances_
        except AttributeError:
            result = self._fallback_global_importance()
            global_importance_cache["global"] = result
            return result

        total = importances.sum()
        items = []
        for i, col in enumerate(FEATURE_COLUMNS):
            score = float(importances[i] / total) if total > 0 else 0.0
            items.append({
                "feature_name": col,
                "importance_score": round(score, 4),
                "rank": 0,
                "description": FEATURE_LABELS.get(col, col),
            })

        items.sort(key=lambda x: x["importance_score"], reverse=True)
        for i, item in enumerate(items):
            item["rank"] = i + 1

        global_importance_cache["global"] = items
        return items

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _build_contributions(
        self, shap_values: np.ndarray, feature_vector: list[float]
    ) -> list[dict]:
        contributions = []
        for i, col in enumerate(FEATURE_COLUMNS):
            sv = float(shap_values[i]) if i < len(shap_values) else 0.0
            contributions.append({
                "feature": col,
                "raw_value": float(feature_vector[i]),
                "shap_value": sv,
                "direction": "positive" if sv >= 0 else "negative",
                "human_label": FEATURE_LABELS.get(col, col),
            })
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return contributions

    def _top_3_reasons(
        self, contributions: list[dict], feature_vector: list[float]
    ) -> list[str]:
        # User-level features are constant across all products for a given user.
        # Prefer product-varying features first so explanations differ per card.
        PRODUCT_VARYING = {"product_avg_rating", "product_review_count",
                           "category_match", "price_percentile", "semantic_similarity"}
        USER_LEVEL = {"user_avg_rating", "user_review_count", "recency_score"}

        positives = [c for c in contributions if c["direction"] == "positive"]

        product_pos = [c for c in positives if c["feature"] in PRODUCT_VARYING]
        user_pos = [c for c in positives if c["feature"] in USER_LEVEL]
        negatives = [c for c in contributions if c["direction"] == "negative"]

        ordered = product_pos + user_pos + negatives
        reasons: list[str] = []
        for c in ordered:
            if len(reasons) >= 3:
                break
            reasons.append(self._format_reason(c))
        return reasons[:3]

    def _format_reason(self, contribution: dict) -> str:
        feature = contribution["feature"]
        value = contribution["raw_value"]
        template = FEATURE_REASONS.get(feature, "{label}: {value:.2f}")
        return template.format(
            value=value,
            pct=value * 100,
            label=FEATURE_LABELS.get(feature, feature),
        )

    def _confidence_score(self, shap_values: np.ndarray) -> int:
        positive_sum = float(np.sum(shap_values[shap_values > 0]))
        total_abs = float(np.sum(np.abs(shap_values)))
        if total_abs < 1e-9:
            return 50
        confidence = int((positive_sum / total_abs) * 100)
        return max(0, min(100, confidence))

    def _counterfactual(
        self, contributions: list[dict], feature_vector: list[float]
    ) -> str:
        negatives = [c for c in contributions if c["shap_value"] < 0]
        if not negatives:
            return (
                "This product already scores highly on all factors — "
                "it's an excellent match for you."
            )

        worst = negatives[0]
        feature = worst["feature"]
        value = worst["raw_value"]
        delta = abs(worst["shap_value"]) * 25

        template = COUNTERFACTUAL_TEMPLATES.get(feature)
        if template is None:
            return (
                f"Improving {FEATURE_LABELS.get(feature, feature)} would "
                f"increase your match score by ~{delta:.0f}%."
            )

        threshold_map = {
            "product_avg_rating": min(5.0, value + 0.5),
            "product_review_count": value * 2,
        }
        threshold = threshold_map.get(feature, value * 1.5)

        return template.format(threshold=threshold, delta=delta, value=value)

    # ── Fallbacks ───────────────────────────────────────────────────────────────

    def _fallback_explanation(self, feature_vector: list[float]) -> dict:
        contributions = []
        for i, col in enumerate(FEATURE_COLUMNS):
            val = float(feature_vector[i]) if i < len(feature_vector) else 0.5
            sv = (val - 0.5) * 0.08
            contributions.append({
                "feature": col,
                "raw_value": val,
                "shap_value": sv,
                "direction": "positive" if sv >= 0 else "negative",
                "human_label": FEATURE_LABELS.get(col, col),
            })
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return {
            "base_value": 0.5,
            "feature_contributions": contributions,
            "top_3_reasons": [self._format_reason(c) for c in contributions[:3]],
            "confidence_score": 65,
            "counterfactual": (
                "Interact with more products to improve recommendation accuracy."
            ),
        }

    def _fallback_global_importance(self) -> list[dict]:
        defaults = [0.22, 0.18, 0.20, 0.15, 0.10, 0.07, 0.05, 0.03]
        items = []
        for i, col in enumerate(FEATURE_COLUMNS):
            items.append({
                "feature_name": col,
                "importance_score": defaults[i],
                "rank": i + 1,
                "description": FEATURE_LABELS.get(col, col),
            })
        return items


# Module-level singleton — imported by main.py lifespan
xai_engine = XAIEngine()
