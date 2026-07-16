#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE_FILE="${AQUAOPS_PROD_COMPOSE_FILE:-docker-compose.prod.yml}"
DB_SERVICE="${AQUAOPS_DB_SERVICE:-db}"
ENV_FILE="${AQUAOPS_ENV_FILE:-.env}"

usage() {
  printf 'Usage: %s DUMP_FILE --confirm-db DATABASE\n' "$0"
}

read_env_key() {
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1
}

[[ $# -eq 3 && "$2" == "--confirm-db" ]] || { usage >&2; exit 2; }
DUMP_FILE="$1"
CONFIRMED_DB="$3"
[[ -s "$DUMP_FILE" ]] || { printf 'Dump file %s is missing or empty.\n' "$DUMP_FILE" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { printf 'Environment file %s was not found.\n' "$ENV_FILE" >&2; exit 1; }

DB_NAME="$(read_env_key POSTGRES_DB)"
DB_USER="$(read_env_key POSTGRES_USER)"
[[ -n "$DB_NAME" && -n "$DB_USER" ]] || {
  printf 'POSTGRES_DB and POSTGRES_USER must be set in %s.\n' "$ENV_FILE" >&2
  exit 1
}
[[ "$CONFIRMED_DB" == "$DB_NAME" ]] || {
  printf 'Confirmation %s does not match configured database %s.\n' "$CONFIRMED_DB" "$DB_NAME" >&2
  exit 1
}

TABLE_COUNT="$(docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME" -Atqc \
  "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")"
[[ "$TABLE_COUNT" == "0" ]] || {
  printf 'Refusing to restore: database %s has %s public tables; restore requires an empty database.\n' \
    "$DB_NAME" "$TABLE_COUNT" >&2
  exit 1
}

printf 'Restoring PostgreSQL backup\n'
printf '  compose_file=%s\n  service=%s\n  database=%s\n  input=%s\n' \
  "$COMPOSE_FILE" "$DB_SERVICE" "$DB_NAME" "$DUMP_FILE"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --exit-on-error --no-owner --no-privileges \
  <"$DUMP_FILE"
printf 'Restore complete. Run application readiness and workflow verification now.\n'
