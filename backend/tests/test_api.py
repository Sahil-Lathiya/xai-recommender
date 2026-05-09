"""
XAI Recommender — API Test Suite
Run: py -3.11 -m pytest backend/tests/test_api.py -v

Two modes:
  • No .env / no DB → health + LLM-fallback tests run; DB tests are skipped.
  • With backend/.env set → all 12 tests run against the live Supabase DB.

To run the full suite, copy backend/.env.example to backend/.env and fill in
your Supabase + OpenAI credentials, then seed the DB first:
  py -3.11 backend/data/seed_demo_data.py
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ── Resolve backend package ───────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env before importing anything that reads settings
_env_file = BACKEND_DIR / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)

from app.main import app  # noqa: E402

# ── Skip marker: applied to every test that needs a live DB ───────────────────
_DB_URL = os.environ.get("SUPABASE_DB_URL", "")
_DB_AVAILABLE = bool(_DB_URL and _DB_URL.startswith("postgresql"))

requires_db = pytest.mark.skipif(
    not _DB_AVAILABLE,
    reason="SUPABASE_DB_URL not set — skipping DB-dependent test. "
           "Fill in backend/.env and re-run for the full suite.",
)

# ── Seed UUIDs (from supabase/migrations/001_initial.sql) ─────────────────────
TECH_USER_ID  = "22222222-2222-2222-2222-222222222201"
BOOKS_USER_ID = "22222222-2222-2222-2222-222222222202"
TECH_EMAIL    = "tech@demo.xai"
DEMO_PASSWORD = "Demo1234!"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def auth_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/users/login",
        json={"email": TECH_EMAIL, "password": DEMO_PASSWORD},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]



# ── Test 1: Health ────────────────────────────────────────────────────────────

class TestHealth:

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Health endpoint must always return 200 with required fields."""
        resp = await client.get("/health")
        assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "healthy"
        assert isinstance(body["model_loaded"], bool)
        assert isinstance(body["db_connected"], bool)
        assert "timestamp" in body
        assert "memory_mb" in body
        assert body["memory_mb"] > 0


# ── Tests 2 & 3: Auth ─────────────────────────────────────────────────────────

class TestUserAuth:

    @requires_db
    @pytest.mark.asyncio
    async def test_user_register_duplicate_returns_409(self, client: AsyncClient):
        """Registering an existing email must return 409 Conflict."""
        resp = await client.post(
            "/api/v1/users/register",
            json={"email": TECH_EMAIL, "name": "Dup", "password": "AnyPass123!"},
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    @requires_db
    @pytest.mark.asyncio
    async def test_user_login_success(self, client: AsyncClient):
        """Demo user login returns a valid JWT."""
        resp = await client.post(
            "/api/v1/users/login",
            json={"email": TECH_EMAIL, "password": DEMO_PASSWORD},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    @requires_db
    @pytest.mark.asyncio
    async def test_user_login_wrong_password_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/users/login",
            json={"email": TECH_EMAIL, "password": "WrongPass999!"},
        )
        assert resp.status_code == 401


# ── Test 4: Recommendations ───────────────────────────────────────────────────

class TestRecommendations:

    @requires_db
    @pytest.mark.asyncio
    async def test_get_recommendations(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/recommendations",
            json={"user_id": TECH_USER_ID, "limit": 5},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["user_id"] == TECH_USER_ID
        assert isinstance(body["recommendations"], list)
        assert len(body["recommendations"]) > 0
        assert isinstance(body["cached"], bool)
        assert isinstance(body["response_time_ms"], int)

        rec = body["recommendations"][0]
        for field in ("recommendation_id", "product", "score", "confidence_score", "top_reason"):
            assert field in rec, f"Missing field: {field}"

        assert 0 <= rec["confidence_score"] <= 100

        product = rec["product"]
        for field in ("id", "name", "category", "price", "rating", "review_count"):
            assert field in product, f"Missing product field: {field}"

    @requires_db
    @pytest.mark.asyncio
    async def test_recommendations_cache_hit(self, client: AsyncClient):
        """Second identical request must be served from TTL cache."""
        payload = {"user_id": BOOKS_USER_ID, "limit": 3}

        resp1 = await client.post("/api/v1/recommendations", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["cached"] is False  # first call always fresh

        resp2 = await client.post("/api/v1/recommendations", json=payload)
        assert resp2.status_code == 200
        assert resp2.json()["cached"] is True   # second call must hit cache

    @requires_db
    @pytest.mark.asyncio
    async def test_recommendations_unknown_user_returns_404(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/recommendations",
            json={"user_id": "00000000-0000-0000-0000-000000000000", "limit": 5},
        )
        assert resp.status_code == 404


# ── Tests 5 & 6: Explanations ─────────────────────────────────────────────────

class TestExplanation:

    @requires_db
    @pytest.mark.asyncio
    async def test_get_explanation(self, client: AsyncClient):
        # Get a fresh recommendation to use its ID
        recs_resp = await client.post(
            "/api/v1/recommendations",
            json={"user_id": TECH_USER_ID, "limit": 1},
        )
        assert recs_resp.status_code == 200, f"Recommendations failed: {recs_resp.text}"
        rec_id = str(recs_resp.json()["recommendations"][0]["recommendation_id"])

        resp = await client.get(f"/api/v1/explain/{rec_id}")
        assert resp.status_code == 200

        body = resp.json()
        assert body["recommendation_id"] == rec_id

        product = body["product"]
        assert "name" in product
        assert product["price"] > 0

        shap = body["shap_values"]
        assert "base_value" in shap
        assert isinstance(shap["feature_contributions"], list)
        assert len(shap["feature_contributions"]) > 0
        assert isinstance(shap["top_3_reasons"], list)

        contrib = shap["feature_contributions"][0]
        for key in ("feature", "shap_value", "direction", "human_label"):
            assert key in contrib

        assert isinstance(body["llm_explanation"], str)
        assert len(body["llm_explanation"]) > 10
        assert 0 <= body["confidence_score"] <= 100
        assert "powered_by" in body

    @requires_db
    @pytest.mark.asyncio
    async def test_get_global_feature_importance(self, client: AsyncClient):
        resp = await client.get("/api/v1/explain/global/feature-importance")
        assert resp.status_code == 200

        body = resp.json()
        assert "features" in body
        assert len(body["features"]) > 0
        assert "cached_until" in body

        feature = body["features"][0]
        for key in ("feature_name", "importance_score", "rank", "description"):
            assert key in feature
        assert feature["rank"] == 1


# ── Tests 7 & 8: Dashboard ────────────────────────────────────────────────────

class TestDashboard:

    @requires_db
    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

        body = resp.json()
        required_keys = [
            "total_recommendations_today",
            "total_users",
            "avg_confidence_score",
            "top_category",
            "model_ndcg_score",
            "cache_hit_rate",
            "estimated_api_cost_today_usd",
        ]
        for key in required_keys:
            assert key in body, f"Missing key: {key}"

        assert body["total_users"] >= 3
        assert 0 <= body["avg_confidence_score"] <= 100
        assert body["cache_hit_rate"] >= 0

    @requires_db
    @pytest.mark.asyncio
    async def test_get_model_performance(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/model-performance")
        assert resp.status_code == 200

        body = resp.json()
        assert "days" in body
        assert len(body["days"]) == 7
        assert "overall_ndcg" in body

        day = body["days"][0]
        for key in ("date", "recommendations_count", "avg_confidence", "avg_response_time_ms"):
            assert key in day


# ── Test 9: LLM Fallback ──────────────────────────────────────────────────────

class TestLLMFallback:

    @pytest.mark.asyncio
    async def test_llm_fallback_returns_string_never_raises(self):
        """LLMExplainer with a broken API key must silently return a string."""
        original_key = os.environ.get("OPENAI_API_KEY", "")
        os.environ["OPENAI_API_KEY"] = "sk-invalid-key-for-testing"

        try:
            from app.ml.llm_explainer import LLMExplainer
            explainer = LLMExplainer()
            result = await explainer.explain(
                product_name="Test Product",
                price=29.99,
                rating=4.5,
                review_count=1234,
                top_3_reasons=[
                    "you typically enjoy highly-rated products",
                    "this is in your favourite category",
                    "the price fits your usual spending range",
                ],
                user_summary="Electronics enthusiast, regular shopper",
                product_id="test-product-id",
            )
            assert isinstance(result, str), "Must return a string, not raise"
            assert len(result) > 10, "Fallback string must be non-empty"
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)
