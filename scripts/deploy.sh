#!/usr/bin/env bash
# One-shot deploy script — runs ON the DigitalOcean Droplet
# Copy this to the Droplet and run: bash deploy.sh
# Or run remotely: ssh root@<IP> 'bash -s' < scripts/deploy.sh

set -euo pipefail

REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/xai-recommender.git"
APP_DIR="/opt/xai-recommender"
COMPOSE_FILE="docker-compose.prod.yml"

echo "════════════════════════════════════════════"
echo "  XAI Recommender — Droplet Deploy Script  "
echo "════════════════════════════════════════════"

# ── 1. Install Docker if missing ──────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "[1/7] Installing Docker..."
  apt-get update -q
  apt-get install -y -q ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  echo "[1/7] ✓ Docker installed"
else
  echo "[1/7] ✓ Docker already installed ($(docker --version))"
fi

# ── 2. Clone or update repo ───────────────────────────────────────────────────
echo "[2/7] Cloning / updating repo..."
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
echo "[2/7] ✓ Repo ready at $APP_DIR"

# ── 3. Verify .env exists ─────────────────────────────────────────────────────
echo "[3/7] Checking environment file..."
if [[ ! -f "$APP_DIR/backend/.env" ]]; then
  echo ""
  echo "  ERROR: backend/.env not found!"
  echo "  Copy backend/.env.example to backend/.env and fill in all values."
  echo "  Then re-run this script."
  exit 1
fi
echo "[3/7] ✓ backend/.env found"

# ── 4. Verify model files ─────────────────────────────────────────────────────
echo "[4/7] Checking model files..."
MODELS_DIR="$APP_DIR/backend/models"
mkdir -p "$MODELS_DIR"
missing=0
for f in saved_model.pkl shap_background.pkl feature_columns.pkl; do
  if [[ ! -f "$MODELS_DIR/$f" ]]; then
    echo "  ✗ Missing: $MODELS_DIR/$f"
    missing=1
  else
    echo "  ✓ $f"
  fi
done
if [[ $missing -eq 1 ]]; then
  echo ""
  echo "  Upload models from your local machine:"
  echo "  bash scripts/upload_models.sh $(curl -s ifconfig.me)"
  echo "  Then re-run this script."
  exit 1
fi
echo "[4/7] ✓ All model files present"

# ── 5. Build Docker images ────────────────────────────────────────────────────
echo "[5/7] Building Docker images (this takes ~3 min on first run)..."
docker compose -f "$COMPOSE_FILE" build --no-cache
echo "[5/7] ✓ Images built"

# ── 6. Start services ─────────────────────────────────────────────────────────
echo "[6/7] Starting services..."
docker compose -f "$COMPOSE_FILE" up -d
echo "[6/7] ✓ Services started"

# ── 7. Health check ───────────────────────────────────────────────────────────
echo "[7/7] Waiting for health check (40s startup grace period)..."
sleep 45

MAX_RETRIES=6
for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf http://localhost:8000/health | grep -q '"status":"healthy"'; then
    echo "[7/7] ✓ Backend healthy!"
    break
  fi
  if [[ $i -eq $MAX_RETRIES ]]; then
    echo "[7/7] ✗ Health check failed after $MAX_RETRIES attempts"
    echo "  Check logs: docker compose -f $COMPOSE_FILE logs backend --tail 50"
    exit 1
  fi
  echo "  Attempt $i/$MAX_RETRIES failed, retrying in 10s..."
  sleep 10
done

DROPLET_IP=$(curl -s ifconfig.me)
echo ""
echo "════════════════════════════════════════════"
echo "  Deploy complete!"
echo ""
echo "  API:    http://$DROPLET_IP:8000"
echo "  Health: http://$DROPLET_IP:8000/health"
echo "  Docs:   http://$DROPLET_IP:8000/docs"
echo ""
echo "  Next: Deploy frontend to Vercel"
echo "  Set VITE_API_BASE_URL=http://$DROPLET_IP:8000"
echo "════════════════════════════════════════════"
