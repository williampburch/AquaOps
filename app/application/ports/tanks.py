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
class FeedingLog:
    occurred_at: datetime
    food_name: str
    amount: Decimal | None = None
    unit: str | None = None
    target_livestock: str | None = None
    notes: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


@dataclass(frozen=True)
class MaintenanceLog:
    occurred_at: datetime
    maintenance_type: str
    duration_minutes: int | None = None
    volume_changed_liters: Decimal | None = None
    equipment_name: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class NoteLog:
    occurred_at: datetime
    title: str
    notes: str | None = None


@dataclass(frozen=True)
class DoseLog:
    occurred_at: datetime
    product_name: str
    dose_amount: Decimal
    dose_unit: str
    location: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class MaintenanceConfig:
    config_type: str
    label: str
    enabled: bool
    interval_days: int | None
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None
    status: str = "off"


@dataclass(frozen=True)
class MaintenanceConfigUpdate:
    config_type: str
    enabled: bool
    interval_days: int | None


@dataclass(frozen=True)
class RecentFeeding:
    food_name: str
    amount: Decimal | None
    unit: str | None
    target_livestock: str | None


@dataclass(frozen=True)
class RecentDose:
    product_name: str
    dose_amount: Decimal
    dose_unit: str
    location: str | None


@dataclass(frozen=True)
class QuickLogContext:
    last_water_change_liters: Decimal | None
    recent_equipment_names: list[str]
    last_feeding: RecentFeeding | None
    recent_food_names: list[str]
    recent_feeding_targets: list[str]
    recent_observation_titles: list[str]
    last_dose: RecentDose | None
    recent_dose_products: list[str]
    recent_dose_locations: list[str]


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
    maintenance_configs: list[MaintenanceConfig]


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

    def log_feeding(self, user_id: int, tank_id: int, data: FeedingLog) -> int | None:
        """Log a feeding as a generic event with feeding details."""

    def log_maintenance(self, user_id: int, tank_id: int, data: MaintenanceLog) -> int | None:
        """Log maintenance as a generic event with maintenance details."""

    def log_note(self, user_id: int, tank_id: int, data: NoteLog) -> int | None:
        """Log a note or observation as a generic event."""

    def log_dose(self, user_id: int, tank_id: int, data: DoseLog) -> int | None:
        """Log a fertilizer dose with a reusable user-owned product."""

    def update_maintenance_configs(
        self,
        user_id: int,
        tank_id: int,
        configs: list[MaintenanceConfigUpdate],
    ) -> bool:
        """Persist recurring maintenance configs for a tank."""

    def get_quick_log_context(self, user_id: int, tank_id: int) -> QuickLogContext | None:
        """Return recent values that can accelerate safe quick logging."""
