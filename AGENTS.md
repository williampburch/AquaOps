# AGENTS.md

## Purpose

This file gives repository-specific guidance to AI coding agents working on AquaOps.

AquaOps is a production-minded personal aquarium tracker and portfolio-quality Python web application. It is intended to be useful for years, not just impressive in a demo.

Prefer practical, maintainable, boring solutions over clever complexity.

## Product priorities

AquaOps should feel like the fastest, clearest freshwater aquarium care log, especially on a phone.

The product should optimize for:

* Mobile-first daily use
* Fast quick logging while standing at the tank
* Minimal typing for common workflows
* Thumb-friendly controls
* Beautiful, modern, polished UX
* Clear, trustworthy history
* Progressive disclosure instead of overwhelming screens
* Beginner-friendly defaults
* Optional depth for power users
* Tank-level configuration instead of one-size-fits-all behavior
* User-owned data with exportable history

Do not chase features just because they are possible. A smaller feature that makes daily aquarium care faster and clearer is usually better than a large feature that adds friction.

The core product loop is:

1. Remember what is due.
2. Log care quickly.
3. Review a trustworthy chronological history.
4. Understand what changed.
5. Decide what to do next.

The long-term differentiator is helping answer: “What changed before this problem?”

That means new features should preserve or improve the timeline connection between water tests, maintenance, feeding, livestock changes, plant changes, observations, photos, and reminders.

## UX expectations

AquaOps should look and feel like a modern, polished app, not a plain admin dashboard.

When adding or changing screens:

* Design mobile first.
* Keep primary actions obvious.
* Keep quick-log paths short.
* Avoid forcing typing when a recent value, preset, dropdown, or repeat-last action would work.
* Use progressive disclosure for optional details.
* Keep forms comfortable on small screens.
* Preserve useful desktop/tablet layouts without sacrificing mobile.
* Avoid cluttering the dashboard with low-value information.
* Make validation errors visible and understandable.
* Keep destructive actions explicit and reversible where practical.
* Maintain visual consistency with the AquaOps brand, ocean/teal palette, responsive command surfaces, and light/dark/system theme support.

Daily workflows should feel fast enough that the user will actually keep using the app.

## Architecture expectations

AquaOps is a server-rendered FastAPI modular monolith.

Respect the existing package boundaries:

* `app.web`: FastAPI routes, browser dependencies, templates, static assets
* `app.application`: use cases and read/write service orchestration
* `app.domain`: framework-independent rules, event types, measurement keys, reminder rules, user preference rules, value types
* `app.infrastructure`: SQLAlchemy models, repositories, auth/session persistence, storage
* `alembic`: schema migrations
* `tests`: unit, application, and web tests

Keep route handlers thin when practical.

Prefer putting business logic in application services or domain helpers instead of burying it in templates or route handlers.

Do not bypass repositories or persistence patterns without a good reason.

Avoid unnecessary abstractions, but do not collapse everything into route functions.

Preserve the SQLite-now, PostgreSQL-later path.

## Event and history model

The shared event timeline is central to AquaOps.

Water tests, feedings, maintenance, fertilizer/root-tab dosing, notes, photos, livestock changes, plant changes, and observations should remain connected to chronological history.

When adding new care workflows, consider whether they should produce an event or event detail record.

Avoid hiding reportable long-term history inside opaque JSON when structured detail tables would make future reports, exports, and analysis easier.

Preserve user trust in history. Do not silently delete meaningful historical records unless the feature explicitly calls for deletion and the user confirms it.

Prefer archive/close/end-date patterns for livestock, plants, reminders, and problems when history should remain reviewable.

## Data and schema changes

Use Alembic migrations for production schema changes.

Do not rely on `AUTO_CREATE_TABLES` for production schema changes.

When changing models:

* Add or update Alembic migrations.
* Keep migrations safe for existing SQLite production data.
* Consider how the change would later translate to PostgreSQL.
* Add tests when practical.
* Update docs if setup, deployment, export, or user-visible behavior changes.

Be careful with production SQLite. Assume the user cares about preserving long-term aquarium history.

## Authentication and security

Local authentication uses bcrypt password hashes and server-side sessions.

Be conservative with auth/session changes.

Never commit `.env`.

Never print or expose production secret values.

When checking `.env`, verify only presence or variable names, not values.

Do not weaken cookie/session behavior for convenience.

For mutating forms, prefer security-minded patterns and keep future CSRF protection in mind.

## Quick logging guidance

Quick logging is one of the most important product areas.

For any quick-log workflow, optimize for:

* Few required fields
* Recently used values
* Repeat-last actions
* Sensible presets
* Typeable dropdowns where useful
* Free-text fallback when needed
* Clear success/failure feedback
* Mobile comfort
* Preservation of structured history

Important quick-log areas include:

* Water changes
* Water tests
* Feedings
* Maintenance
* Observations
* Photos
* Fertilizer dosing
* Livestock changes
* Plant changes

A feature is not truly done if it works on desktop but feels clumsy on a phone.

## Reminders and recommendations

Reminders and recommendations should be useful, not noisy.

Respect tank-level care profiles, maintenance schedules, user preferences, and feature modules.

Plant Care should stay quiet for users who do not need it.

Recommendation logic should avoid simplistic advice. For example, ammonia, nitrite, nitrate, pH, temperature, KH, GH, and TDS should not all be treated the same.

Prefer explanations that tell the user why something is due or recommended.

## Data ownership, export, backup, and restore

AquaOps should protect the user’s long-term data.

Preserve and improve exportability.

When adding new user-owned data, consider whether it belongs in account export.

Backup and restore are high-priority production-hardening areas.

Do not make changes that put SQLite data or uploaded media at unnecessary risk.

## Production deployment

The canonical production deployment path is GHCR image-based deployment.

Production image:

`ghcr.io/williampburch/aquaops`

Production VM repo directory:

`/opt/aquaops`

Production Compose file:

`docker-compose.prod.yml`

Normal production deploy command:

`AQUAOPS_IMAGE_TAG=<short-sha> make deploy`

`make deploy` runs:

`scripts/deploy-image.sh`

Production deployment must not build images on the VM.

Do not document or reintroduce these as the normal production deployment path:

* `docker compose build`
* `docker compose up --build`
* `make deploy-build`

`make deploy-build` may exist only as a legacy/local troubleshooting fallback.

Production app binding:

`127.0.0.1:8010:8000`

Nginx reverse proxies public HTTPS traffic to:

`http://127.0.0.1:8010`

Health check:

`http://127.0.0.1:8010/health`

Persistent Docker volumes:

* `aquaops_data`
* `aquaops_media`

On the VM these may be Compose-prefixed, for example:

* `aquaops_aquaops_data`
* `aquaops_aquaops_media`

Use immutable short SHA image tags for production deployments whenever possible.

Avoid recommending `latest` for production except to explain why it is less reproducible than a short SHA tag.

## Deployment safety

The deployment script pulls the target GHCR image, runs Alembic migrations from that image, recreates the container without building, and health-checks the localhost endpoint.

The script preserves the previous image with a timestamped rollback tag before deploying.

Important limitation: rolling back the container image does not automatically roll back database migrations already applied to the shared SQLite volume.

Before production deployments that may run migrations, remind the operator to confirm a current backup.

## Deployment documentation rule

Any PR that changes deployment behavior must update `docs/deployment.md` in the same PR.

This includes changes to:

* Docker image names
* GHCR publishing
* Docker Compose files
* production ports
* Nginx assumptions
* health checks
* Alembic migration flow
* backup steps
* restore steps
* rollback behavior
* environment variables
* Makefile deployment targets
* production verification commands

Keep deployment documentation aligned with the actual tested production process.

## Documentation expectations

Keep docs current with code.

Update documentation when changes affect:

* user workflows
* setup
* deployment
* operations
* backups
* restore
* exports
* architecture
* environment variables
* screenshots or demo behavior
* public portfolio review

Do not let README, roadmap, architecture docs, and deployment docs contradict each other.

## Testing expectations

Before finishing meaningful changes, run the relevant tests when practical.

Common commands:

`make test`

`pytest`

For style/lint-related changes:

`make lint`

For deployment script changes, include or update tests covering deployment behavior.

For schema changes, include migrations and test the upgraded path when practical.

For UI changes, manually reason through mobile behavior and common user flows.

## GitHub Actions and CI

GitHub Actions publishes Docker images to GHCR on `main` and manual runs.

Images are tagged with:

* `latest`
* `main`
* immutable short commit SHA

The VM deploys only when an operator starts deployment from the VM.

Do not make GitHub Actions SSH into the VM or perform automatic production deployment unless explicitly requested.

## Code style and maintainability

Prefer clear names and straightforward flow.

Avoid clever abstractions that make the app harder to work on.

Keep functions focused.

Keep templates readable.

Avoid duplicating business rules across templates, routes, and services.

Preserve existing conventions unless there is a clear reason to improve them.

When introducing a new pattern, use it consistently and document it if future agents need to follow it.

## Portfolio quality

AquaOps should be credible as a real personal production app and as a portfolio project.

That means changes should demonstrate:

* clean architecture
* practical deployment
* reliable data handling
* polished UX
* thoughtful product direction
* tests where they matter
* clear documentation

Do not add toy/demo-only features that make the app less useful.

Demo data is valuable for portfolio review, but production behavior and real user data should always come first.

## Agent behavior

When working in this repo:

* Read the relevant docs before making large changes.
* Prefer small, coherent changes.
* Explain tradeoffs when changing architecture, deployment, data models, or UX direction.
* Do not expose secrets.
* Do not remove production safeguards for convenience.
* Do not rewrite large areas unnecessarily.
* Keep the app easy to run, easy to deploy, and easy to use.
* When uncertain, preserve the product priorities: mobile-first, quick logging, beautiful UX, useful history, and production safety.
