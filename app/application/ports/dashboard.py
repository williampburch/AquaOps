from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class RecentEvent:
    id: int
    event_type: str
    title: str
    occurred_at: datetime
    tank_name: str | None


@dataclass(frozen=True)
class UpcomingReminder:
    id: int
    title: str
    due_at: datetime
    tank_name: str | None


@dataclass(frozen=True)
class LatestMeasurement:
    metric_key: str
    value: Decimal
    unit: str
    occurred_at: datetime
    tank_name: str | None


@dataclass(frozen=True)
class DashboardSnapshot:
    tank_count: int
    event_count: int
    livestock_count: int
    plant_count: int
    recent_events: list[RecentEvent]
    upcoming_reminders: list[UpcomingReminder]
    latest_measurements: list[LatestMeasurement]


class DashboardReadRepository(Protocol):
    def get_snapshot(self, user_id: int | None) -> DashboardSnapshot:
        """Return a dashboard snapshot for a user or an empty public snapshot."""
