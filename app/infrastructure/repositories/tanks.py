from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.ports.tanks import (
    ChartPoint,
    ChartSeries,
    ParameterReading,
    ParameterTarget,
    TankCreate,
    TankDetail,
    TankEvent,
    TankSummary,
)
from app.domain.enums import EventType
from app.domain.water import (
    FRESHWATER_BEGINNER_TARGETS,
    WATER_METRIC_BY_KEY,
    freshwater_targets_for_temperature_unit,
    metric_label,
)
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    TankModel,
    TankParameterTargetModel,
)


class SqlAlchemyTankRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_tanks(self, user_id: int) -> list[TankSummary]:
        statement = (
            select(
                TankModel,
                func.count(EventModel.id).label("event_count"),
                func.max(EventModel.occurred_at).label("latest_event_at"),
            )
            .outerjoin(EventModel, EventModel.tank_id == TankModel.id)
            .where(TankModel.user_id == user_id, TankModel.archived_at.is_(None))
            .group_by(TankModel.id)
            .order_by(TankModel.name.asc())
        )
        rows = self.session.execute(statement).all()
        return [
            TankSummary(
                id=tank.id,
                name=tank.name,
                tank_type=tank.tank_type,
                volume_liters=tank.volume_liters,
                event_count=event_count,
                latest_event_at=latest_event_at,
            )
            for tank, event_count, latest_event_at in rows
        ]

    def create_tank(self, user_id: int, data: TankCreate) -> int:
        tank = TankModel(
            user_id=user_id,
            name=data.name.strip(),
            tank_type=data.tank_type.strip() or "freshwater",
            volume_liters=data.volume_liters,
            started_on=data.started_on,
            description=data.description,
            lighting=data.lighting,
            filtration=data.filtration,
            substrate=data.substrate,
        )
        self.session.add(tank)
        self.session.flush()
        self._seed_default_targets(tank.id, data.temperature_unit)
        self.session.commit()
        return tank.id

    def get_tank_detail(self, user_id: int, tank_id: int) -> TankDetail | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        self._ensure_default_targets(tank.id)
        self.session.commit()
        targets = self._targets_for_tank(tank.id)

        return TankDetail(
            id=tank.id,
            name=tank.name,
            tank_type=tank.tank_type,
            volume_liters=tank.volume_liters,
            started_on=tank.started_on,
            description=tank.description,
            lighting=tank.lighting,
            filtration=tank.filtration,
            substrate=tank.substrate,
            targets=targets,
            latest_readings=self._latest_readings(tank.id, targets),
            chart_series=self._chart_series(tank.id),
            recent_events=self._recent_events(tank.id),
        )

    def update_targets(
        self,
        user_id: int,
        tank_id: int,
        targets: list[ParameterTarget],
    ) -> bool:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return False

        existing = {
            target.metric_key: target
            for target in self.session.scalars(
                select(TankParameterTargetModel).where(TankParameterTargetModel.tank_id == tank_id)
            )
        }
        for target in targets:
            model = existing.get(target.metric_key)
            if model is None:
                model = TankParameterTargetModel(
                    tank_id=tank_id,
                    metric_key=target.metric_key,
                    min_value=target.min_value,
                    max_value=target.max_value,
                    unit=target.unit,
                )
                self.session.add(model)
            else:
                model.min_value = target.min_value
                model.max_value = target.max_value
                model.unit = target.unit

        self.session.commit()
        return True

    def log_water_test(
        self,
        user_id: int,
        tank_id: int,
        occurred_at: datetime,
        measurements: dict[str, Decimal],
        notes: str | None,
    ) -> int | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        event = EventModel(
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.WATER_TEST.value,
            title="Water test",
            notes=notes or "",
            occurred_at=occurred_at,
            metadata_json={},
        )
        self.session.add(event)
        self.session.flush()

        units_by_key = self._target_units_for_tank(tank_id)
        for metric_key, value in measurements.items():
            metric = WATER_METRIC_BY_KEY[metric_key]
            self.session.add(
                EventMeasurementModel(
                    event_id=event.id,
                    metric_key=metric_key,
                    value=value,
                    unit=units_by_key.get(metric_key, metric.default_unit),
                )
            )

        self.session.commit()
        return event.id

    def _get_owned_tank(self, user_id: int, tank_id: int) -> TankModel | None:
        return self.session.execute(
            select(TankModel).where(
                TankModel.id == tank_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
            )
        ).scalar_one_or_none()

    def _seed_default_targets(self, tank_id: int, temperature_unit: str = "F") -> None:
        for target in freshwater_targets_for_temperature_unit(temperature_unit):
            self.session.add(
                TankParameterTargetModel(
                    tank_id=tank_id,
                    metric_key=target.metric_key,
                    min_value=target.min_value,
                    max_value=target.max_value,
                    unit=target.unit,
                )
            )

    def _ensure_default_targets(self, tank_id: int) -> None:
        existing_keys = set(
            self.session.scalars(
                select(TankParameterTargetModel.metric_key).where(
                    TankParameterTargetModel.tank_id == tank_id
                )
            )
        )
        for target in FRESHWATER_BEGINNER_TARGETS:
            if target.metric_key not in existing_keys:
                self.session.add(
                    TankParameterTargetModel(
                        tank_id=tank_id,
                        metric_key=target.metric_key,
                        min_value=target.min_value,
                        max_value=target.max_value,
                        unit=target.unit,
                    )
                )

    def _targets_for_tank(self, tank_id: int) -> list[ParameterTarget]:
        targets_by_key = {
            target.metric_key: target
            for target in self.session.scalars(
                select(TankParameterTargetModel)
                .where(TankParameterTargetModel.tank_id == tank_id)
                .order_by(TankParameterTargetModel.metric_key.asc())
            )
        }
        ordered_targets = []
        for metric_key, metric in WATER_METRIC_BY_KEY.items():
            target = targets_by_key.get(metric_key)
            ordered_targets.append(
                ParameterTarget(
                    metric_key=metric_key,
                    label=metric.label,
                    min_value=target.min_value if target else None,
                    max_value=target.max_value if target else None,
                    unit=target.unit if target else metric.default_unit,
                )
            )
        return ordered_targets

    def _target_units_for_tank(self, tank_id: int) -> dict[str, str]:
        return {
            target.metric_key: target.unit
            for target in self.session.scalars(
                select(TankParameterTargetModel).where(TankParameterTargetModel.tank_id == tank_id)
            )
        }

    def _latest_readings(
        self,
        tank_id: int,
        targets: list[ParameterTarget],
    ) -> list[ParameterReading]:
        target_by_key = {target.metric_key: target for target in targets}
        statement = (
            select(EventMeasurementModel, EventModel.occurred_at)
            .join(EventModel, EventModel.id == EventMeasurementModel.event_id)
            .where(
                EventModel.tank_id == tank_id,
                EventModel.event_type == EventType.WATER_TEST.value,
            )
            .order_by(EventModel.occurred_at.desc(), EventMeasurementModel.metric_key.asc())
        )
        latest_by_metric = {}
        for measurement, occurred_at in self.session.execute(statement).all():
            latest_by_metric.setdefault(measurement.metric_key, (measurement, occurred_at))

        readings = []
        for metric_key in WATER_METRIC_BY_KEY:
            if metric_key not in latest_by_metric:
                continue
            measurement, occurred_at = latest_by_metric[metric_key]
            target = target_by_key.get(metric_key)
            readings.append(
                ParameterReading(
                    metric_key=metric_key,
                    label=metric_label(metric_key),
                    value=measurement.value,
                    unit=measurement.unit,
                    occurred_at=occurred_at,
                    status=_classify_reading(measurement.value, target),
                )
            )
        return readings

    def _chart_series(self, tank_id: int) -> list[ChartSeries]:
        statement = (
            select(EventMeasurementModel, EventModel.occurred_at)
            .join(EventModel, EventModel.id == EventMeasurementModel.event_id)
            .where(
                EventModel.tank_id == tank_id,
                EventModel.event_type == EventType.WATER_TEST.value,
            )
            .order_by(EventModel.occurred_at.asc())
            .limit(240)
        )
        points_by_metric: dict[str, list[ChartPoint]] = defaultdict(list)
        units_by_metric: dict[str, str] = {}
        for measurement, occurred_at in self.session.execute(statement).all():
            points_by_metric[measurement.metric_key].append(
                ChartPoint(
                    occurred_at=occurred_at.strftime("%Y-%m-%d"),
                    value=float(measurement.value),
                )
            )
            units_by_metric[measurement.metric_key] = measurement.unit

        return [
            ChartSeries(
                metric_key=metric_key,
                label=metric_label(metric_key),
                unit=units_by_metric.get(metric_key, WATER_METRIC_BY_KEY[metric_key].default_unit),
                points=points_by_metric[metric_key],
            )
            for metric_key in WATER_METRIC_BY_KEY
            if points_by_metric.get(metric_key)
        ]

    def _recent_events(self, tank_id: int) -> list[TankEvent]:
        statement = (
            select(EventModel)
            .where(EventModel.tank_id == tank_id)
            .order_by(EventModel.occurred_at.desc())
            .limit(12)
        )
        return [
            TankEvent(
                id=event.id,
                event_type=event.event_type,
                title=event.title,
                occurred_at=event.occurred_at,
                notes=event.notes,
            )
            for event in self.session.scalars(statement)
        ]


def _classify_reading(value: Decimal, target: ParameterTarget | None) -> str:
    if target is None:
        return "unknown"
    if target.min_value is not None and value < target.min_value:
        return "low"
    if target.max_value is not None and value > target.max_value:
        return "high"
    return "ok"
