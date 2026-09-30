#!/usr/bin/env bash
# SecurWork — Daily backup (PostgreSQL + media)
set -euo pipefail

BACKUP_DIR="/var/backups/securwork"
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30
APP_DIR="/var/www/securwork"

mkdir -p "${BACKUP_DIR}"

echo "[${DATE}] Starting backup..."

pg_dump -U securwork securwork | gzip > "${BACKUP_DIR}/db-${DATE}.sql.gz"
tar -czf "${BACKUP_DIR}/media-${DATE}.tar.gz" -C "${APP_DIR}/backend" media/

find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete

echo "[${DATE}] Backup complete."
