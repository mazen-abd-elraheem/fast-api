#!/bin/bash
# =========================================================
# Sanaie Platform — One-Time VPS Setup Script
# Run as root on a fresh Ubuntu 22.04+ Hostinger VPS
# Usage: chmod +x setup-vps.sh && sudo ./setup-vps.sh
# =========================================================
set -e

echo "═══════════════════════════════════════════"
echo "  Sanaie Platform — VPS Setup"
echo "═══════════════════════════════════════════"

# ── 1. System Update ──
echo "[1/7] Updating system..."
apt update && apt upgrade -y

# ── 2. Install Docker ──
echo "[2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose plugin
apt install -y docker-compose-plugin 2>/dev/null || true

# ── 3. Install Nginx & Certbot ──
echo "[3/7] Installing Nginx & Certbot..."
apt install -y nginx certbot python3-certbot-nginx
systemctl enable nginx

# ── 4. Configure Firewall ──
echo "[4/7] Configuring firewall..."
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
echo "✅ Firewall configured (SSH, HTTP, HTTPS only)"

# ── 5. Create App Directory ──
echo "[5/7] Setting up app directory..."
mkdir -p /opt/sanaie
mkdir -p /opt/sanaie/uploaded_images
mkdir -p /opt/backups/sanaie

# ── 6. Generate Secrets ──
echo "[6/7] Generating secure passwords..."
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)

cat > /opt/sanaie/.env << EOF
# =========================================================
# Sanaie Platform — Production Environment
# Generated on $(date)
# =========================================================

ENVIRONMENT=production
DEBUG=False

# MySQL Database
DATABASE_URL=mysql+pymysql://sanaie_user:${DB_PASSWORD}@db:3306/sanaie_db
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
DB_PASSWORD=${DB_PASSWORD}

# Security
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# File Uploads
UPLOAD_DIR=/app/uploaded_images
MAX_UPLOAD_SIZE_MB=10

# CORS — Update with your actual domain
ALLOWED_ORIGINS=["https://api.sanaie.com"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
EOF

chmod 600 /opt/sanaie/.env
echo "✅ Production .env generated at /opt/sanaie/.env"

# ── 7. Display Summary ──
echo "[7/7] Setup complete!"
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ VPS Setup Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Clone your repo:  cd /opt/sanaie && git clone <YOUR_REPO_URL> ."
echo "  2. Copy .env:        (already generated)"
echo "  3. Deploy:           ./deploy/deploy.sh"
echo "  4. SSL:              certbot --nginx -d api.sanaie.com"
echo ""
echo "Generated credentials (SAVE THESE):"
echo "  SECRET_KEY:          ${SECRET_KEY}"
echo "  DB_PASSWORD:         ${DB_PASSWORD}"
echo "  MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}"
echo ""
