from cachetools import TTLCache

# Recommendation results — 5-minute TTL (same request never hits XGBoost twice)
recommendation_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)

# Per-recommendation SHAP + LLM explanation — 1-hour TTL
explanation_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

# OpenAI embedding vectors — 1-hour TTL (product/user embeddings don't change often)
embedding_cache: TTLCache = TTLCache(maxsize=200, ttl=3600)

# Global feature importance — 24-hour TTL (changes only if model is retrained)
global_importance_cache: TTLCache = TTLCache(maxsize=1, ttl=86400)


def cache_stats() -> dict:
    """Return current cache hit statistics for the dashboard."""
    return {
        "recommendation_cache": {
            "size": len(recommendation_cache),
            "maxsize": recommendation_cache.maxsize,
            "ttl": recommendation_cache.ttl,
        },
        "explanation_cache": {
            "size": len(explanation_cache),
            "maxsize": explanation_cache.maxsize,
            "ttl": explanation_cache.ttl,
        },
        "embedding_cache": {
            "size": len(embedding_cache),
            "maxsize": embedding_cache.maxsize,
            "ttl": embedding_cache.ttl,
        },
        "global_importance_cache": {
            "size": len(global_importance_cache),
            "maxsize": global_importance_cache.maxsize,
            "ttl": global_importance_cache.ttl,
        },
    }
