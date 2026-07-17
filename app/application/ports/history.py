from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class HistoryMeasurement:
    metric_key: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class CareHistoryEvent:
    id: int
    event_type: str
    title: str
    occurred_at: datetime
    notes: str | None
    metadata: dict[str, object]
    measurements: tuple[HistoryMeasurement, ...] = ()
    maintenance_type: str | None = None
    duration_minutes: int | None = None
    volume_changed_liters: Decimal | None = None
    equipment_name: str | None = None
    feeding_food_name: str | None = None
    feeding_amount: Decimal | None = None
    feeding_unit: str | None = None
    feeding_target: str | None = None
    dose_product_name: str | None = None
    dose_amount: Decimal | None = None
    dose_unit: str | None = None
    dose_location: str | None = None
    media_asset_id: int | None = None
    photo_caption: str | None = None


@dataclass(frozen=True)
class CareHistoryPage:
    tank_id: int
    tank_name: str
    events: list[CareHistoryEvent]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class CareHistoryReadRepository(Protocol):
    def list_tank_history(
        self,
        user_id: int,
        tank_id: int,
        *,
        event_types: tuple[str, ...] | None,
        maintenance_type: str | None,
        page: int,
        page_size: int,
        plant_care_mode: str,
    ) -> CareHistoryPage | None:
        """Return a page of structured history for one owned tank."""
