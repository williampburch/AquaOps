# AquaOps

AquaOps is a production-minded personal aquarium tracker built with FastAPI, SQLAlchemy,
Jinja2, Bootstrap 5, HTMX, Alembic, and Docker.

The project is designed as a long-lived personal application and a portfolio-quality example
of a clean, maintainable Python web app.

## Current Status

This repository contains the publishable foundation:

- Layered FastAPI application structure
- SQLAlchemy ORM models for users, sessions, tanks, livestock, plants, generic events, event details, media, and reminders
- Alembic migration environment with an initial schema migration
- Local bcrypt authentication with hashed server-side session tokens
- Responsive dark dashboard shell using Jinja2, Bootstrap 5, and HTMX
- Dockerfile and Docker Compose setup for an Azure Linux VM
- GitHub Actions CI for linting, formatting, and tests
- Architecture, ERD, developer setup, and deployment documentation

## Architecture

AquaOps is a modular monolith using clean architecture boundaries:

```text
Browser
  -> app.web                 FastAPI routes, Jinja templates, HTMX partials
  -> app.application         Use cases and orchestration
  -> app.domain              Framework-independent rules and value types
  -> app.infrastructure      SQLAlchemy, auth persistence, file storage
```

The central design choice is the generic `events` table. Water tests, feedings,
maintenance, fertilizer dosing, notes, and photos all share a single chronological
event stream, with type-specific detail tables for reportable data.

## Quick Start

```bash
cp .env.example .env
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

The app will be available at <http://127.0.0.1:8000>. SQLite data and uploaded media are
stored in Docker volumes.

## Development Commands

```bash
make install
make dev
make lint
make test
make migrate
```

## Documentation

- [Architecture](docs/architecture.md)
- [Database ERD](docs/erd.md)
- [Developer Setup](docs/developer-setup.md)
- [Deployment Guide](docs/deployment.md)
- [Roadmap](docs/roadmap.md)

## Roadmap

The next implementation phases are tank CRUD, inventory management, event logging forms,
fertilizer reminders, photo timelines, and reports/charts.

