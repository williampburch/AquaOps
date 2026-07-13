# Deployment Guide

Target: Azure Linux VM, Docker Compose, Nginx reverse proxy, SQLite first.

This guide assumes AquaOps is one of several sites on the same VM. Each site should have
its own domain or subdomain, its own Compose project directory, and its own localhost
port behind Nginx.

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

## 4. Run Migrations

```bash
docker compose build
docker compose run --rm web alembic upgrade head
```

## 5. Start the App

```bash
docker compose up -d
docker compose ps
docker compose logs -f web
```

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
scripts/deploy-container.sh
```

The deploy script fetches `origin/main`, fast-forwards the local checkout, rebuilds the
`web` image, runs Alembic migrations, restarts the container, and prints `docker compose ps`.
It refuses to run when tracked files have local changes unless `--force-dirty` is supplied.
Untracked reference files, such as local mockups under `assets/`, do not block deployment.

Useful options:

```bash
scripts/deploy-container.sh --branch main
scripts/deploy-container.sh --skip-build
scripts/deploy-container.sh --skip-migrations
docker compose logs -f web
```

## 10. PostgreSQL Later

SQLite is intentional for the first deployment. To move later, replace `DATABASE_URL` with
a PostgreSQL URL and add either a PostgreSQL service or a managed database. The ORM and
migrations are structured to support that path.
