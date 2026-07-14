# Deployment Guide

Target: Azure Linux VM, Docker Compose, Nginx reverse proxy, SQLite first.

This guide assumes AquaOps is one of several sites on the same VM. Each site should have
its own domain or subdomain, its own Compose project directory, and its own localhost
port behind Nginx.

Local development continues to use the base Compose file and local Dockerfile:

```bash
docker compose up --build
```

Production uses `docker-compose.prod.yml`, which contains an `image:` reference and no
`build:` section.

## 1. Prepare the VM

Install Docker, the Docker Compose plugin, Git, and Nginx. On Ubuntu:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git nginx
```

Install Docker from Docker's official instructions for your distribution, then verify:

```bash
docker --version
docker compose version
sudo systemctl status nginx
```

Clone the repository into a stable path:

```bash
sudo mkdir -p /opt/aquaops
sudo chown "$USER":"$USER" /opt/aquaops
git clone https://github.com/williampburch/AquaOps.git /opt/aquaops
cd /opt/aquaops
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Set production values in `.env`:

```env
APP_ENV=production
DEBUG=false
SECRET_KEY=<long-random-secret>
DATABASE_URL=sqlite:////app/data/aquaops.db
AUTO_CREATE_TABLES=false
SESSION_COOKIE_NAME=aquaops_session
SESSION_TTL_DAYS=30
DATA_DIR=/app/data
MEDIA_ROOT=/app/media
```

Generate a secret key with:

```bash
openssl rand -hex 32
```

Do not reuse `SECRET_KEY` from another site. It protects session-token hashes.

## 3. Choose a Local Port

The Compose file binds Uvicorn to localhost only:

```yaml
ports:
  - "127.0.0.1:8010:8000"
```

If another site already uses port `8010`, change only the host-side port:

```yaml
ports:
  - "127.0.0.1:8020:8000"
```

Then proxy Nginx to the same port, for example `http://127.0.0.1:8020`.

## 4. Authenticate to GHCR

The AquaOps package may require GitHub Container Registry authentication. Create a
GitHub personal access token with `read:packages`, then authenticate once as the VM user
that runs deployments:

```bash
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u williampburch --password-stdin
```

Do not place the token in the repository or `.env`. Docker stores the login in that
user's Docker client configuration. A public package can be pulled without logging in.

## 5. Deploy and Start the App

Deploy the most recently published `latest` image:

```bash
make deploy
```

The production deployment script pulls the image, runs Alembic migrations from that
image, recreates the service without building, and health-checks the localhost endpoint.
The VM no longer builds AquaOps images during normal production deployments.
For a reproducible deployment, use the short-SHA tag published by GitHub Actions:

```bash
AQUAOPS_IMAGE_TAG=3dc1580 make deploy
```

Use the tag shown for the commit you intend to deploy. `latest` is the default when
`AQUAOPS_IMAGE_TAG` is unset.

Check the app locally from the VM:

```bash
curl -f http://127.0.0.1:8010/health
```

Use your chosen host port if you changed it in Compose.

## 6. Nginx for Multiple Sites

Use one Nginx server block per site. AquaOps ships an example at
`docker/nginx/aquaops.conf.example`.

Copy it into `sites-available`:

```bash
sudo cp docker/nginx/aquaops.conf.example /etc/nginx/sites-available/aquaops.conf
sudo nano /etc/nginx/sites-available/aquaops.conf
```

Set:

- `server_name` to your AquaOps domain, such as `aquaops.example.com`
- both `proxy_pass` values to the localhost port chosen in Compose

Example:

```nginx
server {
    listen 80;
    server_name aquaops.example.com;

    client_max_body_size 25m;

    location /static/ {
        proxy_pass http://127.0.0.1:8010/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

AquaOps versions the application stylesheet URL from the built file timestamp.
This allows long-lived browser and Nginx caching while ensuring a new container
build immediately points browsers to the current CSS instead of a stale mobile
layout.

Enable the site and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/aquaops.conf /etc/nginx/sites-enabled/aquaops.conf
sudo nginx -t
sudo systemctl reload nginx
```

Each additional site on the VM should use a different `server_name` and, if it is a
separate containerized app, a different localhost port.

If the default Nginx welcome site is still enabled and conflicts with your domains,
disable it:

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

At the VM firewall or cloud network security group, expose only HTTP/HTTPS to the
internet. The AquaOps app port should stay bound to `127.0.0.1`.

## 7. TLS

Add TLS with Certbot or your preferred certificate workflow:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d aquaops.example.com
```

Certbot will update the Nginx server block and reload Nginx after issuing the certificate.

## 8. Backups

Back up the Compose-managed Docker volumes:

- `aquaops_data`: SQLite database
- `aquaops_media`: uploaded photos

Depending on the Compose project name, Docker may prefix these names, for example
`aquaops_aquaops_data`. Confirm with:

```bash
docker volume ls
```

For a simple SQLite backup, stop the container or ensure the database is quiet, then copy
the database out of the data volume. For long-term production use, add a tested backup
script before relying on the app for critical history.

## 9. Updating

From `/opt/aquaops`:

```bash
make deploy
```

`make deploy` runs `scripts/deploy-image.sh`. The script:

- refuses to continue if Docker, the Compose plugin, `curl`, or `flock` is unavailable
- takes a non-blocking deployment lock so two releases cannot overlap
- preserves the currently running image under a local rollback tag
- pulls `ghcr.io/williampburch/aquaops:${AQUAOPS_IMAGE_TAG:-latest}`
- runs `alembic upgrade head` in a one-off container using the pulled image
- recreates `aquaops-web` with `--no-build`
- retries `http://127.0.0.1:8010/health` and prints container status, logs, and inspect
  output on failure
- attempts to recreate and health-check the previous image when restart or health
  verification fails

Deploy an immutable SHA-tagged image when possible:

```bash
AQUAOPS_IMAGE_TAG=<short-sha> make deploy
```

The image rollback is best effort. It restores the previous container image, but it does
not downgrade database migrations already applied to the shared SQLite volume. Keep a
tested database and media backup before deployments that include schema changes. Local
`rollback-*` image tags are retained and may be pruned manually after a deployment is
confirmed healthy.

The former VM-build deployment remains available for troubleshooting, but is not the
normal production path:

```bash
make deploy-build
```

That target runs `scripts/deploy-container.sh` and builds locally. Local development still
uses `docker compose up --build` with `docker-compose.yml`.

## GHCR Image Publishing

The separate `Publish Docker image` GitHub Actions workflow now builds the repository
`Dockerfile` and publishes it to `ghcr.io/williampburch/aquaops` after pushes to `main`.
It can also be started manually with **Actions → Publish Docker image → Run workflow**.
Published images receive `latest`, `main`, and short commit-SHA tags.

Production now consumes these images through `docker-compose.prod.yml` and
`scripts/deploy-image.sh`. GitHub Actions publishes images but does not connect to or
modify the VM; an operator still starts each deployment from the VM with `make deploy`.

## 10. PostgreSQL Later

SQLite is intentional for the first deployment. To move later, replace `DATABASE_URL` with
a PostgreSQL URL and add either a PostgreSQL service or a managed database. The ORM and
migrations are structured to support that path.
