#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE_REPOSITORY="${AQUAOPS_IMAGE_REPOSITORY:-ghcr.io/williampburch/aquaops}"
IMAGE_TAG="${AQUAOPS_IMAGE_TAG:?AQUAOPS_IMAGE_TAG must be set to an immutable short SHA}"
TARGET_IMAGE="${IMAGE_REPOSITORY}:${IMAGE_TAG}"
COMPOSE_FILE="${AQUAOPS_PROD_COMPOSE_FILE:-docker-compose.prod.yml}"
SERVICE="${AQUAOPS_DEPLOY_SERVICE:-web}"
DB_SERVICE="${AQUAOPS_DB_SERVICE:-db}"
CONTAINER_NAME="${AQUAOPS_CONTAINER_NAME:-aquaops-web}"
HEALTH_URL="${AQUAOPS_HEALTH_URL:-http://127.0.0.1:8010/health/ready}"
HEALTH_ATTEMPTS="${AQUAOPS_HEALTH_ATTEMPTS:-30}"
HEALTH_DELAY_SECONDS="${AQUAOPS_HEALTH_DELAY_SECONDS:-2}"
DB_HEALTH_ATTEMPTS="${AQUAOPS_DB_HEALTH_ATTEMPTS:-30}"
DB_HEALTH_DELAY_SECONDS="${AQUAOPS_DB_HEALTH_DELAY_SECONDS:-2}"
LOCK_FILE="${AQUAOPS_DEPLOY_LOCK_FILE:-/tmp/aquaops-image-deploy.lock}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE=(docker compose -f "$COMPOSE_FILE")
PREVIOUS_IMAGE_ID=""
PREVIOUS_IMAGE_REF=""
ROLLBACK_TAG=""

log() {
  printf '\n==> %s\n' "$*"
}

run() {
  printf '+ '
  printf '%q ' "$@"
  printf '\n'
  "$@"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s is required but was not found.\n' "$1" >&2
    exit 1
  fi
}

diagnostics() {
  log "Deployment diagnostics"
  "${COMPOSE[@]}" ps >&2 || true
  "${COMPOSE[@]}" logs --tail 120 "$SERVICE" >&2 || true
  "${COMPOSE[@]}" logs --tail 120 "$DB_SERVICE" >&2 || true
  docker inspect \
    --format 'container={{.Name}} image={{.Config.Image}} status={{.State.Status}} exit={{.State.ExitCode}} error={{.State.Error}}' \
    "$CONTAINER_NAME" >&2 || true
}

database_health_check() {
  local attempt
  for ((attempt = 1; attempt <= DB_HEALTH_ATTEMPTS; attempt += 1)); do
    if "${COMPOSE[@]}" exec -T "$DB_SERVICE" sh -c \
      'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      printf 'PostgreSQL is ready on attempt %s/%s.\n' "$attempt" "$DB_HEALTH_ATTEMPTS"
      return 0
    fi
    printf 'Waiting for PostgreSQL (%s/%s)...\n' "$attempt" "$DB_HEALTH_ATTEMPTS"
    sleep "$DB_HEALTH_DELAY_SECONDS"
  done
  return 1
}

health_check() {
  local attempt
  for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt += 1)); do
    if curl --fail --silent --show-error --max-time 4 "$HEALTH_URL" >/dev/null 2>&1; then
      printf 'Health check passed on attempt %s/%s.\n' "$attempt" "$HEALTH_ATTEMPTS"
      return 0
    fi
    printf 'Waiting for health check (%s/%s)...\n' "$attempt" "$HEALTH_ATTEMPTS"
    sleep "$HEALTH_DELAY_SECONDS"
  done
  return 1
}

rollback() {
  if [[ -z "$ROLLBACK_TAG" ]]; then
    printf 'No previous container image was available for automatic rollback.\n' >&2
    return 1
  fi

  log "Rolling back to ${PREVIOUS_IMAGE_REF:-$PREVIOUS_IMAGE_ID}"
  if ! AQUAOPS_IMAGE_TAG="$ROLLBACK_TAG" "${COMPOSE[@]}" \
    up -d --no-build --force-recreate --remove-orphans "$SERVICE"; then
    printf 'Rollback container restart failed.\n' >&2
    diagnostics
    return 1
  fi

  if health_check; then
    printf 'Rollback succeeded using local tag %s:%s.\n' "$IMAGE_REPOSITORY" "$ROLLBACK_TAG" >&2
    return 0
  fi

  printf 'Rollback container did not become healthy.\n' >&2
  diagnostics
  return 1
}

require_command docker
require_command curl
require_command flock

if ! docker info >/dev/null 2>&1; then
  printf 'Docker is installed, but the daemon is unavailable or this user cannot access it.\n' >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  printf 'The Docker Compose plugin is required but unavailable.\n' >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  printf 'Production Compose file %s was not found in %s.\n' "$COMPOSE_FILE" "$REPO_ROOT" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  printf '.env was not found in %s. Configure production settings before deploying.\n' "$REPO_ROOT" >&2
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf 'Another AquaOps image deployment holds lock %s.\n' "$LOCK_FILE" >&2
  exit 1
fi

if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  PREVIOUS_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$CONTAINER_NAME")"
  PREVIOUS_IMAGE_REF="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_NAME")"
  ROLLBACK_TAG="rollback-$(date -u +%Y%m%d%H%M%S)"
  log "Preserving current image ${PREVIOUS_IMAGE_REF} as ${IMAGE_REPOSITORY}:${ROLLBACK_TAG}"
  run docker image tag "$PREVIOUS_IMAGE_ID" "${IMAGE_REPOSITORY}:${ROLLBACK_TAG}"
else
  log "No existing ${CONTAINER_NAME} container found; automatic rollback will be unavailable"
fi

log "Pulling ${TARGET_IMAGE}"
run docker pull "$TARGET_IMAGE"

log "Starting PostgreSQL"
run "${COMPOSE[@]}" pull "$DB_SERVICE"
run "${COMPOSE[@]}" up -d --no-build "$DB_SERVICE"

log "Waiting for PostgreSQL readiness"
if ! database_health_check; then
  printf 'PostgreSQL did not become ready.\n' >&2
  diagnostics
  exit 1
fi

log "Running database migrations with ${TARGET_IMAGE}"
run env AQUAOPS_IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" run --rm "$SERVICE" alembic upgrade head

log "Restarting ${SERVICE} from the pulled image"
if ! AQUAOPS_IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" \
  up -d --no-build --force-recreate --remove-orphans "$SERVICE"; then
  printf 'Container restart failed for %s.\n' "$TARGET_IMAGE" >&2
  diagnostics
  rollback || true
  exit 1
fi

log "Checking ${HEALTH_URL}"
if ! health_check; then
  printf 'Health check failed for %s.\n' "$TARGET_IMAGE" >&2
  diagnostics
  rollback || true
  exit 1
fi

log "Deployment complete"
"${COMPOSE[@]}" ps
printf 'Running image: %s\n' "$TARGET_IMAGE"
printf 'Follow logs with: docker compose -f %s logs -f %s\n' "$COMPOSE_FILE" "$SERVICE"
