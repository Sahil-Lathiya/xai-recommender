"""
Migration: update amazon_url to use exact /dp/{asin} format for all products.

ASINs are extracted from the picsum image_url (seed = ASIN stored at fetch time).
Falls back to s?k= search URL only when ASIN cannot be extracted.

Run from repo root:
    py -3.11 backend/data/fix_amazon_urls.py
"""
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from supabase import create_client

SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_ID", "xairecommende-21")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

resp = supabase.table("products").select("id,name,image_url,amazon_url").execute()
products = resp.data or []

fixed_dp    = 0   # upgraded to /dp/{asin}
fixed_sk    = 0   # kept as s?k= (no ASIN available)
skipped     = 0   # already correct /dp/ URL

for p in products:
    image_url   = p.get("image_url") or ""
    current_url = p.get("amazon_url") or ""
    name        = p.get("name") or ""

    # Extract ASIN from picsum seed: https://picsum.photos/seed/{ASIN}/400/400
    asin_match = re.search(r'picsum\.photos/seed/([A-Z0-9]{10})/', image_url)

    if asin_match:
        asin    = asin_match.group(1)
        new_url = f"https://www.amazon.co.uk/dp/{asin}?tag={ASSOCIATE_TAG}"
    else:
        search_q = urllib.parse.quote_plus(name[:80])
        new_url  = f"https://www.amazon.co.uk/s?k={search_q}&tag={ASSOCIATE_TAG}"

    if current_url == new_url:
        skipped += 1
        continue

    supabase.table("products").update({"amazon_url": new_url}).eq("id", p["id"]).execute()

    if asin_match:
        fixed_dp += 1
        print(f"[dp/]  {name[:55]}")
    else:
        fixed_sk += 1
        print(f"[s?k=] {name[:55]}  (no ASIN in image_url)")

print(
    f"\nDone — {fixed_dp} updated to /dp/ASIN, "
    f"{fixed_sk} kept as s?k=, "
    f"{skipped} already correct."
)
