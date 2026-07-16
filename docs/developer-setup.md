# Developer Setup

## Prerequisites

- Python 3.13
- Docker with Docker Compose
- PostgreSQL 17, normally through the local Compose `db` service

PostgreSQL is the canonical development and integration database. AquaOps does not keep
a second complete SQLite integration path.

## Local setup with a host Python process

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

Choose a local-only password and set it consistently in both `POSTGRES_PASSWORD` and the
password component of `DATABASE_URL` in `.env`. The host connection uses
`localhost:5432`; the Compose web service overrides that host with the internal service
name `db`. Do not commit `.env`.

Open <http://127.0.0.1:8000>.

## Fully containerized development

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm web alembic upgrade head
```

The application is available at <http://127.0.0.1:8010>. The development database port
is bound only to `127.0.0.1` for local inspection. PostgreSQL data persists in
`aquaops_postgres`; media persists separately in `aquaops_media`.

## Schema management

Alembic is authoritative in every environment. `AUTO_CREATE_TABLES=false` is the normal
setting and is mandatory in production.

```bash
alembic upgrade head
alembic check
alembic revision --autogenerate -m "Describe change"
```

After model or migration changes, validate from an empty PostgreSQL database rather than
assuming an already-upgraded local volume proves the full history.

## Tests and quality checks

The integration and web fixtures require a disposable PostgreSQL database URL:

```bash
createdb aquaops_test
export TEST_DATABASE_URL=postgresql+psycopg://aquaops:<password>@localhost:5432/aquaops_test
export DATABASE_URL="$TEST_DATABASE_URL"
alembic upgrade head
alembic check
pytest
ruff check .
black --check .
```

The fixture drops and recreates the test database's `public` schema. Never point
`TEST_DATABASE_URL` at development or production data. Without `TEST_DATABASE_URL`,
PostgreSQL integration and web tests are skipped while pure unit tests can still run.

## Demo data

```bash
aquaops seed-demo
# or
python -m app.scripts.seed_demo
```

The seed runs against the configured PostgreSQL database, replaces only the demo account,
and is idempotent. It refuses production unless `--allow-production` is explicit.

```text
demo@example.com
demo-password
```

The local species catalog is seeded by Alembic. Demo data is portfolio-only; normal
production user data remains primary.
