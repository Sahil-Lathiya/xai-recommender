# Deployment Guide — XAI Recommender

Full production deployment: **DigitalOcean Droplet** (backend API) + **Vercel** (frontend) + **Supabase** (database).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Train the Model Locally](#2-train-the-model-locally)
3. [Supabase — Run Migration](#3-supabase--run-migration)
4. [DigitalOcean — Create Droplet](#4-digitalocean--create-droplet)
5. [DigitalOcean — Configure Environment](#5-digitalocean--configure-environment)
6. [DigitalOcean — Deploy Backend](#6-digitalocean--deploy-backend)
7. [Upload Model Files](#7-upload-model-files)
8. [Seed Demo Data](#8-seed-demo-data)
9. [Vercel — Deploy Frontend](#9-vercel--deploy-frontend)
10. [Smoke Test](#10-smoke-test)
11. [Local Development](#11-local-development)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.11 | `py -3.11 --version` |
| Node.js | 18+ | `node --version` |
| Git | any | `git --version` |
| SSH client | any | `ssh -V` |
| Vercel CLI (optional) | latest | `npm i -g vercel` |

**Accounts needed:**
- [DigitalOcean](https://cloud.digitalocean.com) — activate GitHub Student Pack ($200 credit, covers ~16 months at $12/mo)
- [Supabase](https://app.supabase.com) — free tier, project already created: `kpkpxvjnaptduudgbfcq`
- [Vercel](https://vercel.com) — free tier
- [OpenAI](https://platform.openai.com) — set hard cap to $10/month in billing settings

---

## 2. Train the Model Locally

> **Important:** Training runs on your local machine only. The production server does inference only.

```powershell
# From project root
py -3.11 -m pip install -r backend/requirements.txt
py -3.11 -m pip install datasets sentence-transformers  # training extras only

py -3.11 scripts/train_local.py
```

Expected output:
```
Downloading Amazon Reviews 2023 (All_Beauty)...
Engineering 8 features...
Training XGBRanker (200 estimators)...
NDCG@10: 0.XXXX
Precision@5: 0.XXXX
Saved: backend/models/saved_model.pkl
Saved: backend/models/shap_background.pkl
Saved: backend/models/feature_columns.pkl
Saved: backend/data/demo_products.json (20 products)
Saved: backend/data/demo_users.json (3 users)
```

After training, update the NDCG score in [backend/app/api/routes/dashboard.py](backend/app/api/routes/dashboard.py):
```python
_MODEL_NDCG_AT_10: float = 0.XXXX   # ← paste your actual score
_MODEL_PRECISION_AT_5: float = 0.XXXX
```

---

## 3. Supabase — Run Migration

1. Open [Supabase Dashboard](https://app.supabase.com/project/kpkpxvjnaptduudgbfcq)
2. Go to **SQL Editor** → **New query**
3. Paste the entire contents of [supabase/migrations/001_initial.sql](supabase/migrations/001_initial.sql)
4. Click **Run** — you should see `Success. No rows returned`

This creates all tables, indexes, RLS policies, and seeds 20 products + 3 demo users.

**Verify in Table Editor:** You should see `users`, `products`, `user_interactions`, `recommendations`, `explanations` tables with data.

---

## 4. DigitalOcean — Create Droplet

1. Log in to DigitalOcean
2. Create Droplet → **Choose Region:** Frankfurt (closest to Supabase West Europe)
3. **Image:** Ubuntu 22.04 LTS x64
4. **Size:** Basic → Regular → **$12/mo** (2GB RAM / 1 CPU / 50GB SSD)
5. **Authentication:** SSH Key (add your public key)
6. **Hostname:** `xai-recommender`
7. Click **Create Droplet**

Note your Droplet IP — you'll use it throughout.

---

## 5. DigitalOcean — Configure Environment

SSH into your Droplet and create the environment file:

```bash
ssh root@YOUR_DROPLET_IP

# Create app directory
mkdir -p /opt/xai-recommender/backend/models

# Create the environment file
nano /opt/xai-recommender/backend/.env
```

Paste and fill in all values:

```env
# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL=https://kpkpxvjnaptduudgbfcq.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_DB_URL=postgresql+asyncpg://postgres:YOUR_DB_PASSWORD@db.kpkpxvjnaptduudgbfcq.supabase.co:5432/postgres

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MAX_TOKENS=150
OPENAI_HARD_LIMIT_USD=10

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY=YOUR_RANDOM_32_CHAR_STRING_HERE
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── App ───────────────────────────────────────────────────────────────────────
ENVIRONMENT=production
CORS_ORIGINS=https://YOUR_APP_NAME.vercel.app
PORT=8000
LOG_LEVEL=INFO

# ── Model paths ───────────────────────────────────────────────────────────────
MODEL_PATH=./models/saved_model.pkl
SHAP_BACKGROUND_PATH=./models/shap_background.pkl
FEATURE_COLUMNS_PATH=./models/feature_columns.pkl
```

**Where to find each value:**
- `SUPABASE_KEY` → Supabase Dashboard → Project Settings → API → `anon` `public` key
- `SUPABASE_DB_URL` → Password is what you set when creating the Supabase project
- `OPENAI_API_KEY` → platform.openai.com → API Keys → Create new secret key
- `SECRET_KEY` → generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `CORS_ORIGINS` → update after you deploy to Vercel (you can use `*` temporarily)

---

## 6. DigitalOcean — Deploy Backend

**Option A — Automated script (recommended):**

```bash
# From your LOCAL machine (PowerShell or Git Bash)
scp scripts/deploy.sh root@YOUR_DROPLET_IP:/tmp/deploy.sh
ssh root@YOUR_DROPLET_IP "bash /tmp/deploy.sh"
```

Before running, edit `scripts/deploy.sh` line 7 to set your actual GitHub repo URL:
```bash
REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/xai-recommender.git"
```

**Option B — Manual steps on the Droplet:**

```bash
ssh root@YOUR_DROPLET_IP

# Install Docker
apt-get update && apt-get install -y docker.io docker-compose-plugin
systemctl enable --now docker

# Clone repo
git clone https://github.com/YOUR_GITHUB_USERNAME/xai-recommender.git /opt/xai-recommender
cd /opt/xai-recommender

# Build and start (models must be uploaded first — see Step 7)
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

---

## 7. Upload Model Files

**From your LOCAL machine** after training:

```bash
# Using the upload script
bash scripts/upload_models.sh YOUR_DROPLET_IP
```

This script:
1. Verifies all 3 pkl files exist locally
2. SCPs them to `/opt/xai-recommender/backend/models/` on the Droplet
3. Restarts the backend container
4. Confirms the model loaded via the health endpoint

**Manual alternative:**
```bash
scp backend/models/saved_model.pkl root@YOUR_DROPLET_IP:/opt/xai-recommender/backend/models/
scp backend/models/shap_background.pkl root@YOUR_DROPLET_IP:/opt/xai-recommender/backend/models/
scp backend/models/feature_columns.pkl root@YOUR_DROPLET_IP:/opt/xai-recommender/backend/models/

ssh root@YOUR_DROPLET_IP "cd /opt/xai-recommender && docker compose -f docker-compose.prod.yml restart backend"
```

---

## 8. Seed Demo Data

From your LOCAL machine (requires `pip install supabase passlib bcrypt python-dotenv`):

```powershell
# Copy .env.example and fill in your values
Copy-Item backend\.env.example backend\.env
# Edit backend\.env with your actual Supabase credentials

py -3.11 backend/data/seed_demo_data.py
```

Expected output:
```
Seeding 20 products... ✓
Seeding 3 demo users... ✓
Verifying demo user login:
  tech@demo.xai  → PASS
  books@demo.xai → PASS
  fashion@demo.xai → PASS
Inserting 30 interactions... ✓
Demo data seeded successfully.
```

> **Note:** If you already ran the SQL migration in Step 3, products and users are already seeded. The seed script uses upsert so running it again is safe — it only adds/updates, never duplicates.

---

## 9. Vercel — Deploy Frontend

**Option A — Vercel Dashboard (simplest):**

1. Push your project to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import Git Repository
3. Select `xai-recommender`
4. Set **Root Directory** to `frontend`
5. Set **Framework Preset** to `Vite`
6. Add Environment Variable:
   - `VITE_API_BASE_URL` = `http://YOUR_DROPLET_IP:8000`
7. Click **Deploy**

**Option B — Vercel CLI:**

```bash
cd frontend
npx vercel --prod

# When prompted:
# Set up and deploy? Y
# Which scope? (your account)
# Link to existing project? N
# Project name: xai-recommender
# Directory: ./
# Override settings? N

# After first deploy, set env var:
npx vercel env add VITE_API_BASE_URL production
# Enter: http://YOUR_DROPLET_IP:8000

# Redeploy with the env var
npx vercel --prod
```

**After deploying to Vercel:**

1. Note your Vercel URL (e.g., `https://xai-recommender-abc123.vercel.app`)
2. Update `CORS_ORIGINS` in your Droplet's `backend/.env`:
   ```
   CORS_ORIGINS=https://xai-recommender-abc123.vercel.app
   ```
3. Restart the backend:
   ```bash
   ssh root@YOUR_DROPLET_IP "cd /opt/xai-recommender && docker compose -f docker-compose.prod.yml restart backend"
   ```

---

## 10. Smoke Test

Run these checks to confirm everything is working end-to-end:

```bash
DROPLET_IP="YOUR_DROPLET_IP"
VERCEL_URL="https://your-app.vercel.app"

# 1. Backend health
curl http://$DROPLET_IP:8000/health
# Expected: {"status":"healthy","model_loaded":true,"db_connected":true,...}

# 2. API docs accessible
curl -I http://$DROPLET_IP:8000/docs
# Expected: HTTP/1.1 200 OK

# 3. Get recommendations for demo user
curl -X POST http://$DROPLET_IP:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"22222222-2222-2222-2222-222222222201","n_recommendations":5}'
# Expected: {"recommendations":[...],"response_time_ms":...}

# 4. Dashboard stats
curl http://$DROPLET_IP:8000/api/v1/dashboard/stats
# Expected: JSON with total_recommendations_today, total_users, etc.

# 5. Frontend loads
curl -I $VERCEL_URL
# Expected: HTTP/2 200
```

**Visual checks (open in browser):**
- `http://YOUR_DROPLET_IP:8000/docs` — FastAPI Swagger UI
- `https://your-app.vercel.app` — React frontend with 5 product cards
- Click "Why recommended?" → Explanation panel opens with SHAP chart
- Click "Dashboard" → KPI cards, charts load

---

## 11. Local Development

```bash
# Clone and install
git clone https://github.com/YOUR_GITHUB_USERNAME/xai-recommender.git
cd xai-recommender

# Backend
Copy-Item backend\.env.example backend\.env   # fill in values
py -3.11 -m pip install -r backend/requirements.txt
py -3.11 -m uvicorn app.main:app --reload --app-dir backend  # http://localhost:8000

# Frontend (new terminal)
cd frontend
Copy-Item .env.example .env                   # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                                   # http://localhost:5173
```

**Or with Docker Compose:**

```bash
# Copy envs first
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env

docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

---

## 12. Troubleshooting

### Backend won't start — model not loaded

```bash
ssh root@YOUR_DROPLET_IP
cd /opt/xai-recommender
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

If you see `FileNotFoundError: saved_model.pkl` → upload models (Step 7).

If you see `model_loaded: false` in `/health` but no error → model loaded but XAIEngine failed to init. Check SHAP logs.

### Out of memory (OOM)

```bash
# Check current memory
ssh root@YOUR_DROPLET_IP "free -m && docker stats --no-stream"
```

The 2GB Droplet runs the backend at ~610MB. If another process is consuming memory:
```bash
# Add swap space (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### CORS errors in browser

```bash
# Check current CORS setting on Droplet
ssh root@YOUR_DROPLET_IP "grep CORS /opt/xai-recommender/backend/.env"

# Temporarily allow all origins for debugging
ssh root@YOUR_DROPLET_IP "sed -i 's/CORS_ORIGINS=.*/CORS_ORIGINS=*/' /opt/xai-recommender/backend/.env"
ssh root@YOUR_DROPLET_IP "cd /opt/xai-recommender && docker compose -f docker-compose.prod.yml restart backend"
```

Then set to your exact Vercel URL once confirmed working.

### Database connection error

Symptoms: `{"status":"unhealthy","db_connected":false}`

1. Verify Supabase URL in `.env` matches your project ID (`kpkpxvjnaptduudgbfcq`)
2. Check Supabase Dashboard → Project Settings → Database → Connection string
3. Ensure the password in `SUPABASE_DB_URL` has no special characters that need URL-encoding

### Vercel build fails

```
Error: Could not find "index.html"
```
→ Set Root Directory to `frontend` in Vercel project settings.

```
Error: process.env.VITE_API_BASE_URL is undefined
```
→ Add `VITE_API_BASE_URL` in Vercel Dashboard → Settings → Environment Variables → Production.

### LLM explanations showing template text (not GPT-4o-mini)

This is intentional fallback behavior. Check:
1. `OPENAI_API_KEY` is set correctly in Droplet `.env`
2. OpenAI account has remaining credit (`platform.openai.com/usage`)
3. View backend logs: `docker compose logs backend | grep -i openai`

### Update deployment after code changes

```bash
# From LOCAL machine
git push origin main

# On Droplet
ssh root@YOUR_DROPLET_IP
cd /opt/xai-recommender
git pull
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d --no-deps backend
```

Vercel redeploys automatically on `git push` once connected to GitHub.

---

## Production URLs (fill in after deploy)

| Service | URL |
|---------|-----|
| Backend API | `http://YOUR_DROPLET_IP:8000` |
| API Docs | `http://YOUR_DROPLET_IP:8000/docs` |
| Health Check | `http://YOUR_DROPLET_IP:8000/health` |
| Frontend | `https://your-app.vercel.app` |
| Supabase Dashboard | `https://app.supabase.com/project/kpkpxvjnaptduudgbfcq` |
