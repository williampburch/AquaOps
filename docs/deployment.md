# Deployment Guide

Target: Azure Linux VM, Docker Compose, Nginx reverse proxy, SQLite first.

## 1. Prepare the VM

Install Docker, Docker Compose, Git, and Nginx. Clone the repository into a stable path,
for example `/opt/aquaops`.

## 2. Configure Environment

```bash
cp .env.example .env
```

Set production values:

```env
APP_ENV=production
DEBUG=false
SECRET_KEY=<long-random-secret>
DATABASE_URL=sqlite:////app/data/aquaops.db
AUTO_CREATE_TABLES=false
MEDIA_ROOT=/app/media
```

## 3. Run Migrations

```bash
docker compose build
docker compose run --rm web alembic upgrade head
```

## 4. Start the App

```bash
docker compose up -d
```

## 5. Nginx

Use `docker/nginx/aquaops.conf.example` as the starting server block. Point
`server_name` at your domain and proxy requests to `127.0.0.1:8000`.

Add TLS with Certbot or your preferred certificate workflow.

## 6. Backups

Back up the Docker volumes:

- `aquaops_data`: SQLite database
- `aquaops_media`: uploaded photos

For PostgreSQL later, replace `DATABASE_URL` and add a database service or managed
PostgreSQL instance. The ORM and migrations are already designed around that path.

