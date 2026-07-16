# PostgreSQL Backup and Restore

The `aquaops_postgres` Docker volume is persistent storage, not a backup. A usable backup
must be a PostgreSQL-native dump, copied off the VM, checksummed, and periodically tested.
Uploaded media remains in `aquaops_media` and needs a separate filesystem archive.

## Create a database dump

From `/opt/aquaops`, with the production `.env` present:

```bash
mkdir -p "$HOME/aquaops-backups"
scripts/postgres-backup.sh \
  "$HOME/aquaops-backups/aquaops-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

The script prints the Compose file, service, database name, and output path; it never
prints the password. It uses `pg_dump --format=custom` inside the PostgreSQL 17 container
and refuses to overwrite an existing output file.

Archive media separately:

```bash
MEDIA_VOLUME="$(docker inspect aquaops-web --format '{{range .Mounts}}{{if eq .Destination "/app/media"}}{{.Name}}{{end}}{{end}}')"
BACKUP_DIR="$HOME/aquaops-backups/$(date -u +%Y%m%dT%H%M%SZ)"
test -n "$MEDIA_VOLUME" || { echo "Media volume not found" >&2; exit 1; }
mkdir -p "$BACKUP_DIR"
docker run --rm -v "$MEDIA_VOLUME:/source:ro" -v "$BACKUP_DIR:/backup" \
  alpine:3.20 tar -C /source -czf /backup/aquaops-media.tar.gz .
sha256sum "$BACKUP_DIR"/*
```

Copy both artifacts and checksums off the VM. This PR intentionally does not add Azure
Blob upload, retention automation, or point-in-time recovery.

## Restore into an empty database

Restoration is destructive operational work and should occur during a planned outage.
Create a fresh empty PostgreSQL database/volume, retain the current volume, and stop web
writes. Then run:

```bash
scripts/postgres-restore.sh /path/to/aquaops.dump --confirm-db aquaops
```

The confirmation must exactly match `POSTGRES_DB`. The script refuses to restore when the
target has any public tables, displays the exact target, and uses `pg_restore` with
`--exit-on-error`, `--no-owner`, and `--no-privileges`.

Restore the media archive into the intended media volume separately, then start the web
service and verify:

```bash
docker compose -f docker-compose.prod.yml up -d web
curl -fsS http://127.0.0.1:8010/health/ready
docker compose -f docker-compose.prod.yml logs --tail 80 web db
```

Confirm login, tank history, Quick Log, Care Queue, inventory, photos, and problems before
discarding any previous database or media volume. A successful `pg_restore` alone is not
a complete recovery test.
