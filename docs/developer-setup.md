# Developer Setup

## Prerequisites

- Python 3.13
- Docker and Docker Compose
- SQLite, bundled with Python

## Local Setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Quality Checks

```bash
ruff check .
black --check .
pytest
```

Or use the Makefile:

```bash
make lint
make test
```

## Migrations

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "Describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

The app can auto-create tables in development through `AUTO_CREATE_TABLES=true`, but
production deployments should rely on Alembic migrations.

## Current Product Slice

After creating an account, create a tank from `/tanks`, adjust its water parameter
targets, and log water tests from the tank detail page. Trend charts render after at
least one water test exists.

## Demo Data

Seed a realistic demo account:

```bash
aquaops seed-demo
```

Alternative module form:

```bash
python -m app.scripts.seed_demo
```

Login:

```text
demo@example.com
demo-password
```

The command replaces only the demo account on each run. It will not run in production
unless `--allow-production` is supplied.
