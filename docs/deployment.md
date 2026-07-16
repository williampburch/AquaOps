# AquaOps Production Deployment

AquaOps runs on the existing Azure Linux VM from the immutable GHCR application image:

```text
ghcr.io/williampburch/aquaops:<short-sha>
```

The checkout is `/opt/aquaops`. Normal deployment uses `docker-compose.prod.yml` and
`AQUAOPS_IMAGE_TAG=<short-sha> make deploy`; the VM never builds the production image.

## Production architecture

```text
Azure Linux VM
├── Nginx -> 127.0.0.1:8010
├── AquaOps web container
├── PostgreSQL 17 container (internal Compose network only)
├── aquaops_postgres named volume
└── aquaops_media named volume
```

The `db` service has no host port in production. The web container connects through the
Compose service name `db`. Local media storage is unchanged. Azure Container Apps, Azure
Database for PostgreSQL, and Azure Blob Storage are intentionally outside this reset.

## Production environment

Store settings and secrets in `/opt/aquaops/.env`. Never commit or print this file.
It must contain at least:

```dotenv
APP_ENV=production
SECRET_KEY=<long-random-secret>
POSTGRES_DB=aquaops
POSTGRES_USER=aquaops
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql+psycopg://aquaops:<url-encoded-password>@db:5432/aquaops
AUTO_CREATE_TABLES=false
MEDIA_ROOT=/app/media
```

If the password contains URL-reserved characters, percent-encode only the password in
`DATABASE_URL`; `POSTGRES_PASSWORD` retains its original value. Check presence without
displaying values:

```bash
cd /opt/aquaops
test -f .env && echo ".env exists" || echo "ERROR: .env is missing"
docker compose -f docker-compose.prod.yml config --quiet
```

Compose must show no published port for `db`. `AUTO_CREATE_TABLES=true` and a non-
PostgreSQL production URL are rejected by application settings.

## Health semantics

- `/health/live` confirms that the application process can respond and does not query the
  database.
- `/health/ready` performs `SELECT 1`; database failure returns HTTP 503 without internal
  exception details.
- `/health` is a compatibility alias for database-aware readiness.

Nginx continues to proxy public HTTPS to `http://127.0.0.1:8010`. PostgreSQL port 5432
must not be opened in Compose, the VM firewall, or the Azure network security group.

## One-time SQLite to PostgreSQL reset

This reset intentionally starts PostgreSQL with an empty application database. It does
not import SQLite rows. Preserve the old database archive untouched for safety.

### 1. Stop writes and identify the existing volumes

Announce the maintenance window, stop using AquaOps, then run against the old deployment:

```bash
cd /opt/aquaops
OLD_DATA_VOLUME="$(docker inspect aquaops-web --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Name}}{{end}}{{end}}')"
MEDIA_VOLUME="$(docker inspect aquaops-web --format '{{range .Mounts}}{{if eq .Destination "/app/media"}}{{.Name}}{{end}}{{end}}')"
test -n "$OLD_DATA_VOLUME" || { echo "SQLite data volume not found" >&2; exit 1; }
test -n "$MEDIA_VOLUME" || { echo "Media volume not found" >&2; exit 1; }
docker compose -f docker-compose.prod.yml stop web
```

Do not accept any more writes after this point.

### 2. Archive SQLite and preserve media

```bash
BACKUP_DIR="$HOME/aquaops-backups/postgresql-cutover-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
docker pull alpine:3.20
docker run --rm -v "$OLD_DATA_VOLUME:/source:ro" -v "$BACKUP_DIR:/backup" \
  alpine:3.20 tar -C /source -czf /backup/sqlite-data-volume.tar.gz .
docker run --rm -v "$MEDIA_VOLUME:/source:ro" -v "$BACKUP_DIR:/backup" \
  alpine:3.20 tar -C /source -czf /backup/media-volume-pre-cutover.tar.gz .
test -s "$BACKUP_DIR/sqlite-data-volume.tar.gz"
test -s "$BACKUP_DIR/media-volume-pre-cutover.tar.gz"
sha256sum "$BACKUP_DIR"/*.tar.gz
```

Copy the archives and checksums off the VM. Do not delete or repurpose the SQLite volume.
The existing media volume remains mounted by the new web container.

### 3. Install the new deployment definition and environment

```bash
git pull --ff-only origin main
```

Update `.env` with the PostgreSQL variables above. Confirm the target image uses an
immutable short SHA and that no PostgreSQL volume from a failed trial exists. Let Compose
create the fresh `aquaops_postgres` volume; do not reuse the archived SQLite volume.

### 4. Start PostgreSQL and migrate the empty database

```bash
export AQUAOPS_IMAGE_TAG=<short-sha>
docker pull "ghcr.io/williampburch/aquaops:${AQUAOPS_IMAGE_TAG}"
docker compose -f docker-compose.prod.yml pull db
docker compose -f docker-compose.prod.yml up -d db
until docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; do sleep 2; done
docker compose -f docker-compose.prod.yml run --rm web alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm web alembic current
```

### 5. Start and verify AquaOps

```bash
docker compose -f docker-compose.prod.yml up -d --no-build web
curl -fsS http://127.0.0.1:8010/health/live
curl -fsS http://127.0.0.1:8010/health/ready
```

Create the initial user through normal `/register`; no special password or direct SQL
bootstrap is required. Then verify all of the following before ending the maintenance
window:

1. Login and logout.
2. Create a tank.
3. Quick Log a water test, feeding, maintenance item, and observation.
4. Open the Care Queue and complete or snooze a reminder.
5. Add livestock and a plant, then confirm inventory ownership and totals.
6. Upload and retrieve a photo from the preserved media volume.
7. Open a problem, link timeline events, update its status, and confirm history.
8. Confirm `/health/ready`, local HTTPS through Nginx, and container health.

Leave the SQLite archive and old volume untouched. There is no automatic SQLite import.

## Routine deployment

Before a migration-bearing deployment, create a PostgreSQL dump and media backup as
described in [Backup and Restore](backup-restore.md).

```bash
cd /opt/aquaops
git pull --ff-only origin main
AQUAOPS_IMAGE_TAG=<short-sha> make deploy
```

`scripts/deploy-image.sh`:

1. Acquires the existing deployment lock.
2. Preserves the current application image with a timestamped rollback tag.
3. Pulls the requested immutable application image.
4. Pulls and starts PostgreSQL, then retries `pg_isready` independently of Compose
   `depends_on`.
5. Runs `alembic upgrade head` using the pulled application image.
6. Recreates the web container without building.
7. Retries database-aware `/health/ready`.
8. Prints web and database diagnostics on failure and attempts an application-image
   rollback when possible.

Useful verification:

```bash
curl -fsS http://127.0.0.1:8010/health/live
curl -fsS http://127.0.0.1:8010/health/ready
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail 80 web db
docker inspect aquaops-web --format 'image={{.Config.Image}} id={{.Image}} status={{.State.Status}}'
curl -fsS -o /dev/null -w 'public_https=%{http_code}\n' https://aquaops.william-burch.com/
```

## Rollback limitation

The deploy script can recreate the previous application image, but application-image
rollback does not undo Alembic migrations already applied to PostgreSQL. Restore the
pre-deployment dump or follow a reviewed migration-specific downgrade plan during an
outage when schema recovery is required. Never assume starting an old image restores the
old schema or data.

## Legacy path

`make deploy-build` remains a local troubleshooting fallback only. Normal VM deployment
must use the prebuilt GHCR image. Do not use `docker compose build`, `up --build`, or
`make deploy-build` as the production release path.

Any change to Compose, database initialization, ports, images, migrations, health checks,
backup/restore, or rollback behavior must update this guide in the same PR.
