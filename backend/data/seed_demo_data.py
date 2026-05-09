# ============================================================
# XAI Recommender — Demo Data Seeder
#
# Run ONCE locally after the SQL migration:
#   py -3.11 backend/data/seed_demo_data.py
#
# What this script does:
#   1. Generates real bcrypt password hashes for all demo users
#   2. Upserts users with correct hashed passwords (fixes SQL placeholders)
#   3. Upserts all 20 products (idempotent — safe to run again)
#   4. Inserts 30 demo interactions if not already present
#
# Prerequisites:
#   py -3.11 -m pip install supabase passlib[bcrypt] python-dotenv
#
# Environment variables (set in backend/.env):
#   SUPABASE_URL  — your Supabase project URL
#   SUPABASE_KEY  — your Supabase SERVICE ROLE key (not anon key)
# ============================================================

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Load env ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = REPO_ROOT / "backend" / ".env"

if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    logger.info("Loaded env from %s", ENV_FILE)
else:
    logger.warning(".env not found at %s — relying on system env vars", ENV_FILE)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error(
        "SUPABASE_URL and SUPABASE_KEY must be set. "
        "Copy backend/.env.example to backend/.env and fill in your values."
    )
    sys.exit(1)

# ── Supabase client ───────────────────────────────────────────────────────────
try:
    from supabase import create_client
except ImportError:
    logger.error("Install supabase: py -3.11 -m pip install supabase")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Bcrypt hasher ─────────────────────────────────────────────────────────────
try:
    import bcrypt as _bcrypt
except ImportError:
    logger.error("Install bcrypt: py -3.11 -m pip install bcrypt")
    sys.exit(1)


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(12)).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())

DEMO_PASSWORD = "Demo1234!"


# ── Data ──────────────────────────────────────────────────────────────────────

DEMO_USERS = [
    {
        "id": "22222222-2222-2222-2222-222222222201",
        "email": "tech@demo.xai",
        "name": "Tech Enthusiast",
    },
    {
        "id": "22222222-2222-2222-2222-222222222202",
        "email": "books@demo.xai",
        "name": "Book Lover",
    },
    {
        "id": "22222222-2222-2222-2222-222222222203",
        "email": "fashion@demo.xai",
        "name": "Fashion Fan",
    },
]

DEMO_PRODUCTS = [
    # Electronics
    {"id": "11111111-1111-1111-1111-111111111101", "name": "Sony WH-1000XM5 Wireless Headphones",
     "category": "Electronics", "price": 279.00, "rating": 4.7, "review_count": 23100,
     "description": "Industry-leading noise cancelling with Auto NC Optimizer. 30-hour battery life.",
     "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/dp/B09XS7JWHH"},
    {"id": "11111111-1111-1111-1111-111111111102", "name": "Apple iPad Pro 12.9-inch M2",
     "category": "Electronics", "price": 899.00, "rating": 4.8, "review_count": 8930,
     "description": "The ultimate iPad experience with M2 chip and Liquid Retina XDR display.",
     "image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Apple+iPad+Pro+12.9+M2+2022"},
    {"id": "11111111-1111-1111-1111-111111111103", "name": "Samsung 4K OLED 55-inch Smart TV",
     "category": "Electronics", "price": 1299.00, "rating": 4.5, "review_count": 5670,
     "description": "Self-lit OLED pixels deliver perfect blacks and infinite contrast.",
     "image_url": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Samsung+55+inch+4K+OLED+Smart+TV"},
    {"id": "11111111-1111-1111-1111-111111111104", "name": "Logitech MX Master 3S Mouse",
     "category": "Electronics", "price": 62.99, "rating": 4.7, "review_count": 23100,
     "description": "8K DPI sensor, ultra-fast MagSpeed wheel, ergonomic design.",
     "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/dp/B09HM94VDS"},
    {"id": "11111111-1111-1111-1111-111111111105", "name": "GoPro HERO12 Black Action Camera",
     "category": "Electronics", "price": 349.99, "rating": 4.5, "review_count": 6780,
     "description": "5.3K60 video, 27MP photos, HyperSmooth 6.0 stabilisation.",
     "image_url": "https://picsum.photos/seed/gopro12/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=GoPro+HERO12+Black&i=electronics"},
    {"id": "11111111-1111-1111-1111-111111111106", "name": "Anker 65W USB-C Charging Hub",
     "category": "Electronics", "price": 45.99, "rating": 4.7, "review_count": 18900,
     "description": "6-in-1 hub with 65W PD charging, 4K HDMI, USB-A 3.0.",
     "image_url": "https://images.unsplash.com/photo-1625895197185-efcec01cffe0?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Anker+65W+USB-C+charging+hub"},
    {"id": "11111111-1111-1111-1111-111111111107", "name": "Kindle Paperwhite Signature Edition",
     "category": "Electronics", "price": 139.99, "rating": 4.7, "review_count": 31200,
     "description": "6.8-inch 300ppi display, auto-adjusting warm light, wireless charging.",
     "image_url": "https://images.unsplash.com/photo-1592496431122-2349e0fbc666?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/dp/B09TMF6742"},
    {"id": "11111111-1111-1111-1111-111111111108", "name": "Bose QuietComfort 45 Earbuds",
     "category": "Electronics", "price": 229.99, "rating": 4.4, "review_count": 9870,
     "description": "True wireless earbuds with world-class noise cancellation.",
     "image_url": "https://picsum.photos/seed/bose45/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=Bose+QuietComfort+45+Earbuds&i=electronics"},
    {"id": "11111111-1111-1111-1111-111111111109", "name": "Apple Watch Series 9",
     "category": "Electronics", "price": 379.00, "rating": 4.8, "review_count": 12400,
     "description": "Advanced health sensors, Double Tap gesture, Always-On Retina display.",
     "image_url": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Apple+Watch+Series+9+GPS"},
    # Books
    {"id": "11111111-1111-1111-1111-111111111201", "name": "Atomic Habits by James Clear",
     "category": "Books", "price": 14.99, "rating": 4.8, "review_count": 89400,
     "description": "Tiny changes, remarkable results. The definitive guide to habit formation.",
     "image_url": "https://covers.openlibrary.org/b/isbn/1847941834-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/1847941834"},
    {"id": "11111111-1111-1111-1111-111111111202", "name": "The Psychology of Money by Morgan Housel",
     "category": "Books", "price": 13.99, "rating": 4.7, "review_count": 54300,
     "description": "Timeless lessons on wealth, greed, and happiness.",
     "image_url": "https://covers.openlibrary.org/b/isbn/0857197681-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/0857197681"},
    {"id": "11111111-1111-1111-1111-111111111203", "name": "Deep Work by Cal Newport",
     "category": "Books", "price": 12.99, "rating": 4.6, "review_count": 38700,
     "description": "Rules for focused success in a distracted world.",
     "image_url": "https://covers.openlibrary.org/b/isbn/0349411905-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/0349411905"},
    {"id": "11111111-1111-1111-1111-111111111204", "name": "Thinking, Fast and Slow by Daniel Kahneman",
     "category": "Books", "price": 9.99, "rating": 4.7, "review_count": 71200,
     "description": "A landmark book in social thought exploring two systems of thinking.",
     "image_url": "https://covers.openlibrary.org/b/isbn/0141033576-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/0141033576"},
    {"id": "11111111-1111-1111-1111-111111111205", "name": "Designing Data-Intensive Applications",
     "category": "Books", "price": 49.99, "rating": 4.6, "review_count": 12800,
     "description": "The principles behind reliable, scalable, and maintainable systems.",
     "image_url": "https://covers.openlibrary.org/b/isbn/1449373321-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/1449373321"},
    {"id": "11111111-1111-1111-1111-111111111206", "name": "How Innovation Works by Matt Ridley",
     "category": "Books", "price": 10.99, "rating": 4.5, "review_count": 8200,
     "description": "How innovation emerges from combining ideas in unexpected ways.",
     "image_url": "https://covers.openlibrary.org/b/isbn/0008264546-L.jpg",
     "amazon_url": "https://www.amazon.co.uk/dp/0008264546"},
    # Clothing
    {"id": "11111111-1111-1111-1111-111111111301", "name": "Nike Air Max 270 Trainers",
     "category": "Clothing", "price": 129.99, "rating": 4.6, "review_count": 45600,
     "description": "Max Air cushioning for all-day comfort. Breathable mesh upper.",
     "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Nike+Air+Max+270&i=fashion"},
    {"id": "11111111-1111-1111-1111-111111111302", "name": "Levi's 501 Original Jeans",
     "category": "Clothing", "price": 59.99, "rating": 4.4, "review_count": 32100,
     "description": "The original straight fit since 1873. Classic 5-pocket styling.",
     "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Levis+501+original+jeans&i=fashion"},
    {"id": "11111111-1111-1111-1111-111111111303", "name": "The North Face Fleece Jacket",
     "category": "Clothing", "price": 99.99, "rating": 4.7, "review_count": 28900,
     "description": "Polartec fleece for warmth and comfort in cold conditions.",
     "image_url": "https://images.unsplash.com/photo-1544923246-77307dd654cb?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=North+Face+fleece+jacket&i=fashion"},
    {"id": "11111111-1111-1111-1111-111111111304", "name": "Uniqlo HEATTECH Ultra Warm Crew Neck",
     "category": "Clothing", "price": 29.99, "rating": 4.5, "review_count": 19800,
     "description": "2.25x warmer than regular HEATTECH with a soft, stretchy feel.",
     "image_url": "https://picsum.photos/seed/uniqloHEATTECH/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=Uniqlo+HEATTECH+Ultra+Warm&i=fashion-intl-ship"},
    {"id": "11111111-1111-1111-1111-111111111305", "name": "Adidas Ultraboost 22 Running Shoes",
     "category": "Clothing", "price": 149.99, "rating": 4.6, "review_count": 31500,
     "description": "Responsive BOOST midsole, Primeknit+ upper, continental rubber outsole.",
     "image_url": "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=400&q=80",
     "amazon_url": "https://www.amazon.co.uk/s?k=Adidas+Ultraboost+22&i=fashion"},
    # Home
    {"id": "11111111-1111-1111-1111-111111111401", "name": "Dyson V15 Detect Cordless Vacuum",
     "category": "Home", "price": 649.99, "rating": 4.7, "review_count": 15600,
     "description": "Laser dust detection reveals microscopic dust. HEPA filtration.",
     "image_url": "https://picsum.photos/seed/dysonv15/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=Dyson+V15+Detect+Cordless+Vacuum&i=kitchen"},
    {"id": "11111111-1111-1111-1111-111111111402", "name": "Instant Pot Duo 7-in-1 Pressure Cooker",
     "category": "Home", "price": 79.99, "rating": 4.8, "review_count": 98700,
     "description": "7-in-1 multi-cooker replaces 7 kitchen appliances.",
     "image_url": "https://picsum.photos/seed/instantpot/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=Instant+Pot+Duo+7+in+1+Pressure+Cooker&i=kitchen"},
    {"id": "11111111-1111-1111-1111-111111111403", "name": "Philips Hue White & Colour Smart Bulbs (4-pack)",
     "category": "Home", "price": 59.99, "rating": 4.6, "review_count": 34500,
     "description": "16 million colours, voice control compatible, dimmable.",
     "image_url": "https://picsum.photos/seed/philipshue/400/400",
     "amazon_url": "https://www.amazon.co.uk/s?k=Philips+Hue+White+Colour+Smart+Bulbs&i=lighting"},
]

DEMO_INTERACTIONS = [
    # ── Tech Enthusiast — strong Electronics focus ─────────────────────────────
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111101", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111102", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111104", "action_type": "rate",     "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111107", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111103", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111105", "action_type": "rate",     "rating": 4.0},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111106", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111108", "action_type": "rate",     "rating": 4.0},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111205", "action_type": "rate",     "rating": 3.5},
    {"user_id": "22222222-2222-2222-2222-222222222201", "product_id": "11111111-1111-1111-1111-111111111402", "action_type": "view",     "rating": None},
    # ── Book Lover — strong Books focus ───────────────────────────────────────
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111201", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111202", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111203", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111204", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111205", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111107", "action_type": "rate",     "rating": 4.0},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111101", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111402", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111403", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222202", "product_id": "11111111-1111-1111-1111-111111111304", "action_type": "view",     "rating": None},
    # ── Fashion Fan — strong Clothing focus ───────────────────────────────────
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111301", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111302", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111303", "action_type": "purchase", "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111304", "action_type": "purchase", "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111301", "action_type": "rate",     "rating": 5.0},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111302", "action_type": "rate",     "rating": 4.5},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111401", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111402", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111201", "action_type": "view",     "rating": None},
    {"user_id": "22222222-2222-2222-2222-222222222203", "product_id": "11111111-1111-1111-1111-111111111104", "action_type": "view",     "rating": None},
]


# ── Seeder functions ──────────────────────────────────────────────────────────

def seed_products() -> None:
    logger.info("Upserting %d products (with amazon_url + corrected data)...", len(DEMO_PRODUCTS))
    resp = client.table("products").upsert(DEMO_PRODUCTS, on_conflict="id").execute()
    logger.info("Products upserted: %d rows", len(resp.data) if resp.data else 0)


def seed_users() -> None:
    logger.info("Generating bcrypt hashes for %d demo users (password: %s)...",
                len(DEMO_USERS), DEMO_PASSWORD)
    hashed = _hash_password(DEMO_PASSWORD)
    logger.info("Hash generated: %s", hashed[:20] + "...")

    users_with_passwords = [
        {**u, "hashed_password": hashed}
        for u in DEMO_USERS
    ]

    resp = client.table("users").upsert(
        users_with_passwords,
        on_conflict="id",
    ).execute()
    logger.info("Users seeded: %d rows", len(resp.data) if resp.data else 0)

    # Verify login works
    for u in DEMO_USERS:
        row = client.table("users").select("hashed_password").eq("id", u["id"]).execute()
        if row.data:
            stored_hash = row.data[0]["hashed_password"]
            ok = _verify_password(DEMO_PASSWORD, stored_hash)
            logger.info("  ✓ Login check for %-20s: %s", u["name"], "PASS" if ok else "FAIL")
        else:
            logger.warning("  ✗ User not found in DB: %s", u["name"])


def seed_interactions() -> None:
    logger.info("Seeding %d interactions...", len(DEMO_INTERACTIONS))
    # Remove None ratings for Supabase (it expects null, not None string)
    clean = [
        {k: v for k, v in row.items() if v is not None}
        for row in DEMO_INTERACTIONS
    ]
    resp = client.table("user_interactions").insert(clean, count="exact").execute()
    logger.info("Interactions inserted: %s rows", resp.count if hasattr(resp, "count") else "?")


def fix_images() -> None:
    """Update the three image URLs that changed (idempotent upsert)."""
    fixes = [
        {"id": "11111111-1111-1111-1111-111111111105",
         "image_url": "https://images.unsplash.com/photo-1516567727095-d04e4b8b5b3b?w=400"},
        {"id": "11111111-1111-1111-1111-111111111106",
         "image_url": "https://images.unsplash.com/photo-1591370874773-6702e8f12fd8?w=400"},
        {"id": "11111111-1111-1111-1111-111111111403",
         "image_url": "https://images.unsplash.com/photo-1565814329452-e1efa11c5b89?w=400"},
    ]
    for fix in fixes:
        client.table("products").update(
            {"image_url": fix["image_url"]}
        ).eq("id", fix["id"]).execute()
    logger.info("Image URLs updated for %d products", len(fixes))


def reseed_interactions() -> None:
    """Delete existing demo-user interactions and re-insert with updated set."""
    logger.info("Clearing existing interactions for demo users...")
    for user in DEMO_USERS:
        client.table("user_interactions").delete().eq(
            "user_id", user["id"]
        ).execute()
    logger.info("Cleared. Re-inserting %d interactions...", len(DEMO_INTERACTIONS))
    clean = [
        {k: v for k, v in row.items() if v is not None}
        for row in DEMO_INTERACTIONS
    ]
    resp = client.table("user_interactions").insert(clean, count="exact").execute()
    logger.info("Interactions inserted: %s rows", resp.count if hasattr(resp, "count") else "?")


def verify_counts() -> None:
    logger.info("── Final verification ──")
    for table in ["products", "users", "user_interactions"]:
        resp = client.table(table).select("id", count="exact").execute()
        count = resp.count if hasattr(resp, "count") else len(resp.data or [])
        logger.info("  %-25s : %d rows", table, count)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  XAI Recommender — Demo Data Seeder         ║")
    logger.info("║  Supabase: %s  ║", SUPABASE_URL[:35])
    logger.info("╚══════════════════════════════════════════════╝")

    seed_products()   # upserts all products with amazon_url + corrected ratings/prices
    seed_users()

    try:
        reseed_interactions()
    except Exception as exc:
        logger.warning("Interactions reseed failed: %s", exc)

    verify_counts()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  Seeding complete!                          ║")
    logger.info("║                                             ║")
    logger.info("║  Demo login credentials:                    ║")
    logger.info("║  Email:    tech@demo.xai                    ║")
    logger.info("║  Password: Demo1234!                        ║")
    logger.info("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
