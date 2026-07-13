# Roadmap

## Product Principles

- Fast common workflows
- Mobile-first daily workflows that are comfortable with one hand, minimize
  typing, and scale naturally to tablets and desktops
- Optional depth when a tank needs it
- Tank-level configuration instead of one-size-fits-all behavior
- User-level preferences for defaults and display choices
- Data ownership through exportable, reviewable history
- Clear history over time for livestock, plants, care, and problems
- Beginner-friendly defaults with sensible presets
- Power-user extensibility without forcing complexity on everyone
- No unnecessary complexity in the default experience

## Completed Foundation

- Project structure and clean architecture layers
- Settings and environment loading
- SQLAlchemy ORM and Alembic migrations
- Local bcrypt authentication and server-side sessions
- Dashboard shell with responsive light, dark, and system themes
- Enterprise-style shell and settings surface with compact/comfortable density
- AquaOps branding system with wordmark treatment, ocean/teal palette, and branded command dashboard
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
- Built-in species catalog seeded with common fish, invertebrates, and plants
- Catalog-backed livestock and plant add forms with custom-entry fallback
- Livestock inventory grouped by species and quantity
- Plant inventory grouped by species and quantity
- Notifications page for open reminders
- Reminder completion and snoozing from the care queue
- Quick logging for feedings, maintenance, water changes, and observations from
  tank detail pages
- Dashboard quick links into focused tank-level water change, water test, and
  maintenance logging
- Tank-level maintenance schedule configs for water changes, feeding, filter
  cleaning, and fertilizer
- Schedule-based reminder refresh after matching care logs
- Nitrate-based water change recommendations using tank target ranges and a
  noise buffer
- Care queue explanations for scheduled reminders and nitrate recommendations
- Maintenance schedule status showing last logged care and next due dates
- Mobile app shell with a compact top bar, bottom tab navigation, and mobile
  dashboard quick-log priority
- Mobile-first Quick Log for focused water changes, water tests, and maintenance,
  with tank selection, optional detail disclosure, and visible save errors
- Water changes entered by percentage or preferred volume unit, with one-tap
  percentage presets, recurring schedule context, and optional conditioner,
  substrate vacuum, glass cleaning, filter cleaning, temperature matching,
  duration, and notes
- Persisted user preferences for units, date format, dashboard density, notification window, and feature modules
- Plant Care auto/on/off mode that suppresses fertilizer and root-tab noise unless needed

## Product Direction

AquaOps is a personal app first: a useful hobbyist tool with portfolio-quality
engineering and an expandable foundation. The goal is not to split the product
into separate apps for simple and advanced aquarium keepers. It should stay one
configurable app with smart care modules, tank-level setup choices, user-level
preferences, and progressive disclosure so each workspace can feel as simple or
as detailed as it needs to be.

## Next: Daily Usefulness

- Extend the Quick Log flow beyond Water Change, Water Test, and Maintenance to
  Feeding, Dose, Observation, Photo, Livestock Change, and Plant Change
- Dropdown-first inputs with free-text fallback for repeated values such as
  foods, units, livestock targets, maintenance equipment, fertilizer products,
  observation tags, and common notes
- Recently used values per user/tank so frequent entries become one-click
  choices without blocking custom text
- Ability to promote repeated custom entries into reusable user-owned options
- Extend water change details with reusable conditioner choices plus TDS and
  nitrate before/after readings
- More polished feeding log flow with reusable foods and livestock targeting
- Feeding shortcuts such as "fed today" and "skipped feeding" with optional
  reason
- More polished maintenance log flow with task-specific fields
- More polished notes and observations log flow
- Photo logging in the same quick-log system
- Livestock change flow for deaths, rehomes, moves, quantity adjustments, and
  acquisitions
- Plant change flow for removals, moves, trims, melt, propagation, and root-tab
  placement context
- Livestock edit/archive workflows
- Plant edit/remove/archive workflows
- Fast data entry with minimal required fields
- Optional detail fields for users who want deeper tracking

## Next: Tank-Specific Maintenance Config

- Custom trimming, root-tab, and CO2 check cadences per tank
- Expanded reminder generation from all configured maintenance rules
- Ability to pause or skip generated maintenance reminders
- Maintenance configs that respect enabled modules, so fertilizer reminders only
  appear for tanks using planted care workflows
- Additional tank-specific recommendation rules based on water test results and
  target ranges
- More parameter-specific guidance that treats ammonia and nitrite differently
  from nitrate, avoiding simplistic "water change for every elevated value"
  behavior
- More configurable threshold buffers and severity levels so tiny test variance
  does not create noisy recommendations
- Deeper recommendation history beyond the current care queue explanation

## Next: Configurable Care Modes

- Setup wizard after account creation
- Tank setup wizard when creating a tank
- Hobby-style setup questions for tank type, plants, fertilizer, CO2,
  reminders, units, and desired tracking detail
- Preset care profiles for common aquarium styles
- Custom mode for users who want complete control
- Tank-level module configuration
- User-level default preferences
- Dashboard density options
- Feature and module toggles
- Progressive disclosure so simple users are not overwhelmed

Suggested care profiles:

- Simple Care
- Water Testing
- Planted Tank
- High-Tech Planted
- Breeder / Grow-Out
- Quarantine
- Custom

## Next: Care Schedule Templates

- Weekly water change template
- Daily feeding template
- Weekly fasting day template
- Feeding schedule template
- Filter cleaning schedule template
- Prefilter sponge cleaning template
- Canister cleaning template
- Water testing schedule while cycling
- Weekly nitrate testing template
- Fertilizer dosing schedule
- Root tab replacement schedule
- Plant trimming schedule
- CO2 check schedule
- Custom recurring care templates
- Templates that create editable tank-specific maintenance configs instead of
  rigid global schedules

## Next: Planted Tank Workflows

- Fertilizer product management
- Flourish-style liquid fertilizer dosing
- Root tab placement and location tracking
- Root tab next-due calculation
- CO2 notes and schedule tracking
- Lighting schedule and intensity notes
- Plant trimming logs
- Algae observations
- Plant health notes
- Plant growth and photo timeline

## Next: Observations and Problem Tracking

- General observations such as cloudy water, algae, fish flashing, hiding,
  spawning behavior, plant melt, new growth, snail eggs, unusual behavior, or
  water clarity changes
- Problem and issue records for algae outbreaks, illness, livestock loss,
  cloudy water, ammonia spikes, and parameter swings
- Ability to attach water tests, maintenance events, notes, and photos to a
  problem record
- Ability to close or resolve a problem while keeping full history

## Later: Species Catalog Intelligence

- Searchable catalog management screens
- Species aliases for alternate common names
- External taxonomy or care-source enrichment
- Compatibility hints for temperature, pH, tank size, and social group needs
- CSV import/export for custom catalog rows
- Shared input catalogs for reusable foods, equipment, fertilizer products,
  observation tags, and other common logging values

## Later: Intelligence and Guidance

- Water parameter alerts after test entry
- Configurable alerts for ammonia, nitrite, nitrate, pH, temperature, TDS, KH,
  and GH
- Beginner-friendly alert defaults focused on high-risk issues
- Trend warnings
- Tank-specific alert thresholds
- Tank-specific maintenance suggestions after water tests
- Recommendation logic that considers parameter type, configured target range,
  severity, and recent maintenance history
- Species compatibility hints
- Temperature, pH, tank-size, and social-group checks from catalog data
- Care suggestions based on recent events and water tests
- "What changed before this problem?" style historical correlation

## Later: Sharing, Export, and Data Ownership

- CSV export
- Printable tank history
- Shareable read-only tank snapshot
- Backup and restore workflows
- Photo timeline export
- Optional public portfolio or demo tank page

## Later: Photos and Richer Reports

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
