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

