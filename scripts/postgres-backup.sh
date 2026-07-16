#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE_FILE="${AQUAOPS_PROD_COMPOSE_FILE:-docker-compose.prod.yml}"
DB_SERVICE="${AQUAOPS_DB_SERVICE:-db}"
ENV_FILE="${AQUAOPS_ENV_FILE:-.env}"
OUTPUT="${1:-aquaops-$(date -u +%Y%m%dT%H%M%SZ).dump}"

read_env_key() {
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1
}

[[ -f "$ENV_FILE" ]] || { printf 'Environment file %s was not found.\n' "$ENV_FILE" >&2; exit 1; }
[[ ! -e "$OUTPUT" ]] || { printf 'Refusing to overwrite existing file %s.\n' "$OUTPUT" >&2; exit 1; }

DB_NAME="$(read_env_key POSTGRES_DB)"
DB_USER="$(read_env_key POSTGRES_USER)"
[[ -n "$DB_NAME" && -n "$DB_USER" ]] || {
  printf 'POSTGRES_DB and POSTGRES_USER must be set in %s.\n' "$ENV_FILE" >&2
  exit 1
}

printf 'Creating PostgreSQL backup\n'
printf '  compose_file=%s\n  service=%s\n  database=%s\n  output=%s\n' \
  "$COMPOSE_FILE" "$DB_SERVICE" "$DB_NAME" "$OUTPUT"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom >"$OUTPUT"
test -s "$OUTPUT" || { printf 'Backup file is empty.\n' >&2; exit 1; }
printf 'Backup complete: %s\n' "$OUTPUT"
