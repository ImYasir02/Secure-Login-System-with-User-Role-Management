#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/secure_login}"
DB_NAME="${DB_NAME:-secure_login}"
DB_USER="${DB_USER:-securelogin_backup}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3307}"
DATE_TAG="$(date +%F_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [[ -z "${MYSQL_PWD:-}" ]]; then
  echo "MYSQL_PWD env var is required for non-interactive backups" >&2
  exit 1
fi

mysqldump --single-transaction --quick --routines --triggers \
  -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" \
  | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE_TAG}.sql.gz"

find "$BACKUP_DIR" -type f -name '*.sql.gz' -mtime +14 -delete
