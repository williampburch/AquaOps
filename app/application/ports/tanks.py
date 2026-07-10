from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class TankCreate:
    name: str
    tank_type: str
    volume_liters: Decimal | None
    started_on: date | None
    description: str | None
    lighting: str | None
    filtration: str | None
    substrate: str | None
    temperature_unit: str = "F"


@dataclass(frozen=True)
class TankSummary:
    id: int
    name: str
    tank_type: str
    volume_liters: Decimal | None
    event_count: int
    latest_event_at: datetime | None


@dataclass(frozen=True)
class ParameterTarget:
    metric_key: str
    label: str
    min_value: Decimal | None
    max_value: Decimal | None
    unit: str


@dataclass(frozen=True)
class ParameterReading:
    metric_key: str
    label: str
    value: Decimal
    unit: str
    occurred_at: datetime
    status: str


@dataclass(frozen=True)
class ChartPoint:
    occurred_at: str
    value: float


@dataclass(frozen=True)
class ChartSeries:
    metric_key: str
    label: str
    unit: str
    points: list[ChartPoint]


@dataclass(frozen=True)
class TankEvent:
    id: int
    event_type: str
    title: str
    occurred_at: datetime
    notes: str | None


@dataclass(frozen=True)
class TankDetail:
    id: int
    name: str
    tank_type: str
    volume_liters: Decimal | None
    started_on: date | None
    description: str | None
    lighting: str | None
    filtration: str | None
    substrate: str | None
    targets: list[ParameterTarget]
    latest_readings: list[ParameterReading]
    chart_series: list[ChartSeries]
    recent_events: list[TankEvent]


class TankRepository(Protocol):
    def list_tanks(self, user_id: int) -> list[TankSummary]:
        """Return all active tanks for the user."""

    def create_tank(self, user_id: int, data: TankCreate) -> int:
        """Create a tank and return its id."""

    def get_tank_detail(self, user_id: int, tank_id: int) -> TankDetail | None:
        """Return full tank details if owned by the user."""

    def update_targets(
        self,
        user_id: int,
        tank_id: int,
        targets: list[ParameterTarget],
    ) -> bool:
        """Persist water parameter targets for a tank."""

    def log_water_test(
        self,
        user_id: int,
        tank_id: int,
        occurred_at: datetime,
        measurements: dict[str, Decimal],
        notes: str | None,
    ) -> int | None:
        """Log a water test as a generic event."""
