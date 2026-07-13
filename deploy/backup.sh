#!/bin/bash
# =========================================================
# Sanaie Platform — Automated Database Backup
# Add to crontab: 0 3 * * * /opt/sanaie/deploy/backup.sh
# Keeps 30 days of backups
# =========================================================
set -e

BACKUP_DIR="/opt/backups/sanaie"
DATE=$(date +%Y%m%d_%H%M)
COMPOSE_FILE="/opt/sanaie/docker-compose.prod.yml"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# ── Database dump ──
docker exec sanaie-mysql mysqldump \
    -u root \
    -p"$(grep MYSQL_ROOT_PASSWORD /opt/sanaie/.env | cut -d= -f2)" \
    --single-transaction \
    --routines \
    --triggers \
    sanaie_db 2>/dev/null | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

DB_SIZE=$(du -h "$BACKUP_DIR/db_${DATE}.sql.gz" | cut -f1)
echo "  ✅ Database backup: db_${DATE}.sql.gz ($DB_SIZE)"

# ── Uploaded images backup ──
if [ -d "/opt/sanaie/uploaded_images" ]; then
    tar -czf "$BACKUP_DIR/uploads_${DATE}.tar.gz" \
        -C /opt/sanaie uploaded_images/ 2>/dev/null || true
    UPLOAD_SIZE=$(du -h "$BACKUP_DIR/uploads_${DATE}.tar.gz" 2>/dev/null | cut -f1)
    echo "  ✅ Uploads backup: uploads_${DATE}.tar.gz ($UPLOAD_SIZE)"
fi

# ── Cleanup old backups (30 days) ──
find "$BACKUP_DIR" -type f -mtime +30 -delete
TOTAL=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "  📦 Total backup size: $TOTAL"

echo "[$(date)] Backup complete."
