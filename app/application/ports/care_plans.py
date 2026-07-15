from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class CareSchedule:
    id: int
    config_key: str
    config_type: str
    label: str
    enabled: bool
    interval_days: int | None
    schedule_mode: str
    preferred_weekday: int | None
    start_date: date | None
    reminders_enabled: bool
    notes: str | None
    provenance: str
    profile_key: str | None
    next_due_at: datetime | None


@dataclass(frozen=True)
class CarePlan:
    tank_id: int
    tank_name: str
    care_profile: str
    schedules: list[CareSchedule]


@dataclass(frozen=True)
class CareScheduleUpdate:
    config_key: str
    config_type: str
    label: str | None
    enabled: bool
    interval_days: int | None
    schedule_mode: str = "scheduled"
    preferred_weekday: int | None = None
    start_date: date | None = None
    reminders_enabled: bool = True
    notes: str | None = None


class CarePlanRepository(Protocol):
    def get_care_plan(self, user_id: int, tank_id: int) -> CarePlan | None: ...

    def apply_profile(
        self,
        user_id: int,
        tank_id: int,
        profile_key: str,
        strategy: str,
    ) -> bool: ...

    def save_advanced_plan(
        self,
        user_id: int,
        tank_id: int,
        schedules: list[CareScheduleUpdate],
    ) -> bool: ...

    def add_custom_task(
        self,
        user_id: int,
        tank_id: int,
        schedule: CareScheduleUpdate,
    ) -> bool: ...
