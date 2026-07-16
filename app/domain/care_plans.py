from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class CareTaskDefinition:
    key: str
    label: str
    default_interval_days: int
    group: str
    quick_log_connected: bool
    description: str


CARE_TASKS = {
    task.key: task
    for task in (
        CareTaskDefinition(
            "water_change",
            "Water changes",
            7,
            "Water",
            True,
            "Connected to Water Change Quick Log.",
        ),
        CareTaskDefinition(
            "water_test",
            "Water testing",
            7,
            "Water",
            True,
            "Connected to Water Test Quick Log.",
        ),
        CareTaskDefinition(
            "feeding",
            "Feeding",
            1,
            "Livestock",
            True,
            "Connected to Feeding Quick Log.",
        ),
        CareTaskDefinition(
            "fasting_day",
            "Fasting day",
            7,
            "Livestock",
            False,
            "Reminder-only; record a skipped feeding separately when useful.",
        ),
        CareTaskDefinition(
            "filter_cleaning",
            "Filter cleaning",
            30,
            "Equipment",
            True,
            "Connected to maintenance logging.",
        ),
        CareTaskDefinition(
            "prefilter_cleaning",
            "Prefilter sponge cleaning",
            14,
            "Equipment",
            False,
            "Reminder-only generic equipment task.",
        ),
        CareTaskDefinition(
            "canister_maintenance",
            "Canister maintenance",
            60,
            "Equipment",
            False,
            "Reminder-only generic equipment task.",
        ),
        CareTaskDefinition(
            "glass_cleaning",
            "Glass cleaning",
            14,
            "Aquarium",
            True,
            "Connected to maintenance logging.",
        ),
        CareTaskDefinition(
            "substrate_vacuum",
            "Substrate vacuuming",
            14,
            "Aquarium",
            True,
            "Connected to maintenance logging.",
        ),
        CareTaskDefinition(
            "fertilizer",
            "Fertilizer dosing",
            7,
            "Plant care",
            True,
            "Connected to fertilizer Quick Log.",
        ),
        CareTaskDefinition(
            "root_tabs",
            "Root-tab replacement",
            90,
            "Plant care",
            False,
            "Reminder-only until placement-aware root-tab logging is added.",
        ),
        CareTaskDefinition(
            "plant_trimming",
            "Plant trimming",
            30,
            "Plant care",
            True,
            "Connected to maintenance logging.",
        ),
        CareTaskDefinition(
            "co2_check",
            "CO₂ check",
            7,
            "Plant care",
            False,
            "Reminder-only until structured CO₂ logging is added.",
        ),
        CareTaskDefinition(
            "equipment_inspection",
            "Equipment inspection",
            30,
            "Equipment",
            False,
            "Reminder-only generic equipment task.",
        ),
    )
}

QUICK_LOG_ACTION_BY_TASK = {
    "water_change": "water_change",
    "water_test": "water_test",
    "feeding": "feeding",
    "filter_cleaning": "maintenance",
    "glass_cleaning": "maintenance",
    "substrate_vacuum": "maintenance",
    "fertilizer": "dose",
    "plant_trimming": "maintenance",
}

WEEKDAY_LABELS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def task_label(config_type: str, custom_label: str | None = None) -> str:
    if custom_label:
        return custom_label
    task = CARE_TASKS.get(config_type)
    return task.label if task else config_type.replace("_", " ").title()


def quick_log_action(config_type: str) -> str | None:
    task = CARE_TASKS.get(config_type)
    if task is None or not task.quick_log_connected:
        return None
    return QUICK_LOG_ACTION_BY_TASK.get(config_type)


def next_schedule_due_at(
    base: datetime,
    interval_days: int,
    *,
    preferred_weekday: int | None = None,
    start_date: date | None = None,
) -> datetime:
    due_at = base + timedelta(days=interval_days)
    if start_date and start_date > due_at.date():
        due_at = datetime.combine(start_date, time(hour=9), tzinfo=base.tzinfo)
    if preferred_weekday is not None:
        due_at += timedelta(days=(preferred_weekday - due_at.weekday()) % 7)
    return due_at
