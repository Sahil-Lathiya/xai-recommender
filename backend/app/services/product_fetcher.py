"""
Background service: fetch real Amazon products via Scavio API and upsert into Supabase.

Runs once on startup, then every 6 hours via APScheduler.
All failures are caught and logged — this service never crashes the application.
"""
import asyncio
import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SEARCH_QUERIES: dict[str, list[str]] = {
    "Electronics": [
        "wireless earbuds",
        "laptop stand",
        "mechanical keyboard",
        "webcam HD",
        "USB hub",
    ],
    "Books": [
        "python programming book",
        "machine learning book",
        "productivity book bestseller",
        "fiction bestseller 2024",
    ],
    "Clothing": [
        "men hoodie",
        "women running shoes",
        "casual jacket",
        "gym t-shirt",
    ],
    "Home": [
        "desk lamp LED",
        "coffee maker",
        "air purifier",
        "kitchen knife set",
    ],
}

_SCAVIO_URL = "https://api.scavio.dev/api/v1/amazon/search"
_MAX_PER_QUERY = 3  # top-N products to take from each Scavio search


def _affiliate_url(raw_url: str, tag: str) -> str:
    """Append affiliate tag to an Amazon URL, handling both ? and & cases."""
    if not raw_url:
        return raw_url
    sep = "&" if "?" in raw_url else "?"
    return f"{raw_url}{sep}tag={tag}"


async def fetch_and_upsert_products() -> None:
    """
    Fetch real Amazon products from Scavio for all categories and insert new ones
    into Supabase. Existing products (matched by exact name) are skipped to prevent
    duplicates across scheduler runs.
    """
    if not settings.SCAVIO_API_KEY:
        logger.warning("SCAVIO_API_KEY not configured — skipping product fetch")
        return

    from app.db.database import get_supabase
    supabase = get_supabase()

    # Load all existing product names once to avoid per-product DB round-trips
    try:
        existing_resp = await asyncio.to_thread(
            lambda: supabase.table("products").select("name").execute()
        )
        existing_names: set[str] = {
            row["name"].lower().strip()
            for row in (existing_resp.data or [])
        }
        logger.info("Scavio fetch started — %d products already in DB", len(existing_names))
    except Exception as exc:
        logger.warning("Could not pre-load existing product names: %s", exc)
        existing_names = set()

    headers = {
        "Authorization": f"Bearer {settings.SCAVIO_API_KEY}",
        "Content-Type": "application/json",
    }

    new_rows: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for category, queries in SEARCH_QUERIES.items():
            for query in queries:
                try:
                    resp = await client.post(
                        _SCAVIO_URL,
                        headers=headers,
                        json={
                            "query": query,
                            "domain": "co.uk",
                            "sort_by": "average_review",
                            "pages": 1,
                        },
                    )
                    resp.raise_for_status()
                    products = resp.json().get("data", {}).get("products", [])

                    for p in products[:_MAX_PER_QUERY]:
                        name = (p.get("title") or "").strip()
                        if not name:
                            continue
                        if name.lower() in existing_names:
                            continue

                        price_raw = p.get("price")
                        try:
                            price = round(float(price_raw), 2)
                        except (TypeError, ValueError):
                            continue
                        if price <= 0:
                            continue

                        rating = min(5.0, float(p.get("rating") or 0.0))
                        review_count = int(p.get("reviews_count") or 0)
                        image_url = p.get("url_image") or None
                        raw_url = p.get("url") or ""
                        amazon_url = (
                            _affiliate_url(raw_url, settings.AMAZON_ASSOCIATE_ID)
                            if raw_url else None
                        )
                        description = (
                            f"{name}. Rated {rating}★ by "
                            f"{review_count:,} customers on Amazon UK."
                        )

                        new_rows.append({
                            "id": str(uuid.uuid4()),
                            "name": name[:500],
                            "category": category,
                            "price": price,
                            "rating": round(rating, 2),
                            "review_count": review_count,
                            "description": description[:1000],
                            "image_url": image_url,
                            "amazon_url": amazon_url,
                        })
                        # Mark as seen so duplicate query results don't re-insert
                        existing_names.add(name.lower())

                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Scavio HTTP error for query %r (%s): %s",
                        query, category, exc,
                    )
                except Exception as exc:
                    logger.warning(
                        "Scavio unexpected error for query %r (%s): %s",
                        query, category, exc,
                    )

                # Respect Scavio rate limits — 1 req/s is safe for free tier
                await asyncio.sleep(1.0)

    if not new_rows:
        logger.info("Scavio fetch complete — no new products to insert")
        return

    # Batch upsert (on_conflict=id is safe since all IDs are fresh UUIDs)
    try:
        await asyncio.to_thread(
            lambda: supabase.table("products")
            .upsert(new_rows, on_conflict="id")
            .execute()
        )
        logger.info(
            "Scavio fetch complete — %d new products inserted across %d categories",
            len(new_rows),
            len(SEARCH_QUERIES),
        )
    except Exception as exc:
        logger.error("Scavio batch insert failed: %s", exc)
