from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.ports.tanks import (
    DoseLog,
    FeedingLog,
    MaintenanceConfigUpdate,
    MaintenanceLog,
    NoteLog,
    ParameterTarget,
    TankCreate,
    TankRepository,
)
from app.domain.care_profiles import CARE_PROFILES
from app.domain.enums import MaintenanceType
from app.domain.maintenance import MAINTENANCE_CONFIG_LABELS
from app.domain.water import FRESHWATER_BEGINNER_TARGETS, WATER_METRIC_BY_KEY, metric_label


@dataclass(frozen=True)
class TankService:
    repository: TankRepository

    def list_tanks(self, user_id: int):
        return self.repository.list_tanks(user_id)

    def create_tank(self, user_id: int, data: TankCreate) -> int:
        if not data.name.strip():
            raise ValueError("Tank name is required")
        if data.care_profile not in CARE_PROFILES:
            raise ValueError("Choose an available care profile")
        return self.repository.create_tank(user_id, data)

    def get_tank_detail(self, user_id: int, tank_id: int):
        return self.repository.get_tank_detail(user_id, tank_id)

    def get_quick_log_context(self, user_id: int, tank_id: int):
        return self.repository.get_quick_log_context(user_id, tank_id)

    def update_targets(
        self,
        user_id: int,
        tank_id: int,
        raw_targets: dict[str, tuple[Decimal | None, Decimal | None, str]],
    ) -> bool:
        targets = [
            ParameterTarget(
                metric_key=metric_key,
                label=metric_label(metric_key),
                min_value=min_value,
                max_value=max_value,
                unit=unit.strip() or WATER_METRIC_BY_KEY[metric_key].default_unit,
            )
            for metric_key, (min_value, max_value, unit) in raw_targets.items()
            if metric_key in WATER_METRIC_BY_KEY
        ]
        return self.repository.update_targets(user_id, tank_id, targets)

    def log_water_test(
        self,
        user_id: int,
        tank_id: int,
        occurred_at: datetime,
        measurements: dict[str, Decimal],
        notes: str | None,
    ) -> int | None:
        filtered_measurements = {
            metric_key: value
            for metric_key, value in measurements.items()
            if metric_key in WATER_METRIC_BY_KEY
        }
        if not filtered_measurements:
            raise ValueError("At least one water parameter is required")
        return self.repository.log_water_test(
            user_id=user_id,
            tank_id=tank_id,
            occurred_at=occurred_at,
            measurements=filtered_measurements,
            notes=notes,
        )

    def log_feeding(self, user_id: int, tank_id: int, data: FeedingLog) -> int | None:
        has_food = bool(data.food_name.strip()) or any(
            food_name.strip() for food_name in data.food_names
        )
        if not data.skipped and not has_food:
            raise ValueError("Food name is required")
        if any(len(food_name.strip()) > 160 for food_name in (*data.food_names, data.food_name)):
            raise ValueError("Food names must be 160 characters or fewer")
        if data.amount is not None and data.amount < 0:
            raise ValueError("Feeding amount cannot be negative")
        return self.repository.log_feeding(user_id, tank_id, data)

    def log_maintenance(self, user_id: int, tank_id: int, data: MaintenanceLog) -> int | None:
        allowed_types = {maintenance_type.value for maintenance_type in MaintenanceType}
        if data.maintenance_type not in allowed_types:
            raise ValueError("Maintenance type is not supported")
        if data.duration_minutes is not None and data.duration_minutes < 0:
            raise ValueError("Duration cannot be negative")
        if data.volume_changed_liters is not None and data.volume_changed_liters < 0:
            raise ValueError("Water change volume cannot be negative")
        readings = (
            data.nitrate_before,
            data.nitrate_after,
            data.tds_before,
            data.tds_after,
        )
        if any(reading is not None and reading < 0 for reading in readings):
            raise ValueError("Water change readings cannot be negative")
        return self.repository.log_maintenance(user_id, tank_id, data)

    def log_note(self, user_id: int, tank_id: int, data: NoteLog) -> int | None:
        if not data.title.strip() and not (data.notes or "").strip():
            raise ValueError("A note title or body is required")
        return self.repository.log_note(user_id, tank_id, data)

    def log_dose(self, user_id: int, tank_id: int, data: DoseLog) -> int | None:
        if not data.product_name.strip():
            raise ValueError("Fertilizer product is required")
        if data.dose_amount <= 0:
            raise ValueError("Dose amount must be greater than zero")
        if not data.dose_unit.strip():
            raise ValueError("Dose unit is required")
        return self.repository.log_dose(user_id, tank_id, data)

    def update_maintenance_configs(
        self,
        user_id: int,
        tank_id: int,
        configs: list[MaintenanceConfigUpdate],
    ) -> bool:
        allowed_types = set(MAINTENANCE_CONFIG_LABELS)
        normalized = []
        for config in configs:
            if config.config_type not in allowed_types:
                continue
            if config.interval_days is not None and config.interval_days < 1:
                raise ValueError("Maintenance intervals must be at least one day")
            normalized.append(config)
        return self.repository.update_maintenance_configs(user_id, tank_id, normalized)

    def default_targets(self) -> list[ParameterTarget]:
        return [
            ParameterTarget(
                metric_key=target.metric_key,
                label=metric_label(target.metric_key),
                min_value=target.min_value,
                max_value=target.max_value,
                unit=target.unit,
            )
            for target in FRESHWATER_BEGINNER_TARGETS
        ]
