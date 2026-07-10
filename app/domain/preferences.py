from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

US_GALLON_TO_LITER = Decimal("3.785411784")
LITER_TO_US_GALLON = Decimal("0.2641720524")
FAHRENHEIT_TO_CELSIUS_SCALE = Decimal("5") / Decimal("9")


@dataclass(frozen=True)
class UserPreferences:
    unit_system: str = "us"
    volume_unit: str = "gallon"
    temperature_unit: str = "F"
    date_format: str = "mdy"
    dashboard_density: str = "comfortable"
    advanced_mode: bool = False
    reminder_window_days: int = 14
    enable_livestock: bool = True
    enable_plants: bool = True
    enable_reports: bool = True
    enable_notifications: bool = True
    enable_advanced_water: bool = True
    plant_care_mode: str = "auto"


DEFAULT_PREFERENCES = UserPreferences()


VOLUME_UNIT_LABELS = {
    "gallon": "gal",
    "liter": "L",
}

TEMPERATURE_UNIT_LABELS = {
    "F": "F",
    "C": "C",
}

PLANT_CARE_MODES = {"auto", "on", "off"}
PLANT_CARE_REMINDER_TYPES = {"fertilizer", "root_tabs"}


def normalize_preferences(preferences: UserPreferences) -> UserPreferences:
    unit_system = preferences.unit_system if preferences.unit_system in {"us", "metric"} else "us"
    volume_unit = (
        preferences.volume_unit if preferences.volume_unit in VOLUME_UNIT_LABELS else "gallon"
    )
    temperature_unit = (
        preferences.temperature_unit
        if preferences.temperature_unit in TEMPERATURE_UNIT_LABELS
        else "F"
    )
    date_format = (
        preferences.date_format if preferences.date_format in {"mdy", "dmy", "iso"} else "mdy"
    )
    dashboard_density = (
        preferences.dashboard_density
        if preferences.dashboard_density in {"comfortable", "compact"}
        else "comfortable"
    )
    reminder_window_days = min(max(preferences.reminder_window_days, 1), 60)
    plant_care_mode = (
        preferences.plant_care_mode if preferences.plant_care_mode in PLANT_CARE_MODES else "auto"
    )
    return UserPreferences(
        unit_system=unit_system,
        volume_unit=volume_unit,
        temperature_unit=temperature_unit,
        date_format=date_format,
        dashboard_density=dashboard_density,
        advanced_mode=preferences.advanced_mode,
        reminder_window_days=reminder_window_days,
        enable_livestock=preferences.enable_livestock,
        enable_plants=preferences.enable_plants,
        enable_reports=preferences.enable_reports,
        enable_notifications=preferences.enable_notifications,
        enable_advanced_water=preferences.enable_advanced_water,
        plant_care_mode=plant_care_mode,
    )


def plant_care_enabled(preferences: UserPreferences, feature_needed: bool = False) -> bool:
    if not preferences.enable_plants:
        return False
    if preferences.plant_care_mode == "on":
        return True
    if preferences.plant_care_mode == "off":
        return False
    return feature_needed


def volume_to_liters(value: Decimal | None, volume_unit: str) -> Decimal | None:
    if value is None:
        return None
    if volume_unit == "gallon":
        return (value * US_GALLON_TO_LITER).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def volume_from_liters(value: Decimal | None, volume_unit: str) -> Decimal | None:
    if value is None:
        return None
    if volume_unit == "gallon":
        return (value * LITER_TO_US_GALLON).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def fahrenheit_to_celsius(value: Decimal) -> Decimal:
    return ((value - Decimal("32")) * FAHRENHEIT_TO_CELSIUS_SCALE).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
