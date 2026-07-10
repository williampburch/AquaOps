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

Open <http://127.0.0.1:8000>.

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

Format local changes:

```bash
make format
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
production deployments should use Alembic migrations with `AUTO_CREATE_TABLES=false`.

## Current Product Slice

After creating an account, the current app supports:

- Dashboard cards for tanks, events, livestock, and plants
- Tank creation and tank detail pages
- Per-tank water parameter targets
- Water test logging from a tank detail page
- Latest readings and per-parameter trend charts
- `/events` activity stream
- `/reports` event mix and nitrate trend charts
- `/livestock` inventory summary grouped by species
- `/plants` inventory summary grouped by species
- `/notifications` open reminder queue
- `/settings` persisted workspace preferences for units, dates, dashboard density, modules, and Plant Care mode

The settings flow stores per-user preferences in `user_preferences`. Volumes remain
canonical in liters in the database, while the UI can display and accept either gallons or
liters. New tank target presets honor the user's preferred temperature unit.

Feature modules can be simplified per workspace. Plant Care supports `Auto`, `On`, and
`Off`; in auto mode, fertilizer and root-tab reminders stay hidden until the app detects
active plants, a planted tank, or fertilizer history.

Some domain tables already exist before full UI workflows do. Maintenance, fertilizer,
feeding, media, and reminder detail models are present, while complete user-facing CRUD
flows for those areas are still roadmap work.

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
