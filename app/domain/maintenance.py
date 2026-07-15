from __future__ import annotations

from app.domain.care_plans import CARE_TASKS

MAINTENANCE_CONFIG_LABELS = {key: task.label for key, task in CARE_TASKS.items()}

MAINTENANCE_CONFIG_DEFAULT_INTERVALS = {
    key: task.default_interval_days for key, task in CARE_TASKS.items()
}
