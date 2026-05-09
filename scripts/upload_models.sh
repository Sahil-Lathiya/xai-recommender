#!/usr/bin/env bash
# Upload trained model files to DigitalOcean Droplet
# Usage: bash scripts/upload_models.sh <DROPLET_IP>
# Run this AFTER py -3.11 scripts/train_local.py completes

set -euo pipefail

DROPLET_IP="${1:-}"
if [[ -z "$DROPLET_IP" ]]; then
  echo "Usage: bash scripts/upload_models.sh <DROPLET_IP>"
  exit 1
fi

REMOTE_USER="root"
REMOTE_MODELS_DIR="/opt/xai-recommender/backend/models"
LOCAL_MODELS_DIR="backend/models"

required_files=(
  "saved_model.pkl"
  "shap_background.pkl"
  "feature_columns.pkl"
)

echo "── Checking local model files ──"
for f in "${required_files[@]}"; do
  if [[ ! -f "$LOCAL_MODELS_DIR/$f" ]]; then
    echo "ERROR: $LOCAL_MODELS_DIR/$f not found."
    echo "Run: py -3.11 scripts/train_local.py"
    exit 1
  fi
  size=$(du -sh "$LOCAL_MODELS_DIR/$f" | cut -f1)
  echo "  ✓ $f ($size)"
done

echo ""
echo "── Uploading to $REMOTE_USER@$DROPLET_IP:$REMOTE_MODELS_DIR ──"
ssh "$REMOTE_USER@$DROPLET_IP" "mkdir -p $REMOTE_MODELS_DIR"

for f in "${required_files[@]}"; do
  echo "  Uploading $f ..."
  scp "$LOCAL_MODELS_DIR/$f" "$REMOTE_USER@$DROPLET_IP:$REMOTE_MODELS_DIR/$f"
  echo "  ✓ Done"
done

echo ""
echo "── Restarting backend to load new models ──"
ssh "$REMOTE_USER@$DROPLET_IP" \
  "cd /opt/xai-recommender && docker compose -f docker-compose.prod.yml restart backend"

echo ""
echo "── Verifying model loaded ──"
sleep 8
response=$(ssh "$REMOTE_USER@$DROPLET_IP" \
  "curl -sf http://localhost:8000/health || echo 'HEALTH_FAIL'")

if echo "$response" | grep -q '"model_loaded":true'; then
  echo "  ✓ Model loaded successfully"
elif echo "$response" | grep -q "HEALTH_FAIL"; then
  echo "  ✗ Health check failed — check: docker logs xai-backend"
  exit 1
else
  echo "  ⚠ Model not loaded yet — may still be initialising"
  echo "  Check: ssh $REMOTE_USER@$DROPLET_IP 'docker logs xai-backend --tail 30'"
fi

echo ""
echo "Upload complete. Models are live on the Droplet."
