# AquaOps

AquaOps is a production-minded personal aquarium tracker built with FastAPI,
SQLAlchemy, PostgreSQL, Jinja2, Bootstrap 5, HTMX, Chart.js, Alembic, and Docker.

It is designed as a real long-lived personal app and as a portfolio-quality example of
a clean, maintainable Python web application.

## Current Status

This repository contains a publishable, working foundation:

- Layered FastAPI application structure with web, application, domain, and infrastructure boundaries
- SQLAlchemy ORM models for users, preferences, sessions, tanks, livestock, plants, species catalog data, generic events, event details, media, reminders, and problem tracking
- Alembic migration environment with schema revisions for initial tables, tank targets, user preferences, and the built-in species catalog
- Local bcrypt authentication with hashed server-side session tokens
- Tank creation, tank detail, and tank-specific water parameter targets
- Water test logging through the generic event model
- Dashboard metric cards, recent events, reminders, latest readings, and trend charts
- Activity stream page powered by the generic event table
- Reports page with event mix and nitrate trend charts
- Catalog-backed livestock and plant entry from tank detail pages, plus inventory summaries grouped by species with quantity totals
- Mobile-friendly livestock and plant lifecycle management with quantity edits,
  tank moves, reasoned removals, and preserved change history
- Actionable Care Queue with clickable overdue, due-today, and upcoming filters,
  task-specific Quick Log links, configurable due-soon windows, and plant-care filtering
- Mobile-first Care Plan Editor for reviewing an existing tank, safely applying
  presets, building an Advanced Custom plan, and adding generic recurring tasks
- Persistent user settings for US/metric display, volume and temperature units, date format, dashboard density, feature modules, and Plant Care auto/on/off behavior
- Branded enterprise-style UI with AquaOps wordmark, ocean/teal palette, responsive command surfaces, and persisted light, dark, and system theme choices
- Public, mobile-first in-app user guide covering setup, daily care, inventory,
  problems, history, reports, preferences, and data export
- Installable PWA shell with branded home-screen icons, standalone mobile
  display, safe-area support, browser install controls, and a privacy-conscious
  offline connection fallback
- Demo seed data for portfolio review and screenshots
- Dockerfile and Docker Compose setup for an Azure Linux VM
- Example Nginx reverse proxy config for hosting behind a domain
- GitHub Actions CI for linting, formatting, and tests
- Architecture, ERD, developer setup, deployment, and roadmap documentation

## Architecture

AquaOps is a modular monolith using clean architecture boundaries:

```text
Browser
  -> app.web                 FastAPI routes, Jinja templates, static assets
  -> app.application         Use cases and orchestration
  -> app.domain              Framework-independent rules and value types
  -> app.infrastructure      SQLAlchemy repositories, auth persistence, storage
```

The central design choice is the generic `events` table. Water tests, feedings,
maintenance, fertilizer dosing, notes, and photos all share a single chronological event
stream, with type-specific detail tables for reportable data.

## Quick Start

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

Set the same local development password in `POSTGRES_PASSWORD` and `DATABASE_URL` in
`.env`, then open <http://127.0.0.1:8000>. PostgreSQL 17 is the canonical database;
Alembic, not application startup, creates and upgrades its schema.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The app will be available at <http://127.0.0.1:8010>. PostgreSQL data and uploaded media
are stored in separate Docker volumes. Development exposes PostgreSQL only on
`127.0.0.1:5432` for local inspection; production does not publish the database port.
The app port remains bound to `127.0.0.1` so it can sit behind Nginx.

## Development Commands

```bash
make install
make dev
make lint
make test
make migrate
make seed-demo
```

Production deploys pull an immutable GHCR image and do not build on the VM:

```bash
AQUAOPS_IMAGE_TAG=<short-sha> make deploy
```

See the [Deployment Guide](docs/deployment.md) before running migrations or a
production deployment.

## Demo Login

Create or refresh a portfolio-friendly demo account:

```bash
aquaops seed-demo
# or
python -m app.scripts.seed_demo
```

Then log in with:

```text
Email: demo@example.com
Password: demo-password
```

The seed command is idempotent: rerunning it replaces the demo account data with a fresh
set of fictional tanks, water tests, feedings, maintenance events, fertilizer events,
livestock, plants, and reminders. It refuses to run when `APP_ENV=production` unless
`--allow-production` is passed.

## Documentation

- [Architecture](docs/architecture.md)
- [Database ERD](docs/erd.md)
- [Developer Setup](docs/developer-setup.md)
- [Deployment Guide](docs/deployment.md)
- [Backup and Restore](docs/backup-restore.md)
- [In-app User Guide](https://aquaops.william-burch.com/guide)
- [Roadmap](docs/roadmap.md)

## Implemented Tracking

- Tank profile: type, volume, start date, lighting, filtration, substrate
- Water targets: ammonia, nitrite, nitrate, pH, temperature, KH, GH, TDS
- Water tests: logged as generic `water_test` events with metric rows
- Activity stream: recent event timeline across all tanks
- Species catalog: built-in starter database for common fish, invertebrates, and plants, with custom-entry fallback
- Inventory: add livestock and plants from tank detail pages, then view grouped summaries with quantity totals
- Reports: event mix and nitrate trend charts
- Notifications: open reminder queue with overdue, due today, and upcoming buckets, plus completion and snoozing
- Quick logging: tank-level feedings, maintenance, water changes, and observations
- Mobile Quick Log: focused water change, water test, and maintenance entry with
  thumb-friendly controls, optional details, and visible validation feedback
- Recent Quick Log context: last water-change volume, previous readings, recent
  maintenance equipment, and remembered tank selection
- Maintenance schedules: per-tank Care Plan Editor with preset provenance,
  scheduled/as-needed modes, optional weekdays/start dates, custom tasks, and
  non-destructive reminder reconciliation
- Recommendations: nitrate-based water change suggestions from tank-specific target ranges, with care queue explanations
- Mobile UX: compact app bar, bottom tab navigation, mobile drawer, and dashboard quick-log priority
- PWA: install from Settings or the browser home-screen menu; private aquarium
  pages and care submissions remain network-only instead of being cached offline
- Preferences: US/metric display, gallons/liters, Fahrenheit/Celsius, date format, compact/comfortable density, and feature module toggles
- Plant Care mode: `Auto`, `On`, or `Off` filtering for fertilizer, root-tab, and plant-care noise
- Problem tracking: open, monitor, and resolve tank issues while connecting tests,
  maintenance, observations, photos, and other relevant timeline events
- Demo data: realistic fictional tanks and event history for screenshots and review

## Roadmap

The next product phase continues daily usefulness through reusable logging values,
richer maintenance automation, configurable onboarding, problem follow-ups,
notification delivery, photo timelines, and dependable backup/restore workflows.
See [docs/roadmap.md](docs/roadmap.md) for the full staged direction and product
principles.
