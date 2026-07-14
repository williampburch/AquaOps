from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ActivityEvent:
    id: int
    event_type: str
    title: str
    occurred_at: datetime
    tank_name: str | None
    notes: str | None
    media_asset_id: int | None = None
    photo_caption: str | None = None


@dataclass(frozen=True)
class EventTypeSummary:
    event_type: str
    count: int


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: str
    detail: str


@dataclass(frozen=True)
class NitrateTrendPoint:
    occurred_at: str
    value: float
    tank_name: str


@dataclass(frozen=True)
class ReportsSnapshot:
    metrics: list[ReportMetric]
    event_type_summary: list[EventTypeSummary]
    nitrate_trend: list[NitrateTrendPoint]


class ActivityReadRepository(Protocol):
    def list_recent_events(
        self,
        user_id: int,
        limit: int = 50,
        plant_care_mode: str = "auto",
    ) -> list[ActivityEvent]:
        """Return recent timeline events for a user."""

    def get_reports_snapshot(
        self,
        user_id: int,
        plant_care_mode: str = "auto",
    ) -> ReportsSnapshot:
        """Return report summary data for a user."""
