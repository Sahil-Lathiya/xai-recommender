import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy async engine — only created if DB URL is configured
_engine = None
_AsyncSessionLocal = None

if settings.SUPABASE_DB_URL:
    _engine = create_async_engine(
        settings.SUPABASE_DB_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.is_development,
    )
    _AsyncSessionLocal = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


class Base(DeclarativeBase):
    pass


# Supabase client (singleton)
_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


async def run_startup_migrations() -> None:
    """Add new columns idempotently on every startup."""
    if _engine is None:
        return
    try:
        async with _engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS amazon_url VARCHAR(1000)"
            ))
        logger.info("Startup schema migrations applied")
    except Exception as exc:
        logger.warning("Startup migration warning (non-fatal): %s", exc)


async def check_db_health() -> bool:
    if _engine is None:
        return False
    try:
        async with _AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _AsyncSessionLocal is None:
        raise RuntimeError("Database not configured — set SUPABASE_DB_URL in .env")
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
