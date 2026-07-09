# Roadmap

## Completed Foundation

- Project structure and clean architecture layers
- Settings and environment loading
- SQLAlchemy ORM and Alembic migrations
- Local bcrypt authentication and server-side sessions
- Dashboard shell with responsive light, dark, and system themes
- Docker, Docker Compose, and CI
- Demo seed command for portfolio review

## Current Product Slice

- Tank creation and profile pages
- Tank-specific water parameter target ranges
- Water test logging through the generic event model
- Latest water readings and per-parameter trend charts
- Dashboard cards linking to detailed views
- Activity stream page
- Reports page with event mix and nitrate trend charts
- Read-only livestock inventory grouped by species and quantity
- Read-only plant inventory grouped by species and quantity
- Notifications page for open reminders
- Settings/automation foundation for future schedules, alerts, and feature modules

## Next: Core Data Entry

- Livestock create/edit/archive screens
- Plant create/edit/remove screens
- Generic event entry flow
- Maintenance log UI
- Feeding log UI
- Notes UI

## Next: Fertilizer and Reminders

- Built-in fertilizer product management
- Custom fertilizer products
- Dose logging UI
- Root-tab location tracking
- Automatic next-due calculation in user workflows
- Reminder completion and snoozing
- Configurable care schedules for feeding, water changes, filter cleaning, trimming, and dosing

## Next: Alerts and Automation

- Configurable water-parameter alert thresholds
- Alert generation after water tests
- Notification badges/counts
- Feature module toggles
- Admin/settings persistence

## Next: Photos and Richer Reports

- Local photo uploads
- Photo timeline
- Maintenance and fertilizer reports
- Livestock and plant history reports
- Exportable report data

## Production Hardening

- CSRF protection for all mutating forms
- Rate limiting on auth routes
- Backup and restore scripts
- PostgreSQL deployment profile
- Media storage abstraction for Azure Blob Storage
