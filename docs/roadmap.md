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

## Product Focus

AquaOps should be the fastest, clearest freshwater aquarium care log, especially
on a phone. Its initial audience is engaged freshwater and planted-tank keepers,
particularly people managing multiple display, breeding, grow-out, quarantine,
or propagation tanks. It should win through low-friction daily use and useful
history rather than trying to have the longest feature list.

The core product loop is:

1. Remember what is due
2. Log care while standing at the tank
3. Review a trustworthy chronological history
4. Understand what changed
5. Decide what to do next

The long-term differentiator is answering questions such as "What changed before
this problem?" by connecting water tests, maintenance, livestock and plant
changes, observations, and photos on one timeline.

## Completed Foundation

- Project structure and clean architecture layers
- Settings and environment loading
- SQLAlchemy ORM and Alembic migrations
- Local bcrypt authentication and server-side sessions
- Dashboard shell with responsive light, dark, and system themes, including a
  dark default and one-tap light/dark swap for new mobile sessions
- Enterprise-style shell and settings surface with compact/comfortable density
- AquaOps branding system with wordmark treatment, ocean/teal palette, and branded command dashboard
- Docker, Docker Compose, and CI
- Demo seed command for portfolio review

## Current Product Slice

- Tank creation and profile pages
- Mobile-first tank setup wizard with Simple Care, Water Testing, Planted Tank,
  High-Tech Planted, Breeder / Grow-Out, Quarantine, and Custom profiles
- Care profiles that persist on each tank and create immediately useful,
  editable feeding, water-change, water-test, filter, fertilizer, and plant-trim
  schedules with starter items in the Care Queue
- Mobile-first Care Plan Editor available from aquarium details and each Care
  Queue tank item, with safe preset merge/replace/start-fresh choices, explicit
  profile/manual/legacy provenance, and Advanced Custom progressive disclosure
- Advanced Custom schedules for all currently supported care types, including
  scheduled/as-needed modes, cadence, optional weekday/start date, notes,
  reminder controls, and user-named recurring tasks
- Non-destructive reminder reconciliation that supersedes obsolete or duplicate
  open reminders, preserves completed history, and schedules the next occurrence
  when a linked Care Queue item is completed
- Separate GitHub Actions image publishing to GHCR on `main` and manual runs,
  tagged as `latest`, `main`, and the immutable short commit SHA; the VM still
  deploys only when an operator starts it
- Pull-only production deployment from GHCR with PostgreSQL 17 on the existing VM,
  an isolated production Compose file, a single-deploy lock, database readiness waits,
  Alembic migrations from the pulled image, bounded localhost health checks, failure
  diagnostics, and best-effort prior-image rollback while preserving database and media
  volumes
- Tank-specific water parameter target ranges
- Water test logging through the generic event model
- Latest water readings and per-parameter trend charts
- Dashboard cards linking to detailed views
- Activity stream page
- Mobile-first tank Care History with event-type filters, maintenance task
  filtering, structured care details, and older/newer pagination beyond the
  compact recent-event preview
- Contextual "Last time" summaries in Water Change, Water Test, and Maintenance
  Quick Log, with direct links into the matching tank history
- Reports page with event mix and nitrate trend charts
- Built-in species catalog seeded with common fish, invertebrates, and plants
- Catalog-backed livestock and plant add forms with custom-entry fallback
- Livestock inventory grouped by species and quantity
- Plant inventory grouped by species and quantity
- Mobile-friendly item-level livestock and plant management for edits, quantity
  changes, tank moves, and reasoned removals that remain in event history
- Mobile Quick Log livestock and plant changes for catalog-backed or custom
  additions, one-tap quantity increases, partial-group reductions, and reasoned
  removals that automatically archive an entry when its quantity reaches zero
- Actionable Care Queue with clickable overdue, due-today, and upcoming status
  cards plus task-specific Quick Log links
- Reminder completion and snoozing from the care queue, with matching logged care
  automatically satisfying connected reminders and recommendations
- Quick logging for feedings, maintenance, water changes, and observations from
  tank detail pages
- Dashboard quick links into focused tank-level water change, water test,
  feeding, observation, and maintenance logging
- Tank-level maintenance schedule configs for water changes, feeding, filter
  cleaning, and fertilizer
- Schedule-based reminder refresh after matching care logs
- Nitrate-based water change recommendations using tank target ranges and a
  noise buffer
- Care queue explanations for scheduled reminders and nitrate recommendations
- Maintenance schedule status showing last logged care and next due dates
- Mobile app shell with a compact top bar, bottom tab navigation, and mobile
  dashboard quick-log priority
- Public, mobile-first in-app user guide with quick-start steps, task-focused
  feature guidance, daily routines, and direct links into core workflows
- Installable PWA behavior with AquaOps home-screen icons, standalone display,
  Android/desktop install prompting, iPhone/iPad Add to Home Screen guidance,
  safe-area-aware mobile chrome, and a privacy-conscious offline fallback that
  never caches authenticated aquarium pages or form submissions
- Mobile-first Quick Log for focused water changes, water tests, feeding,
  observations, and maintenance, with tank selection, optional detail
  disclosure, and visible save errors
- Adaptive mobile Quick Log launcher that keeps the four most common care
  actions immediately visible while grouping photos, observations, dosing,
  livestock, and plant changes behind one compact secondary-action control
- Mobile Photo Quick Log with native rear-camera capture, authenticated local
  media delivery, upload validation, previews, captions, and photos embedded in
  the activity timeline
- Water changes entered by percentage or preferred volume unit, with one-tap
  percentage presets, recurring schedule context, automatically reusable
  conditioner names, optional nitrate/TDS before-and-after readings, substrate
  vacuum, glass cleaning, filter cleaning, temperature matching, duration, and
  notes
- Quick Log recent-value assistance for the last water-change volume, prior water
  readings, one-tap reuse of the latest nitrate/TDS as pre-change readings,
  recently used conditioners and maintenance equipment, and remembered tank
  selection
- Feeding Quick Log with a searchable, typeable multi-select for recently used
  and custom foods, multiple foods per feeding, recent and common one-tap units,
  quick livestock targets, one-tap repeat-last feeding, and skipped feeding
  history with an optional reason
- Observation Quick Log with behavior, health, algae, plant growth, water
  clarity, and spawning presets, recently used titles, and optional detail
- Fertilizer Dose Quick Log with automatically reusable user-owned products,
  recent locations, structured amount and unit history, and one-tap repeat-last
  dosing
- Portable account data export as a ZIP of CSV datasets covering tanks, care
  events and details, water measurements, schedules, reminders, livestock,
  plants, fertilizer products, problem records and event links, preferences,
  and a machine-readable manifest
- Mobile-first problem records for algae, illness, livestock loss, cloudy water,
  ammonia spikes, parameter swings, equipment failures, and plant decline, with
  severity and open, monitoring, or resolved states
- Problem timelines that connect existing tests, maintenance, observations,
  photos, and other tank events while preserving opening, status, and resolution
  updates in the shared chronological history
- Persisted user preferences for units, date format, dashboard density, notification window, and feature modules
- Plant Care auto/on/off mode that suppresses fertilizer and root-tab noise unless needed

## Product Direction

AquaOps is a personal app first: a useful hobbyist tool with portfolio-quality
engineering and an expandable foundation. The goal is not to split the product
into separate apps for simple and advanced aquarium keepers. It should stay one
configurable app with smart care modules, tank-level setup choices, user-level
preferences, and progressive disclosure so each workspace can feel as simple or
as detailed as it needs to be.

## Adoption Priority

Near-term work should follow this order:

1. Frictionless mobile logging and inventory lifecycle management
2. Recently used values and repeat-last-action shortcuts
3. Tank-specific care history and contextual last-action visibility
4. Notification delivery outside the app through push or email
5. Photo capture and tank, plant, and livestock timelines
6. Import, backup automation, and restore so long-term data remains trustworthy
7. Historical explanations that help connect a problem with preceding changes
8. Low-friction post-registration onboarding and install education

Reef-specific breadth is not an immediate priority. If AquaOps later targets reef
keepers, that should be an intentional expansion covering salinity, alkalinity,
calcium, magnesium, phosphate, dosing, equipment, and controller integrations.

## Next: Daily Usefulness

- Recently used and reusable common notes across Quick Log workflows
- Ability to promote repeated custom entries into reusable user-owned options
- Promote repeated custom foods and livestock targets into reusable user-owned
  options shared across tanks
- More polished maintenance log flow with task-specific fields
- Extend livestock and plant changes with partial-group moves, trims, root-tab
  placement context, and richer per-entry timelines
- Fast data entry with minimal required fields
- Optional detail fields for users who want deeper tracking

## Next: Tank-Specific Maintenance Config

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
- Hobby-style setup questions for tank type, plants, fertilizer, CO2,
  reminders, units, and desired tracking detail
- Tank-level module configuration
- Extend the current user preferences, dashboard density options, feature
  toggles, and progressive disclosure into onboarding defaults

## Next: Reusable Care Templates

- Save a user-built care plan as a reusable template
- Named cycling, prefilter, canister, root-tab, CO₂, and fasting-day templates
- Preview template changes before applying them across several tanks

## Next: Planted Tank Workflows

- Fertilizer product management
- Root tab placement and location tracking
- Root tab next-due calculation
- CO2 notes and schedule tracking
- Lighting schedule and intensity notes
- Plant trimming logs
- Algae observations
- Plant health notes
- Plant growth and photo timeline

## Next: Observations and Problem Tracking

- Dedicated problem filters and tank-level active-problem summaries
- Faster follow-up logging directly from a problem record
- Structured treatments, affected livestock or plants, outcomes, and recurrence
  tracking without losing the connected event timeline
- Assisted "what changed before this problem?" comparisons across connected and
  nearby history

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

- Printable tank history
- Shareable read-only tank snapshot
- Import, backup automation, and restore workflows
- Photo timeline export
- Optional public portfolio or demo tank page

## Later: Controlled Beta and Tank Sharing

- Controlled beta registration with explicit operator approval or an allowlist
- Private tank sharing with clear viewer/editor roles
- Invitations, revocation, and an audit trail for shared-tank changes
- No billing, subscription, or entitlement model until real usage justifies it

## Later: Photos and Richer Reports

- Dedicated tank, plant, and livestock photo timelines beyond the current
  unified activity stream
- Maintenance and fertilizer reports
- Livestock and plant history reports
- Exportable report data

## Production Hardening

- Add optional protected-environment approval around the existing manual,
  pull-only GHCR production delivery path
- Add automated pre-migration volume backups and a tested database-aware rollback
  procedure beyond the current best-effort image rollback
- CSRF protection for all mutating forms
- Rate limiting on auth routes
- Expand PostgreSQL backup verification and off-VM retention automation
- Media storage abstraction for Azure Blob Storage
