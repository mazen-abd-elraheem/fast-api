#!/bin/bash
# =========================================================
# Sanaie Platform — Deployment Script
# Run after git pull to rebuild and restart services
# Usage: chmod +x deploy.sh && ./deploy.sh
# =========================================================
set -e

APP_DIR="/opt/sanaie"
COMPOSE_FILE="docker-compose.prod.yml"

echo "═══════════════════════════════════════════"
echo "  Sanaie Platform — Deploying..."
echo "═══════════════════════════════════════════"

cd "$APP_DIR"

# ── 1. Pull latest code ──
echo "[1/5] Pulling latest code..."
git pull origin main

# ── 2. Build images ──
echo "[2/5] Building Docker images..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# ── 3. Restart services ──
echo "[3/5] Restarting services..."
docker compose -f "$COMPOSE_FILE" down
docker compose -f "$COMPOSE_FILE" up -d

# ── 4. Wait for healthy ──
echo "[4/5] Waiting for services..."
sleep 15

# ── 5. Health check ──
echo "[5/5] Verifying deployment..."
for i in $(seq 1 10); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo ""
        echo "═══════════════════════════════════════════"
        echo "  ✅ Deployment Successful!"
        echo "═══════════════════════════════════════════"
        echo ""
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || true
        echo ""
        echo "Services:"
        docker compose -f "$COMPOSE_FILE" ps
        exit 0
    fi
    echo "  Waiting for API... ($i/10, status=$STATUS)"
    sleep 3
done

echo ""
echo "⚠️  Health check failed! Check logs:"
echo "  docker compose -f $COMPOSE_FILE logs api"
exit 1
