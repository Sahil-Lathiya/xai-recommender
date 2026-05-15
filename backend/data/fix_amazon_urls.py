"""
One-shot migration: fix /dp/{asin} amazon_url values to s?k= search URLs.

Run from repo root:
    py -3.11 backend/data/fix_amazon_urls.py
"""
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_ID", "xairecommende-21")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

resp = supabase.table("products").select("id,name,amazon_url").execute()
products = resp.data or []

fixed = 0
skipped = 0

for p in products:
    url = p.get("amazon_url") or ""
    if "/dp/" not in url and url.startswith("https://www.amazon.co.uk/s?k="):
        skipped += 1
        continue

    search_q = urllib.parse.quote_plus((p["name"] or "")[:80])
    new_url = f"https://www.amazon.co.uk/s?k={search_q}&tag={ASSOCIATE_TAG}"

    supabase.table("products").update({"amazon_url": new_url}).eq("id", p["id"]).execute()
    fixed += 1
    print(f"Fixed: {p['name'][:60]}")

print(f"\nDone — fixed {fixed} products, skipped {skipped} already correct.")
