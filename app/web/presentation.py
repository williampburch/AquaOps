from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar

from app.domain.preferences import (
    DEFAULT_PREFERENCES,
    VOLUME_UNIT_LABELS,
    UserPreferences,
    plant_care_enabled,
    volume_from_liters,
)

T = TypeVar("T")
ADVANCED_WATER_METRICS = {"kh", "gh", "tds"}


@dataclass(frozen=True)
class UserDisplay:
    preferences: UserPreferences = DEFAULT_PREFERENCES

    @property
    def volume_unit_label(self) -> str:
        return VOLUME_UNIT_LABELS[self.preferences.volume_unit]

    @property
    def density_class(self) -> str:
        return f"density-{self.preferences.dashboard_density}"

    def format_volume(self, volume_liters: Decimal | None) -> str:
        value = volume_from_liters(volume_liters, self.preferences.volume_unit)
        if value is None:
            return "--"
        return f"{value} {self.volume_unit_label}"

    def format_date(self, value: date | datetime | None, *, include_year: bool = True) -> str:
        if value is None:
            return "--"
        month_name = value.strftime("%b")
        if self.preferences.date_format == "iso":
            return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        if self.preferences.date_format == "dmy":
            return (
                f"{value.day} {month_name} {value.year}"
                if include_year
                else f"{value.day} {month_name}"
            )
        return (
            f"{month_name} {value.day}, {value.year}"
            if include_year
            else f"{month_name} {value.day}"
        )

    def format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "--"
        return f"{self.format_date(value)} at {value.strftime('%-I:%M %p')}"

    def module_enabled(self, module: str, *, feature_needed: bool = False) -> bool:
        return {
            "livestock": self.preferences.enable_livestock,
            "plants": self.preferences.enable_plants,
            "reports": self.preferences.enable_reports,
            "notifications": self.preferences.enable_notifications,
            "advanced_water": self.preferences.enable_advanced_water,
            "plant_care": plant_care_enabled(self.preferences, feature_needed),
        }.get(module, True)

    def visible_water_items(self, items: Iterable[T]) -> list[T]:
        if self.preferences.enable_advanced_water:
            return list(items)
        return [item for item in items if _water_metric_key(item) not in ADVANCED_WATER_METRICS]


def _water_metric_key(item: object) -> str:
    metric_key = getattr(item, "metric_key", None)
    if metric_key is not None:
        return str(metric_key)
    key = getattr(item, "key", None)
    value = getattr(key, "value", None)
    return str(value or key or "")
