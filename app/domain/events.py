from __future__ import annotations

from typing import Optional

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, MeasurementMetric


@dataclass(frozen=True)
class WaterMeasurement:
    metric: MeasurementMetric
    value: Decimal
    unit: str


@dataclass(frozen=True)
class EventDraft:
    user_id: int
    event_type: EventType
    occurred_at: datetime
    title: str
    tank_id: Optional[int] = None
    notes: Optional[str] = None
