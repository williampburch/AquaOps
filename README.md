# AquaOps

AquaOps is a production-minded personal aquarium tracker built with FastAPI,
SQLAlchemy, Jinja2, Bootstrap 5, HTMX, Chart.js, Alembic, and Docker.

It is designed as a real long-lived personal app and as a portfolio-quality example of
a clean, maintainable Python web application.

## Current Status

This repository contains a publishable, working foundation:

- Layered FastAPI application structure with web, application, domain, and infrastructure boundaries
- SQLAlchemy ORM models for users, preferences, sessions, tanks, livestock, plants, species catalog data, generic events, event details, media, and reminders
- Alembic migration environment with schema revisions for initial tables, tank targets, user preferences, and the built-in species catalog
- Local bcrypt authentication with hashed server-side session tokens
- Tank creation, tank detail, and tank-specific water parameter targets
- Water test logging through the generic event model
- Dashboard metric cards, recent events, reminders, latest readings, and trend charts
- Activity stream page powered by the generic event table
- Reports page with event mix and nitrate trend charts
- Catalog-backed livestock and plant entry from tank detail pages, plus inventory summaries grouped by species with quantity totals
- Notifications page for open reminders with configurable due-soon windows and plant-care filtering
- Persistent user settings for US/metric display, volume and temperature units, date format, dashboard density, feature modules, and Plant Care auto/on/off behavior
- Branded enterprise-style UI with AquaOps wordmark, ocean/teal palette, responsive command surfaces, and persisted light, dark, and system theme choices
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
alembic upgrade head
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The app will be available at <http://127.0.0.1:8010>. SQLite data and uploaded media are
stored in Docker volumes. The Compose file binds the app to `127.0.0.1` so it can sit
behind Nginx without exposing Uvicorn directly to the public internet.

## Development Commands

```bash
make install
make dev
make lint
make test
make migrate
make seed-demo
```

Deploy an existing Docker Compose host from the repo directory:

```bash
scripts/deploy-container.sh
```

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
- Maintenance schedules: per-tank reminder cadences for water changes, feeding, filter cleaning, and fertilizer
- Recommendations: nitrate-based water change suggestions from tank-specific target ranges, with care queue explanations
- Preferences: US/metric display, gallons/liters, Fahrenheit/Celsius, date format, compact/comfortable density, and feature module toggles
- Plant Care mode: `Auto`, `On`, or `Off` filtering for fertilizer, root-tab, and plant-care noise
- Demo data: realistic fictional tanks and event history for screenshots and review

## Roadmap

The next product phase continues daily usefulness: dropdown-first task logging with
free-text fallback, edit/archive workflows for livestock and plants, richer maintenance
automation, and configurable care modes. From there, the roadmap expands into reusable
care schedule templates, planted tank workflows, observation/problem tracking, richer
catalog intelligence, exports, and production hardening. See
[docs/roadmap.md](docs/roadmap.md) for the full staged direction and product
principles.
