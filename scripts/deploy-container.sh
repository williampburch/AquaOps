#!/usr/bin/env bash
set -Eeuo pipefail

BRANCH="${AQUAOPS_DEPLOY_BRANCH:-main}"
REMOTE="${AQUAOPS_DEPLOY_REMOTE:-origin}"
SERVICE="${AQUAOPS_DEPLOY_SERVICE:-web}"
COMPOSE="${AQUAOPS_COMPOSE:-docker compose}"
SKIP_BUILD=0
SKIP_MIGRATIONS=0
FORCE_DIRTY=0

usage() {
  cat <<'USAGE'
Usage: scripts/deploy-container.sh [options]

Pull the latest AquaOps code and restart the Docker Compose web container.

Options:
  --branch NAME        Branch to deploy. Default: main
  --remote NAME        Git remote to pull from. Default: origin
  --service NAME       Compose service to deploy. Default: web
  --compose COMMAND    Compose command. Default: "docker compose"
  --skip-build         Do not rebuild the image before restart
  --skip-migrations    Do not run Alembic migrations
  --force-dirty        Continue even if tracked files have local changes
  -h, --help           Show this help

Environment overrides:
  AQUAOPS_DEPLOY_BRANCH
  AQUAOPS_DEPLOY_REMOTE
  AQUAOPS_DEPLOY_SERVICE
  AQUAOPS_COMPOSE
USAGE
}

log() {
  printf '\n==> %s\n' "$*"
}

run() {
  printf '+ %s\n' "$*"
  "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH="${2:?Missing branch name}"
      shift 2
      ;;
    --remote)
      REMOTE="${2:?Missing remote name}"
      shift 2
      ;;
    --service)
      SERVICE="${2:?Missing service name}"
      shift 2
      ;;
    --compose)
      COMPOSE="${2:?Missing compose command}"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS=1
      shift
      ;;
    --force-dirty)
      FORCE_DIRTY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  printf 'git is required but was not found.\n' >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  printf 'docker is required but was not found.\n' >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [[ ! -f docker-compose.yml ]]; then
  printf 'docker-compose.yml was not found in %s\n' "$REPO_ROOT" >&2
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  printf 'Current branch is %s, expected %s.\n' "$CURRENT_BRANCH" "$BRANCH" >&2
  printf 'Checkout the target branch first or run with --branch %s.\n' "$CURRENT_BRANCH" >&2
  exit 1
fi

if [[ "$FORCE_DIRTY" -eq 0 ]]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    printf 'Tracked local changes are present. Commit/stash them or rerun with --force-dirty.\n' >&2
    git status --short >&2
    exit 1
  fi
fi

log "Fetching latest ${REMOTE}/${BRANCH}"
run git fetch --prune "$REMOTE" "$BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "${REMOTE}/${BRANCH}")"
if [[ "$LOCAL_SHA" == "$REMOTE_SHA" ]]; then
  log "Repository is already at ${LOCAL_SHA:0:12}"
else
  log "Fast-forwarding to ${REMOTE_SHA:0:12}"
  run git pull --ff-only "$REMOTE" "$BRANCH"
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  log "Building ${SERVICE} image"
  # shellcheck disable=SC2086
  run $COMPOSE build "$SERVICE"
fi

if [[ "$SKIP_MIGRATIONS" -eq 0 ]]; then
  log "Running database migrations"
  # shellcheck disable=SC2086
  run $COMPOSE run --rm "$SERVICE" alembic upgrade head
fi

log "Restarting ${SERVICE} container"
# shellcheck disable=SC2086
run $COMPOSE up -d --remove-orphans "$SERVICE"

log "Container status"
# shellcheck disable=SC2086
run $COMPOSE ps

log "Deploy complete"
printf 'Tip: follow logs with `%s logs -f %s`\n' "$COMPOSE" "$SERVICE"
