# AquaOps Production Deployment

AquaOps production runs on an Azure Linux VM from a prebuilt Docker image published
to GitHub Container Registry (GHCR):

```text
ghcr.io/williampburch/aquaops
```

The repository checkout is `/opt/aquaops`. Production uses
`docker-compose.prod.yml`, and `make deploy` runs `scripts/deploy-image.sh`.
The VM does **not** build an application image during a normal production deployment.

## Production architecture

- The `aquaops-web` container binds `127.0.0.1:8010:8000`. The application port is
  not exposed directly to the internet.
- Nginx terminates public HTTPS traffic and proxies it to
  `http://127.0.0.1:8010`.
- The local health endpoint is `http://127.0.0.1:8010/health`.
- SQLite data is stored in the `aquaops_data` Docker volume.
- Uploaded media is stored in the `aquaops_media` Docker volume.
- Docker Compose may prefix the physical volume names with the project name, such as
  `aquaops_aquaops_data` and `aquaops_aquaops_media`.
- Production settings and secrets are stored in `/opt/aquaops/.env`.

Never commit `.env`, print its contents, or copy its secrets into deployment logs or
support chats. Confirm that the file exists without displaying it:

```bash
cd /opt/aquaops
test -f .env && echo ".env exists" || echo "ERROR: .env is missing"
```

## Image tags

GitHub Actions publishes the application image after a successful build. Production
deployments should use the immutable short Git commit SHA for the desired release:

```bash
AQUAOPS_IMAGE_TAG=ed8ab8a make deploy
```

Replace `ed8ab8a` with the tag for the commit being deployed. A short-SHA tag makes
the deployed version explicit and repeatable. The `latest` tag can move whenever a
new image is published, so it is less safe and should not be used for routine
production deployments.

## GHCR access

Public GHCR images can be pulled without authentication. If the AquaOps package is
private, authenticate once as the same Linux user that performs deployments. Use a
GitHub personal access token (classic) with only the `read:packages` scope. Do not put
the token in this repository or in `.env`.

```bash
read -rsp "GitHub package token: " CR_PAT
echo
printf '%s' "$CR_PAT" | docker login ghcr.io -u williampburch --password-stdin
unset CR_PAT
```

Docker saves the registry login in that Linux user's Docker client configuration.

## Before every deployment

### 1. Connect and run preflight checks

```bash
cd /opt/aquaops
pwd
docker --version
docker compose version
curl --version
flock --version
test -f .env && echo ".env exists" || echo "ERROR: .env is missing"
```

The expected working directory is `/opt/aquaops`. Stop if `.env` is missing or Docker
is unavailable.

Check the current container, health endpoint, and persistent volumes:

```bash
docker ps --filter "name=aquaops-web"
curl -fsS http://127.0.0.1:8010/health
docker volume ls --format '{{.Name}}' | grep aquaops
```

### 2. Back up data and media

Back up both persistent volumes before any deployment that may run migrations. The
following example discovers the actual volume names from the running container, stops
the application for a consistent SQLite backup, and creates timestamped compressed
archives. It does not print `.env`.

```bash
cd /opt/aquaops

DATA_VOLUME="$(docker inspect aquaops-web --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Name}}{{end}}{{end}}')"
MEDIA_VOLUME="$(docker inspect aquaops-web --format '{{range .Mounts}}{{if eq .Destination "/app/media"}}{{.Name}}{{end}}{{end}}')"
BACKUP_DIR="$HOME/aquaops-backups/$(date -u +%Y%m%dT%H%M%SZ)"

test -n "$DATA_VOLUME" || { echo "Could not find the /app/data volume" >&2; exit 1; }
test -n "$MEDIA_VOLUME" || { echo "Could not find the /app/media volume" >&2; exit 1; }
mkdir -p "$BACKUP_DIR"

docker pull alpine:3.20
docker compose -f docker-compose.prod.yml stop web
docker run --rm \
  -v "$DATA_VOLUME:/source:ro" \
  -v "$BACKUP_DIR:/backup" \
  alpine:3.20 tar -C /source -czf /backup/aquaops_data.tar.gz .
docker run --rm \
  -v "$MEDIA_VOLUME:/source:ro" \
  -v "$BACKUP_DIR:/backup" \
  alpine:3.20 tar -C /source -czf /backup/aquaops_media.tar.gz .

ls -lh "$BACKUP_DIR"
sha256sum "$BACKUP_DIR"/*.tar.gz
docker compose -f docker-compose.prod.yml start web
curl -fsS http://127.0.0.1:8010/health
```

Pulling the small backup helper image before stopping the service limits downtime. Both
archives must exist and have plausible, nonzero sizes, the checksums must be recorded,
and the existing application must be healthy before proceeding. If an archive command
fails and leaves the service stopped, restart the existing container with:

```bash
docker compose -f docker-compose.prod.yml start web
curl -fsS http://127.0.0.1:8010/health
```

Copy backups off the VM and periodically test restoration. A backup stored only on the
production VM is not sufficient disaster recovery. Restoring a volume overwrites live
state, so perform restoration only during a planned outage and retain the current
volumes until the restored application has been verified.

## Deploy a release

Choose the short-SHA tag for the release and use the same value in every command below.
This example uses `ed8ab8a`:

### 1. Confirm that the image is available

```bash
docker pull ghcr.io/williampburch/aquaops:ed8ab8a
```

If this fails with an authorization error, complete the GHCR authentication step above.
Do not proceed if the requested image cannot be pulled.

### 2. Update the deployment files

```bash
cd /opt/aquaops
git pull --ff-only origin main
```

The fast-forward-only pull stops instead of silently merging unexpected VM-side Git
changes. Resolve any reported local changes deliberately before deploying.

### 3. Deploy the selected image

```bash
AQUAOPS_IMAGE_TAG=ed8ab8a make deploy
```

`make deploy` runs `scripts/deploy-image.sh`, which:

1. Takes a deployment lock so two deployments cannot overlap.
2. Preserves the previously running image with a timestamped local `rollback-*` tag.
3. Pulls `ghcr.io/williampburch/aquaops:<tag>` from GHCR.
4. Runs `alembic upgrade head` using the pulled image.
5. Recreates `aquaops-web` with Docker Compose and `--no-build`.
6. Retries `http://127.0.0.1:8010/health` and prints diagnostics on failure.
7. Attempts to recreate the previous image if restart or health verification fails.

## Verify the deployment

Run all of these checks after `make deploy` succeeds:

```bash
curl -fsS http://127.0.0.1:8010/health
docker ps --filter "name=aquaops-web"
docker compose -f docker-compose.prod.yml logs --tail 80 web
curl -fsS -o /dev/null -w "public_https=%{http_code}\n" https://aquaops.william-burch.com/
```

The local health request must succeed, `aquaops-web` should be running, and the public
HTTPS check should report a successful HTTP status. If verification fails, retain the
command output and inspect the diagnostics printed by the deploy script.

To confirm which image reference the container was created from:

```bash
docker inspect aquaops-web --format 'image={{.Config.Image}} id={{.Image}} status={{.State.Status}}'
```

## Rollback behavior and limitation

Before replacing an existing container, the deploy script tags its image locally as:

```text
ghcr.io/williampburch/aquaops:rollback-<UTC timestamp>
```

If the new container cannot start or pass its health check, the script makes a
best-effort attempt to recreate the service from that preserved image. Keep these local
rollback tags until the new release and its data are confirmed healthy.

**Image rollback does not reverse database migrations.** Alembic may already have
changed the SQLite database in the shared data volume before a container failure is
detected. If a release requires a database rollback, use the migration-specific recovery
plan or restore the pre-deployment data backup during a planned outage. Do not assume
that starting the old image also restores the old schema.

## Nginx and TLS

Nginx is the only public entry point. It reverse proxies AquaOps HTTPS traffic to:

```nginx
proxy_pass http://127.0.0.1:8010;
```

The application port must remain bound to localhost in `docker-compose.prod.yml`:

```yaml
ports:
  - "127.0.0.1:8010:8000"
```

After an intentional Nginx configuration change, validate before reloading:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Do not expose port `8010` through the Azure network security group or VM firewall.

## Local and legacy deployment paths

Local development may continue to use `docker-compose.yml` and build the repository's
Dockerfile on a development machine. This is separate from production.

`make deploy-build` remains only as a legacy/local troubleshooting fallback. It builds
an image on the machine where it is run and is **not** the normal or recommended Azure
VM deployment path. Production releases must use the prebuilt GHCR image through
`AQUAOPS_IMAGE_TAG=<short-sha> make deploy`.

## Documentation maintenance

Any future change to deployment behavior, ports, Compose files, image registry, volume
names, health checks, rollback behavior, or the backup/restore process must update
`docs/deployment.md` in the same pull request.
