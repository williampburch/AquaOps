from __future__ import annotations

from typing import Optional

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.ports.tanks import ParameterTarget, TankCreate, TankRepository
from app.domain.water import FRESHWATER_BEGINNER_TARGETS, WATER_METRIC_BY_KEY, metric_label


@dataclass(frozen=True)
class TankService:
    repository: TankRepository

    def list_tanks(self, user_id: int):
        return self.repository.list_tanks(user_id)

    def create_tank(self, user_id: int, data: TankCreate) -> int:
        if not data.name.strip():
            raise ValueError("Tank name is required")
        return self.repository.create_tank(user_id, data)

    def get_tank_detail(self, user_id: int, tank_id: int):
        return self.repository.get_tank_detail(user_id, tank_id)

    def update_targets(
        self,
        user_id: int,
        tank_id: int,
        raw_targets: dict[str, Optional[tuple[Decimal], Optional[Decimal], str]],
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
        notes: Optional[str],
    ) -> Optional[int]:
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
