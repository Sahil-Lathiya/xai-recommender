import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import psutil
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import check_db_health, run_startup_migrations

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("═══ XAI Recommender API starting ═══")

    # Load ML model and SHAP explainer at startup (once only)
    try:
        from app.ml.recommender import model_manager
        from app.ml.xai_engine import xai_engine

        model_manager.load()
        xai_engine.initialize(model_manager.model)
        app.state.model_loaded = True
        logger.info("XGBoost model + SHAP TreeExplainer loaded successfully")
    except Exception as exc:
        logger.error("Model load failed (running without ML): %s", exc)
        app.state.model_loaded = False

    # Run idempotent schema migrations (adds new columns if missing)
    await run_startup_migrations()

    # Verify database connectivity
    app.state.db_connected = await check_db_health()
    logger.info("Database connected: %s", app.state.db_connected)

    # Track startup time for uptime calculation
    app.state.started_at = datetime.now(timezone.utc)

    # Cache hit counters for dashboard
    app.state.cache_hits = 0
    app.state.cache_total = 0
    app.state.total_llm_tokens = 0
    app.state.total_llm_calls = 0

    # Product fetcher — run once on startup only (Scavio free tier: 250 credits/month).
    # Manual refresh: POST /api/v1/admin/refresh-products
    from app.services.amazon_fetcher import fetch_and_upsert_products
    asyncio.create_task(fetch_and_upsert_products())

    logger.info("═══ XAI Recommender API ready on port %d ═══", settings.PORT)

    yield

    logger.info("═══ XAI Recommender API shutting down ═══")


app = FastAPI(
    title="XAI Recommender API",
    description=(
        "Production-grade Explainable AI Product Recommendation System. "
        "Real-time SHAP explanations, LLM-powered natural language output, "
        "and live monitoring dashboard."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    return response


# ── Global exception handler — never leaks stack traces ────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ── Health endpoint ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    process = psutil.Process(os.getpid())
    memory_mb = round(process.memory_info().rss / 1024 / 1024, 1)
    db_ok = await check_db_health()

    return {
        "status": "healthy",
        "model_loaded": getattr(app.state, "model_loaded", False),
        "db_connected": db_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "memory_mb": memory_mb,
        "environment": settings.ENVIRONMENT,
    }


# ── Routers ────────────────────────────────────────────────────────────────────
from app.api.routes import dashboard, explanations, recommendations, users  # noqa: E402

app.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])
app.include_router(explanations.router, prefix="/api/v1", tags=["explanations"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
