# ============================================================
# XAI Recommender — Local Training Script
# Run ONLY on your laptop, NEVER on the production server.
#
# Command: py -3.11 scripts/train_local.py
#
# Requirements (install once):
#   py -3.11 -m pip install datasets sentence-transformers xgboost shap
#             scikit-learn pandas numpy joblib openai tqdm
#
# Outputs written to backend/models/:
#   saved_model.pkl        ← XGBoost ranker
#   shap_background.pkl    ← SHAP background dataset (50 kmeans points)
#   feature_columns.pkl    ← ordered list of 8 feature names
#   demo_products.json     ← 20 seed products for Supabase
#   demo_users.json        ← 3 demo user profiles for Supabase
# ============================================================

import json
import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "backend" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS_DIR / "saved_model.pkl"
SHAP_BACKGROUND_PATH = MODELS_DIR / "shap_background.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.pkl"
DEMO_PRODUCTS_PATH = MODELS_DIR / "demo_products.json"
DEMO_USERS_PATH = MODELS_DIR / "demo_users.json"

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

SUBSET_SIZE = 50_000


# ── Step 1: Load dataset ───────────────────────────────────────────────────────
def load_dataset() -> pd.DataFrame:
    logger.info("Loading Amazon Reviews 2023 dataset (All_Beauty subset)...")
    try:
        from datasets import load_dataset as hf_load
    except ImportError:
        logger.error("Install datasets: py -3.11 -m pip install datasets")
        sys.exit(1)

    dataset = hf_load(
        "McAuley-Lab/Amazon-Reviews-2023",
        "raw_review_All_Beauty",
        trust_remote_code=True,
        split="full",
    )

    df = dataset.to_pandas()
    logger.info("Full dataset size: %d rows", len(df))

    # Take a manageable subset
    if len(df) > SUBSET_SIZE:
        df = df.sample(n=SUBSET_SIZE, random_state=42).reset_index(drop=True)
        logger.info("Subset sampled: %d rows", len(df))

    # Normalise column names
    rename_map = {}
    if "overall" in df.columns:
        rename_map["overall"] = "rating"
    if "asin" in df.columns:
        rename_map["asin"] = "product_id"
    if "reviewerID" in df.columns:
        rename_map["reviewerID"] = "user_id"
    if "unixReviewTime" in df.columns:
        rename_map["unixReviewTime"] = "timestamp"
    if "rating" in df.columns and "overall" not in df.columns:
        pass  # already named correctly

    df = df.rename(columns=rename_map)

    required = {"user_id", "product_id", "rating"}
    missing = required - set(df.columns)
    if missing:
        logger.error("Dataset missing columns: %s. Available: %s", missing, df.columns.tolist())
        sys.exit(1)

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["user_id", "product_id", "rating"])
    df["rating"] = df["rating"].clip(1, 5)
    df["timestamp"] = pd.to_numeric(df.get("timestamp", pd.Series([0] * len(df))), errors="coerce").fillna(0)

    logger.info("Dataset loaded: %d reviews, %d unique users, %d unique products",
                len(df), df["user_id"].nunique(), df["product_id"].nunique())
    return df


# ── Step 2: Feature engineering ────────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    logger.info("Engineering features...")

    # User-level aggregates
    user_stats = df.groupby("user_id").agg(
        user_avg_rating=("rating", "mean"),
        user_review_count=("rating", "count"),
        user_last_ts=("timestamp", "max"),
    ).reset_index()

    # Product-level aggregates
    product_stats = df.groupby("product_id").agg(
        product_avg_rating=("rating", "mean"),
        product_review_count=("rating", "count"),
    ).reset_index()

    # Price simulation (no real price in this dataset — derive from product popularity)
    product_stats["price_raw"] = (
        product_stats["product_avg_rating"] * 20
        + np.random.RandomState(42).uniform(5, 200, len(product_stats))
    )
    cat_max = product_stats["price_raw"].max()
    cat_min = product_stats["price_raw"].min()
    product_stats["price_percentile"] = (
        (product_stats["price_raw"] - cat_min) / (cat_max - cat_min + 1e-9)
    )

    # Category assignment from product_id prefix (deterministic)
    categories = ["Electronics", "Books", "Clothing", "Home"]
    product_stats["category"] = product_stats["product_id"].apply(
        lambda pid: categories[hash(str(pid)) % 4]
    )

    # Join everything onto the interaction dataframe
    merged = df.merge(user_stats, on="user_id", how="left")
    merged = merged.merge(product_stats, on="product_id", how="left")

    # User's favourite category
    user_fav = merged.groupby(["user_id", "category"])["rating"].mean()
    user_fav_cat = user_fav.groupby("user_id").idxmax().apply(lambda x: x[1])
    user_fav_cat = user_fav_cat.reset_index()
    user_fav_cat.columns = ["user_id", "fav_category"]
    merged = merged.merge(user_fav_cat, on="user_id", how="left")
    merged["category_match"] = (merged["category"] == merged["fav_category"]).astype(float)

    # Recency score: exponential decay (more recent = higher score)
    ts_max = merged["timestamp"].max()
    ts_range = ts_max - merged["timestamp"].min() + 1
    merged["recency_score"] = np.exp(-3 * (ts_max - merged["timestamp"]) / ts_range)

    # Semantic similarity: cosine similarity proxy using rating correlation
    # (real embeddings would use OpenAI API — too expensive for 50k rows locally)
    # We use a deterministic proxy: normalised product rating similarity
    user_mean = merged["user_avg_rating"].clip(1, 5)
    product_mean = merged["product_avg_rating"].clip(1, 5)
    merged["semantic_similarity"] = 1 - abs(user_mean - product_mean) / 4.0

    # Target: binary relevance (rating >= 4 = relevant)
    merged["label"] = (merged["rating"] >= 4).astype(int)

    merged = merged.fillna(0)

    X = merged[FEATURE_COLUMNS].astype(float)
    y = merged["label"].values

    # Group sizes for XGBoost ranker (rows per user, in order)
    groups = merged.groupby("user_id", sort=False).size().values

    logger.info("Feature matrix shape: %s", X.shape)
    logger.info("Positive labels: %.1f%%", 100 * y.mean())
    return X, y, groups, merged


# ── Step 3: Train XGBoost Ranker ───────────────────────────────────────────────
def train_model(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray):
    logger.info("Training XGBoost Ranker...")
    try:
        import xgboost as xgb
        from sklearn.model_selection import GroupShuffleSplit
    except ImportError:
        logger.error("Install xgboost and scikit-learn: py -3.11 -m pip install xgboost scikit-learn")
        sys.exit(1)

    # Group-aware train/test split
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    user_ids_per_row = np.repeat(np.arange(len(groups)), groups)

    train_idx, test_idx = next(gss.split(X, y, groups=user_ids_per_row))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # Recompute group sizes for train/test sets
    train_user_ids = user_ids_per_row[train_idx]
    test_user_ids = user_ids_per_row[test_idx]
    _, train_group_counts = np.unique(train_user_ids, return_counts=True)
    _, test_group_counts = np.unique(test_user_ids, return_counts=True)

    model = xgb.XGBRanker(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        objective="rank:pairwise",
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )

    model.fit(
        X_train,
        y_train,
        group=train_group_counts,
        eval_set=[(X_test, y_test)],
        eval_group=[test_group_counts],
        verbose=False,
    )

    logger.info("Training complete. Evaluating...")
    return model, X_train, X_test, y_test, test_user_ids


# ── Step 4: Evaluate ───────────────────────────────────────────────────────────
def evaluate(model, X_test: pd.DataFrame, y_test: np.ndarray, test_user_ids: np.ndarray):
    try:
        from sklearn.metrics import ndcg_score
    except ImportError:
        logger.warning("sklearn ndcg_score not available — skipping evaluation")
        return 0.0, 0.0

    scores = model.predict(X_test)

    ndcg_scores = []
    precision_scores = []

    unique_users = np.unique(test_user_ids)
    for uid in unique_users:
        mask = test_user_ids == uid
        if mask.sum() < 2:
            continue
        y_true_u = y_test[mask].reshape(1, -1)
        y_score_u = scores[mask].reshape(1, -1)

        if y_true_u.sum() == 0:
            continue

        ndcg = ndcg_score(y_true_u, y_score_u, k=10)
        ndcg_scores.append(ndcg)

        top5_idx = np.argsort(scores[mask])[::-1][:5]
        p5 = y_test[mask][top5_idx].mean()
        precision_scores.append(p5)

    avg_ndcg = float(np.mean(ndcg_scores)) if ndcg_scores else 0.0
    avg_p5 = float(np.mean(precision_scores)) if precision_scores else 0.0

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  NDCG@10   : %.4f", avg_ndcg)
    logger.info("  Precision@5: %.4f", avg_p5)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("→ Fill these into DEMO_SCRIPT.md before the showcase!")

    return avg_ndcg, avg_p5


# ── Step 5: Save SHAP background ───────────────────────────────────────────────
def save_shap_background(model, X_train: pd.DataFrame):
    logger.info("Computing SHAP background dataset (kmeans, k=50)...")
    try:
        import shap
    except ImportError:
        logger.error("Install shap: py -3.11 -m pip install shap")
        sys.exit(1)

    background = shap.kmeans(X_train.values, 50)
    joblib.dump(background, SHAP_BACKGROUND_PATH)
    logger.info("SHAP background saved → %s", SHAP_BACKGROUND_PATH)
    return background


# ── Step 6: Save artifacts ─────────────────────────────────────────────────────
def save_artifacts(model, feature_columns: list):
    joblib.dump(model, MODEL_PATH)
    logger.info("Model saved → %s (%.1f MB)", MODEL_PATH, MODEL_PATH.stat().st_size / 1e6)

    joblib.dump(feature_columns, FEATURE_COLUMNS_PATH)
    logger.info("Feature columns saved → %s", FEATURE_COLUMNS_PATH)


# ── Step 7: Save demo data ─────────────────────────────────────────────────────
def save_demo_data():
    logger.info("Generating demo data...")

    demo_products = [
        # Electronics (8 products)
        {"id": "11111111-1111-1111-1111-111111111101", "name": "Sony WH-1000XM5 Wireless Headphones",
         "category": "Electronics", "price": 279.99, "rating": 4.8, "review_count": 12450,
         "description": "Industry-leading noise cancelling with Auto NC Optimizer. 30-hour battery life.",
         "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400"},
        {"id": "11111111-1111-1111-1111-111111111102", "name": "Apple iPad Pro 12.9-inch M2",
         "category": "Electronics", "price": 899.99, "rating": 4.7, "review_count": 8930,
         "description": "The ultimate iPad experience with M2 chip and Liquid Retina XDR display.",
         "image_url": "https://images.unsplash.com/photo-1544244015-0df4702503db?w=400"},
        {"id": "11111111-1111-1111-1111-111111111103", "name": "Samsung 4K OLED 55-inch Smart TV",
         "category": "Electronics", "price": 1299.99, "rating": 4.6, "review_count": 5670,
         "description": "Self-lit OLED pixels deliver perfect blacks and infinite contrast.",
         "image_url": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400"},
        {"id": "11111111-1111-1111-1111-111111111104", "name": "Logitech MX Master 3S Mouse",
         "category": "Electronics", "price": 89.99, "rating": 4.9, "review_count": 23100,
         "description": "8K DPI sensor, ultra-fast MagSpeed wheel, ergonomic design.",
         "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400"},
        {"id": "11111111-1111-1111-1111-111111111105", "name": "GoPro HERO12 Black Action Camera",
         "category": "Electronics", "price": 349.99, "rating": 4.5, "review_count": 6780,
         "description": "5.3K60 video, 27MP photos, HyperSmooth 6.0 stabilisation.",
         "image_url": "https://images.unsplash.com/photo-1617440168937-c6497eaa8db5?w=400"},
        {"id": "11111111-1111-1111-1111-111111111106", "name": "Anker 65W USB-C Charging Hub",
         "category": "Electronics", "price": 45.99, "rating": 4.7, "review_count": 18900,
         "description": "6-in-1 hub with 65W PD charging, 4K HDMI, USB-A 3.0.",
         "image_url": "https://images.unsplash.com/photo-1586772002130-e9a0e8c2f8b5?w=400"},
        {"id": "11111111-1111-1111-1111-111111111107", "name": "Kindle Paperwhite Signature Edition",
         "category": "Electronics", "price": 139.99, "rating": 4.8, "review_count": 31200,
         "description": "6.8-inch 300ppi display, auto-adjusting warm light, wireless charging.",
         "image_url": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=400"},
        {"id": "11111111-1111-1111-1111-111111111108", "name": "Bose QuietComfort 45 Earbuds",
         "category": "Electronics", "price": 229.99, "rating": 4.4, "review_count": 9870,
         "description": "True wireless earbuds with world-class noise cancellation.",
         "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400"},
        # Books (5 products)
        {"id": "11111111-1111-1111-1111-111111111201", "name": "Atomic Habits by James Clear",
         "category": "Books", "price": 14.99, "rating": 4.9, "review_count": 89400,
         "description": "Tiny changes, remarkable results. The definitive guide to habit formation.",
         "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400"},
        {"id": "11111111-1111-1111-1111-111111111202", "name": "The Psychology of Money by Morgan Housel",
         "category": "Books", "price": 13.99, "rating": 4.7, "review_count": 54300,
         "description": "Timeless lessons on wealth, greed, and happiness.",
         "image_url": "https://images.unsplash.com/photo-1554774853-719586f82d77?w=400"},
        {"id": "11111111-1111-1111-1111-111111111203", "name": "Deep Work by Cal Newport",
         "category": "Books", "price": 12.99, "rating": 4.6, "review_count": 38700,
         "description": "Rules for focused success in a distracted world.",
         "image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400"},
        {"id": "11111111-1111-1111-1111-111111111204", "name": "Thinking, Fast and Slow by Daniel Kahneman",
         "category": "Books", "price": 15.99, "rating": 4.5, "review_count": 71200,
         "description": "A landmark book in social thought exploring two systems of thinking.",
         "image_url": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400"},
        {"id": "11111111-1111-1111-1111-111111111205", "name": "Designing Data-Intensive Applications",
         "category": "Books", "price": 49.99, "rating": 4.9, "review_count": 12800,
         "description": "The principles behind reliable, scalable, and maintainable systems.",
         "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400"},
        # Clothing (4 products)
        {"id": "11111111-1111-1111-1111-111111111301", "name": "Nike Air Max 270 Trainers",
         "category": "Clothing", "price": 129.99, "rating": 4.6, "review_count": 45600,
         "description": "Max Air cushioning for all-day comfort. Breathable mesh upper.",
         "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400"},
        {"id": "11111111-1111-1111-1111-111111111302", "name": "Levi's 511 Slim Fit Jeans",
         "category": "Clothing", "price": 59.99, "rating": 4.4, "review_count": 32100,
         "description": "Classic slim fit with just the right amount of stretch.",
         "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400"},
        {"id": "11111111-1111-1111-1111-111111111303", "name": "The North Face Fleece Jacket",
         "category": "Clothing", "price": 99.99, "rating": 4.7, "review_count": 28900,
         "description": "Polartec fleece for warmth and comfort in cold conditions.",
         "image_url": "https://images.unsplash.com/photo-1604644401890-0bd678c83788?w=400"},
        {"id": "11111111-1111-1111-1111-111111111304", "name": "Uniqlo HEATTECH Ultra Warm Crew Neck",
         "category": "Clothing", "price": 29.99, "rating": 4.5, "review_count": 19800,
         "description": "2.25× warmer than regular HEATTECH with a soft, stretchy feel.",
         "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400"},
        # Home (3 products)
        {"id": "11111111-1111-1111-1111-111111111401", "name": "Dyson V15 Detect Cordless Vacuum",
         "category": "Home", "price": 649.99, "rating": 4.7, "review_count": 15600,
         "description": "Laser dust detection reveals microscopic dust. HEPA filtration.",
         "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400"},
        {"id": "11111111-1111-1111-1111-111111111402", "name": "Instant Pot Duo 7-in-1 Pressure Cooker",
         "category": "Home", "price": 79.99, "rating": 4.8, "review_count": 98700,
         "description": "7-in-1 multi-cooker replaces 7 kitchen appliances.",
         "image_url": "https://images.unsplash.com/photo-1585515320310-259814833e62?w=400"},
        {"id": "11111111-1111-1111-1111-111111111403", "name": "Philips Hue White & Colour Smart Bulbs (4-pack)",
         "category": "Home", "price": 59.99, "rating": 4.6, "review_count": 34500,
         "description": "16 million colours, voice control compatible, dimmable.",
         "image_url": "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400"},
    ]

    demo_users = [
        {
            "id": "22222222-2222-2222-2222-222222222201",
            "email": "tech@demo.xai",
            "name": "Tech Enthusiast",
            "password": "Demo1234!",
            "favourite_category": "Electronics",
            "description": "Loves the latest gadgets, always researching tech reviews.",
        },
        {
            "id": "22222222-2222-2222-2222-222222222202",
            "email": "books@demo.xai",
            "name": "Book Lover",
            "password": "Demo1234!",
            "favourite_category": "Books",
            "description": "Voracious reader across non-fiction, productivity, and science.",
        },
        {
            "id": "22222222-2222-2222-2222-222222222203",
            "email": "fashion@demo.xai",
            "name": "Fashion Fan",
            "password": "Demo1234!",
            "favourite_category": "Clothing",
            "description": "Style-conscious shopper who values quality and brand reputation.",
        },
    ]

    with open(DEMO_PRODUCTS_PATH, "w", encoding="utf-8") as f:
        json.dump(demo_products, f, indent=2)
    logger.info("Demo products saved → %s (%d products)", DEMO_PRODUCTS_PATH, len(demo_products))

    with open(DEMO_USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(demo_users, f, indent=2)
    logger.info("Demo users saved → %s (%d users)", DEMO_USERS_PATH, len(demo_users))


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  XAI Recommender — Local Training Pipeline  ║")
    logger.info("║  Python %s                               ║", sys.version[:6])
    logger.info("╚══════════════════════════════════════════════╝")
    logger.info("Output directory: %s", MODELS_DIR)

    # 1. Load dataset
    df = load_dataset()

    # 2. Feature engineering
    X, y, groups, merged = engineer_features(df)

    # 3. Train model
    model, X_train, X_test, y_test, test_user_ids = train_model(X, y, groups)

    # 4. Evaluate
    ndcg, p5 = evaluate(model, X_test, y_test, test_user_ids)

    # 5. Save SHAP background
    save_shap_background(model, X_train)

    # 6. Save model artifacts
    save_artifacts(model, FEATURE_COLUMNS)

    # 7. Save demo data
    save_demo_data()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║  Training complete! Next steps:             ║")
    logger.info("║                                             ║")
    logger.info("║  1. Upload pkl files to Droplet:            ║")
    logger.info("║     scp backend/models/*.pkl                ║")
    logger.info("║         root@DROPLET_IP:~/xai-recommender/ ║")
    logger.info("║         backend/models/                     ║")
    logger.info("║                                             ║")
    logger.info("║  2. Seed Supabase:                          ║")
    logger.info("║     py -3.11 backend/data/seed_demo_data.py║")
    logger.info("║                                             ║")
    logger.info("║  3. Fill DEMO_SCRIPT.md with these scores: ║")
    logger.info("║     NDCG@10    = %.4f                  ║", ndcg)
    logger.info("║     Precision@5 = %.4f                  ║", p5)
    logger.info("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
