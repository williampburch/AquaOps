from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import MeasurementMetric
from app.domain.preferences import fahrenheit_to_celsius


@dataclass(frozen=True)
class WaterMetricDefinition:
    key: MeasurementMetric
    label: str
    default_unit: str
    decimal_places: int


@dataclass(frozen=True)
class WaterTargetPreset:
    metric_key: str
    min_value: Decimal | None
    max_value: Decimal | None
    unit: str


WATER_METRICS: tuple[WaterMetricDefinition, ...] = (
    WaterMetricDefinition(MeasurementMetric.AMMONIA, "Ammonia", "ppm", 2),
    WaterMetricDefinition(MeasurementMetric.NITRITE, "Nitrite", "ppm", 2),
    WaterMetricDefinition(MeasurementMetric.NITRATE, "Nitrate", "ppm", 1),
    WaterMetricDefinition(MeasurementMetric.PH, "pH", "pH", 2),
    WaterMetricDefinition(MeasurementMetric.TEMPERATURE, "Temperature", "F", 1),
    WaterMetricDefinition(MeasurementMetric.KH, "KH", "dKH", 1),
    WaterMetricDefinition(MeasurementMetric.GH, "GH", "dGH", 1),
    WaterMetricDefinition(MeasurementMetric.TDS, "TDS", "ppm", 0),
)


FRESHWATER_BEGINNER_TARGETS: tuple[WaterTargetPreset, ...] = (
    WaterTargetPreset(MeasurementMetric.AMMONIA.value, Decimal("0"), Decimal("0"), "ppm"),
    WaterTargetPreset(MeasurementMetric.NITRITE.value, Decimal("0"), Decimal("0"), "ppm"),
    WaterTargetPreset(MeasurementMetric.NITRATE.value, Decimal("0"), Decimal("40"), "ppm"),
    WaterTargetPreset(MeasurementMetric.PH.value, Decimal("6.5"), Decimal("8.0"), "pH"),
    WaterTargetPreset(MeasurementMetric.TEMPERATURE.value, Decimal("74"), Decimal("80"), "F"),
    WaterTargetPreset(MeasurementMetric.KH.value, Decimal("3"), Decimal("8"), "dKH"),
    WaterTargetPreset(MeasurementMetric.GH.value, Decimal("4"), Decimal("12"), "dGH"),
    WaterTargetPreset(MeasurementMetric.TDS.value, Decimal("50"), Decimal("400"), "ppm"),
)


WATER_METRIC_BY_KEY = {metric.key.value: metric for metric in WATER_METRICS}
FRESHWATER_TARGET_BY_KEY = {target.metric_key: target for target in FRESHWATER_BEGINNER_TARGETS}


def metric_label(metric_key: str) -> str:
    metric = WATER_METRIC_BY_KEY.get(metric_key)
    return metric.label if metric else metric_key.replace("_", " ").title()


def freshwater_targets_for_temperature_unit(temperature_unit: str) -> tuple[WaterTargetPreset, ...]:
    if temperature_unit != "C":
        return FRESHWATER_BEGINNER_TARGETS
    return tuple(
        WaterTargetPreset(
            metric_key=target.metric_key,
            min_value=(
                fahrenheit_to_celsius(target.min_value)
                if target.metric_key == MeasurementMetric.TEMPERATURE.value
                and target.min_value is not None
                else target.min_value
            ),
            max_value=(
                fahrenheit_to_celsius(target.max_value)
                if target.metric_key == MeasurementMetric.TEMPERATURE.value
                and target.max_value is not None
                else target.max_value
            ),
            unit="C" if target.metric_key == MeasurementMetric.TEMPERATURE.value else target.unit,
        )
        for target in FRESHWATER_BEGINNER_TARGETS
    )
