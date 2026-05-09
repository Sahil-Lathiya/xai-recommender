# XAI Recommender

**Production-grade Explainable AI Product Recommendation System**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-FF6600?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PC9zdmc+)](https://xgboost.readthedocs.io)
[![SHAP](https://img.shields.io/badge/SHAP-0.45-FF4B4B)](https://shap.readthedocs.io)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![Deployed on DigitalOcean](https://img.shields.io/badge/Deployed-DigitalOcean-0080FF?logo=digitalocean&logoColor=white)](https://digitalocean.com)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

Every AI recommendation system answers *what*. This one also answers *why*.

XAI Recommender combines an XGBoost learning-to-rank model with SHAP TreeExplainer and GPT-4o-mini to deliver real-time product recommendations with mathematically exact feature-level explanations and plain-English summaries — deployed on a live cloud stack with a React dashboard.

**Live demo:** `https://your-app.vercel.app`  
**API docs:** `http://YOUR_DROPLET_IP:8000/docs`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (Vercel CDN)                     │
│                                                                 │
│  React 18 + Vite  ·  TailwindCSS  ·  Framer Motion            │
│  Zustand (state)  ·  React Query (cache)  ·  Recharts          │
│                                                                 │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│  │   Home   │  │   Dashboard    │  │   ProductDetail      │   │
│  │ 5 cards  │  │ KPIs + charts  │  │ Full explanation     │   │
│  └──────────┘  └────────────────┘  └──────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / Axios
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND API  (DigitalOcean Droplet, Frankfurt)     │
│                 FastAPI · Uvicorn 2 workers · Docker            │
│                                                                 │
│  POST /api/v1/recommendations   ──► ModelManager               │
│  GET  /api/v1/explain/{id}      ──► XAIEngine + LLMExplainer   │
│  GET  /api/v1/dashboard/stats   ──► DashboardRouter            │
│  GET  /health                   ──► HealthCheck                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    ML Layer                             │   │
│  │                                                         │   │
│  │  XGBRanker ──► SHAP TreeExplainer ──► LLM Explainer    │   │
│  │  (rank:pairwise, 200 trees, 8 features)   (GPT-4o-mini) │   │
│  │                                                         │   │
│  │  TTLCache ×4: recs(300s) · explain(3600s) ·            │   │
│  │              embed(3600s) · global(86400s)              │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ asyncpg / SQLAlchemy
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATABASE  (Supabase, West Europe)                  │
│              PostgreSQL · pgvector · Row Level Security         │
│                                                                 │
│  users  ·  products  ·  user_interactions                      │
│  recommendations (JSONB shap_values)  ·  explanations          │
└─────────────────────────────────────────────────────────────────┘

LOCAL TRAINING ONLY (never runs on server):
  py -3.11 scripts/train_local.py
  Amazon Reviews 2023 (50k rows) → 8 features → XGBRanker
  → saved_model.pkl + shap_background.pkl + feature_columns.pkl
```

---

## Features

| Feature | Detail |
|---------|--------|
| **XGBoost Ranking** | `XGBRanker` with `rank:pairwise`, 200 estimators, 8 hand-engineered features |
| **SHAP Explanations** | `TreeExplainer` — exact SHAP values, ~5ms per call, no approximation |
| **GPT-4o-mini Summaries** | LangChain LCEL chain, silent template fallback on any failure |
| **Counterfactual XAI** | Tells users what would change a recommendation score |
| **4-layer TTL Cache** | Recommendations, explanations, embeddings, global importance |
| **Live Dashboard** | KPI cards with count-up animation, area chart, pie chart, performance table |
| **Deterministic IDs** | `uuid5(user_id + product_id)` → same pair always hits the same cache key |
| **Always-On** | DigitalOcean Droplet, never sleeps, model loaded once at startup |
| **Hard Cost Cap** | OpenAI spend hard-capped at $10/month via config |

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.111 + Uvicorn (2 workers) |
| ML Model | XGBoost 2.0 `XGBRanker` (rank:pairwise) |
| Explainability | SHAP 0.45 `TreeExplainer` |
| LLM | LangChain 0.1 + `langchain-openai` + GPT-4o-mini |
| Database ORM | SQLAlchemy 2.0 async (asyncpg driver) |
| Database | Supabase PostgreSQL + pgvector |
| Caching | cachetools `TTLCache` ×4 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Config | Pydantic `BaseSettings` |
| Monitoring | psutil memory, request logging middleware |
| Containerisation | Docker multi-stage build (python:3.11-slim) |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 18 + Vite 5 |
| Styling | TailwindCSS 3.4 (dark mode default) |
| Animation | Framer Motion 11 |
| Charts | Recharts 2.12 (waterfall, area, bar, pie) |
| State | Zustand 4.5 with persist middleware |
| Data fetching | React Query (@tanstack/react-query v5) |
| HTTP client | Axios 1.6 |
| Icons | Lucide React |
| Deployment | Vercel (edge CDN, auto-deploy on push) |

### Infrastructure
| Service | Plan | Cost |
|---------|------|------|
| DigitalOcean Droplet | 2GB RAM / 1 CPU / 50GB SSD / Frankfurt | $12/mo |
| Supabase | Free tier (500MB DB, 2GB bandwidth) | $0 |
| Vercel | Free tier (unlimited bandwidth) | $0 |
| OpenAI API | Hard cap $10/mo (actual: <$1/mo with caching) | <$10/mo |
| **Total** | | **~$12/mo** |

> All infrastructure costs are covered by the **GitHub Student Developer Pack** ($200 DigitalOcean credit).

---

## The 8 Features

| Feature | Description | Source |
|---------|-------------|--------|
| `user_avg_rating` | User's mean rating across all interactions | User interaction history |
| `user_review_count` | Number of products the user has interacted with | User interaction history |
| `product_avg_rating` | Mean rating for this product across all users | Product aggregate |
| `product_review_count` | Total number of reviews (popularity signal) | Product aggregate |
| `category_match` | 1.0 if product matches user's favourite category | Derived |
| `price_percentile` | Product price rank within the candidate set (0–1) | Derived at inference time |
| `semantic_similarity` | Cosine similarity proxy between user taste and product | Derived from rating delta |
| `recency_score` | Exponential decay from user's last interaction date | Derived |

---

## Quick Start — Local Development

### Prerequisites
- Python 3.11 (`py -3.11 --version`)
- Node.js 18+ (`node --version`)
- Supabase project (free at [supabase.com](https://supabase.com))
- OpenAI API key ([platform.openai.com](https://platform.openai.com))

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/xai-recommender.git
cd xai-recommender
```

```powershell
# Backend environment
Copy-Item backend\.env.example backend\.env
# Edit backend\.env — fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_DB_URL, OPENAI_API_KEY

# Frontend environment
Copy-Item frontend\.env.example frontend\.env
# VITE_API_BASE_URL=http://localhost:8000
```

### 2. Run the database migration

1. Open [Supabase Dashboard](https://app.supabase.com) → SQL Editor → New query
2. Paste contents of `supabase/migrations/001_initial.sql` → Run

### 3. Train the model locally

```powershell
py -3.11 -m pip install -r backend/requirements.txt
py -3.11 -m pip install datasets sentence-transformers  # training extras only

py -3.11 scripts/train_local.py
# Outputs: backend/models/*.pkl (3 files)
# Runtime: ~5 min on a modern laptop
```

### 4. Seed demo data

```powershell
py -3.11 backend/data/seed_demo_data.py
# Seeds 20 products, 3 demo users, 30 interactions
# Generates real bcrypt hashes for Demo1234! password
```

### 5. Run the backend

```powershell
cd backend
py -3.11 -m uvicorn app.main:app --reload --port 8000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 6. Run the frontend

```powershell
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### 7. Run the tests

```powershell
py -3.11 -m pytest backend/tests/test_api.py -v
# 2 tests run without DB (health + LLM fallback)
# 10 tests run when backend/.env is configured
```

---

## Production Deployment

Full step-by-step guide: **[DEPLOYMENT.md](DEPLOYMENT.md)**

**TL;DR:**
```bash
# 1. Create DigitalOcean Droplet (Ubuntu 22.04, $12/mo, Frankfurt)
# 2. SSH in and run the deploy script
scp scripts/deploy.sh root@YOUR_IP:/tmp/deploy.sh
ssh root@YOUR_IP "bash /tmp/deploy.sh"

# 3. Upload trained model files from local machine
bash scripts/upload_models.sh YOUR_DROPLET_IP

# 4. Deploy frontend to Vercel
cd frontend && npx vercel --prod
# Set VITE_API_BASE_URL=http://YOUR_DROPLET_IP:8000
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — status, model_loaded, db_connected, memory_mb |
| `POST` | `/api/v1/recommendations` | Get ranked recommendations for a user |
| `GET` | `/api/v1/explain/{recommendation_id}` | Full SHAP + LLM explanation |
| `GET` | `/api/v1/explain/global/feature-importance` | Global XGBoost feature importances |
| `POST` | `/api/v1/users/register` | Register a new user |
| `POST` | `/api/v1/users/login` | Login, returns JWT |
| `POST` | `/api/v1/users/interaction` | Record a user interaction (view/click/purchase/rate) |
| `GET` | `/api/v1/users/{user_id}/profile` | User profile with interaction stats |
| `GET` | `/api/v1/dashboard/stats` | Live dashboard KPIs |
| `GET` | `/api/v1/dashboard/model-performance` | 7-day performance history |

Full interactive docs available at `/docs` (Swagger UI).

---

## Demo Users

Pre-seeded users for the showcase — login password for all: `Demo1234!`

| User | Email | Persona |
|------|-------|---------|
| Tech Enthusiast 💻 | `tech@demo.xai` | Heavy Electronics interactions → recommends gadgets |
| Book Lover 📚 | `books@demo.xai` | Heavy Books interactions → recommends non-fiction |
| Fashion Fan 👗 | `fashion@demo.xai` | Heavy Clothing interactions → recommends apparel |

---

## Project Structure

```
xai-recommender/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # recommendations, explanations, users, dashboard
│   │   ├── core/               # config (Pydantic Settings), security (JWT + bcrypt)
│   │   ├── db/                 # SQLAlchemy models, async engine, Supabase client
│   │   ├── ml/                 # recommender, xai_engine, llm_explainer, cache
│   │   ├── schemas/            # Pydantic v2 request/response models
│   │   └── main.py             # FastAPI app, lifespan, middleware
│   ├── data/
│   │   └── seed_demo_data.py   # Supabase seeder with real bcrypt hashes
│   ├── models/                 # *.pkl files (git-ignored, generated by training)
│   ├── tests/
│   │   └── test_api.py         # 12-test pytest suite
│   ├── Dockerfile              # Multi-stage: builder + runtime (non-root user)
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Charts/         # SHAPWaterfall, FeatureImportanceChart, RecommendationsOverTime, CategoryPie
│   │   │   ├── Dashboard/      # KPICard (count-up), ModelPerformanceTable
│   │   │   ├── ExplanationPanel/  # ExplanationPanel, ConfidenceRing, CounterfactualCard
│   │   │   ├── Navbar/         # Navbar with dark-mode toggle
│   │   │   └── ProductCard/    # ProductCard, SkeletonCard
│   │   ├── hooks/              # useRecommendations, useExplanation
│   │   ├── pages/              # Home, Dashboard, ProductDetail
│   │   ├── services/           # api.js (Axios instance)
│   │   └── store/              # appStore.js (Zustand)
│   ├── Dockerfile              # dev stage + nginx:alpine production stage
│   ├── nginx.conf
│   └── vercel.json
├── scripts/
│   ├── train_local.py          # LOCAL ONLY: py -3.11 scripts/train_local.py
│   ├── deploy.sh               # One-shot Droplet deploy script
│   └── upload_models.sh        # SCP model files to Droplet
├── supabase/
│   └── migrations/
│       └── 001_initial.sql     # Tables, indexes, RLS, 20 products, 3 users, 30 interactions
├── docker-compose.yml          # Local development
├── docker-compose.prod.yml     # Production (memory limits, healthchecks)
├── DEPLOYMENT.md               # Full deployment guide
├── DEMO_SCRIPT.md              # Showcase day script with employer Q&A
└── README.md
```

---

## Model Performance

| Metric | Score |
|--------|-------|
| NDCG@10 | *(run `py -3.11 scripts/train_local.py` to generate)* |
| Precision@5 | *(run `py -3.11 scripts/train_local.py` to generate)* |
| Training data | 50,000 Amazon Reviews 2023 (All_Beauty subset) |
| Features | 8 engineered features |
| Model | XGBRanker (rank:pairwise, 200 estimators, max_depth=6) |
| Inference latency | ~150ms fresh · <5ms cached |
| Memory footprint | ~620MB on 2GB Droplet |

---

## Key Design Decisions

**Why not sentence-transformers for embeddings at inference time?**  
They require 1GB+ of RAM and a 2–5 second cold-start. Instead, semantic similarity is computed as a fast rating-delta proxy at inference time. The pgvector column and index are in the schema for future upgrade.

**Why deterministic recommendation IDs?**  
`uuid5(NAMESPACE_URL, f"rec:{user_id}:{product_id}")` means the same user–product pair always produces the same UUID. This makes the explanation cache hit across requests and server restarts without any shared state.

**Why a template LLM fallback?**  
The LLM call wraps every possible exception. If OpenAI is down, rate-limited, or the hard cost cap is hit, the system generates a coherent two-sentence explanation from the SHAP reasons alone. Users never see an error.

**Why 4 separate TTL caches?**  
Different data has different staleness tolerance. Recommendations (300s) need to reflect recent interactions. Explanations (3600s) are deterministic once computed. Global feature importance (86400s) only changes when the model is retrained.

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by Sahil Dineshbhai Lathiya · MSc Business and Data Analytics · Ravensbourne University London · 2026*
