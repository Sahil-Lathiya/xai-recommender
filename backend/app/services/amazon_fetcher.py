"""
Fetch real Amazon UK products via Scavio API and upsert into Supabase.

Runs once on startup only — no recurring schedule (Scavio free tier: 250 credits/month).
Manual refresh: POST /api/v1/admin/refresh-products

Image strategy: use picsum.photos/seed/{asin}/400/400
  Amazon CDN (m.media-amazon.com) blocks cross-origin loads — never store those URLs.

Amazon URL: https://www.amazon.co.uk/s?k={encoded_name}&tag=xairecommende-21
  Never use /dp/{asin} — ASINs are US-based and 404 on the UK site.
"""
import asyncio
import logging
import urllib.parse
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SEARCH_QUERIES: dict[str, list[str]] = {
    "Electronics": [
        "wireless earbuds",
        "laptop stand",
        "mechanical keyboard",
        "smart watch",
    ],
    "Books": [
        "python programming book",
        "machine learning book",
        "productivity book",
    ],
    "Clothing": [
        "men running shoes",
        "women casual jacket",
        "gym hoodie",
    ],
    "Home": [
        "LED desk lamp",
        "coffee maker",
        "air purifier",
    ],
}

_SCAVIO_URL  = "https://api.scavio.dev/api/v1/amazon/search"
_MAX_PER_QUERY = 3


async def fetch_and_upsert_products() -> None:
    """
    Fetch real Amazon products for all categories and upsert into Supabase.
    New products are inserted; existing products (matched by name) get their
    price, rating, review_count, and amazon_url refreshed.
    Never raises — all errors are caught and logged.
    """
    if not settings.SCAVIO_API_KEY:
        logger.warning("SCAVIO_API_KEY not set — skipping Amazon product fetch")
        return

    try:
        from app.db.database import get_supabase
        supabase = get_supabase()
    except Exception as exc:
        logger.warning("Supabase client unavailable for product fetch: %s", exc)
        return

    # Load existing products: name → id mapping for upsert-with-update
    try:
        existing_resp = await asyncio.to_thread(
            lambda: supabase.table("products").select("id,name").execute()
        )
        existing_by_name: dict[str, str] = {
            row["name"].lower().strip(): row["id"]
            for row in (existing_resp.data or [])
        }
        logger.info(
            "Amazon fetch starting — %d products already in DB",
            len(existing_by_name),
        )
    except Exception as exc:
        logger.warning("Could not load existing product names: %s", exc)
        existing_by_name = {}

    headers = {
        "Authorization": f"Bearer {settings.SCAVIO_API_KEY}",
        "Content-Type": "application/json",
    }

    upsert_rows: list[dict] = []
    credits_ok = True

    async with httpx.AsyncClient(timeout=30.0) as client:
        for category, queries in SEARCH_QUERIES.items():
            if not credits_ok:
                break

            for query in queries:
                if not credits_ok:
                    break

                try:
                    resp = await client.post(
                        _SCAVIO_URL,
                        headers=headers,
                        json={
                            "query":    query,
                            "domain":   "co.uk",
                            "currency": "GBP",
                            "sort_by":  "average_review",
                            "pages":    1,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    # Guard credits — stop all fetching if running low
                    credits_remaining = data.get("credits_remaining", 999)
                    if credits_remaining < 20:
                        logger.warning(
                            "Scavio credits low (%d remaining) — stopping fetch early",
                            credits_remaining,
                        )
                        credits_ok = False
                        break

                    products = data.get("data", {}).get("products", [])
                    fetched = 0

                    for p in products[:_MAX_PER_QUERY]:
                        asin = (p.get("asin") or "").strip()
                        if not asin:
                            continue

                        name = (p.get("title") or "").strip()[:500]
                        if not name:
                            continue

                        try:
                            price = round(float(p.get("price") or 0), 2)
                        except (TypeError, ValueError):
                            continue
                        if price <= 0:
                            continue

                        rating       = round(min(5.0, float(p.get("rating") or 0.0)), 2)
                        review_count = int(p.get("reviews_count") or 0)

                        # Deterministic image: same ASIN → same image every time
                        image_url = f"https://picsum.photos/seed/{asin}/400/400"
                        # Search URL — never /dp/{asin} which 404s for US ASINs on UK site
                        search_q  = urllib.parse.quote_plus(name[:80])
                        amazon_url = (
                            f"https://www.amazon.co.uk/s?k={search_q}"
                            f"&tag={settings.AMAZON_ASSOCIATE_ID}"
                        )

                        name_key = name.lower()
                        # Reuse existing id so the upsert updates rather than duplicates
                        product_id = existing_by_name.get(name_key) or str(uuid.uuid4())

                        upsert_rows.append({
                            "id":           product_id,
                            "name":         name,
                            "category":     category,
                            "price":        price,
                            "rating":       rating,
                            "review_count": review_count,
                            "description":  name[:500],
                            "image_url":    image_url,
                            "amazon_url":   amazon_url,
                        })
                        existing_by_name[name_key] = product_id
                        fetched += 1

                    logger.info(
                        "Scavio query %r (%s): %d products queued (credits left: %d)",
                        query, category, fetched, credits_remaining,
                    )

                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Scavio HTTP %d for query %r (%s)",
                        exc.response.status_code, query, category,
                    )
                except Exception as exc:
                    logger.warning(
                        "Scavio error for query %r (%s): %s",
                        query, category, exc,
                    )

                # Respect Scavio rate limit (free tier: ~1 req/s)
                await asyncio.sleep(1.2)

    if not upsert_rows:
        logger.info("Amazon fetch complete — no products to upsert")
        return

    try:
        await asyncio.to_thread(
            lambda: supabase.table("products")
            .upsert(upsert_rows, on_conflict="id")
            .execute()
        )
        logger.info(
            "Amazon fetch complete — %d products upserted across %d categories",
            len(upsert_rows),
            len({r["category"] for r in upsert_rows}),
        )
    except Exception as exc:
        logger.error("Amazon batch upsert failed: %s", exc)
