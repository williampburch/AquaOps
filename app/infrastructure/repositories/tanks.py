from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from itertools import chain

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.ports.tanks import (
    ChartPoint,
    ChartSeries,
    DoseLog,
    FeedingLog,
    MaintenanceConfig,
    MaintenanceConfigUpdate,
    MaintenanceLog,
    NoteLog,
    ParameterReading,
    ParameterTarget,
    QuickLogContext,
    RecentDose,
    RecentFeeding,
    TankCreate,
    TankDetail,
    TankEvent,
    TankSummary,
)
from app.core.time import utc_now
from app.domain.care_profiles import care_profile
from app.domain.enums import EventType, MaintenanceType
from app.domain.maintenance import (
    MAINTENANCE_CONFIG_DEFAULT_INTERVALS,
    MAINTENANCE_CONFIG_LABELS,
)
from app.domain.water import (
    FRESHWATER_BEGINNER_TARGETS,
    WATER_METRIC_BY_KEY,
    freshwater_targets_for_temperature_unit,
    metric_label,
)
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    FeedingEventDetailModel,
    FertilizerEventDetailModel,
    FertilizerProductModel,
    MaintenanceEventDetailModel,
    ReminderModel,
    TankMaintenanceConfigModel,
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
                care_profile=tank.care_profile,
            )
            for tank, event_count, latest_event_at in rows
        ]

    def create_tank(self, user_id: int, data: TankCreate) -> int:
        profile = care_profile(data.care_profile)
        tank = TankModel(
            user_id=user_id,
            name=data.name.strip(),
            tank_type=data.tank_type.strip() or "freshwater",
            care_profile=profile.key,
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
        self._seed_maintenance_profile(
            user_id,
            tank.id,
            profile.schedule_intervals,
            data.reminders_enabled,
        )
        self.session.commit()
        return tank.id

    def get_tank_detail(self, user_id: int, tank_id: int) -> TankDetail | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        self._ensure_default_targets(tank.id)
        self._ensure_default_maintenance_configs(tank.id)
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
            maintenance_configs=self._maintenance_configs_for_tank(tank.id),
            care_profile=tank.care_profile,
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

    def update_maintenance_configs(
        self,
        user_id: int,
        tank_id: int,
        configs: list[MaintenanceConfigUpdate],
    ) -> bool:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return False

        existing = {
            config.config_type: config
            for config in self.session.scalars(
                select(TankMaintenanceConfigModel).where(
                    TankMaintenanceConfigModel.tank_id == tank_id
                )
            )
        }
        for config in configs:
            model = existing.get(config.config_type)
            if model is None:
                model = TankMaintenanceConfigModel(
                    tank_id=tank_id,
                    config_type=config.config_type,
                    enabled=config.enabled,
                    interval_days=config.interval_days,
                )
                self.session.add(model)
            else:
                model.enabled = config.enabled
                model.interval_days = config.interval_days

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

        self._create_nitrate_recommendation(user_id, tank_id, event.id, measurements)
        self._refresh_scheduled_reminder(
            user_id=user_id,
            tank_id=tank_id,
            source_event_id=event.id,
            config_type="water_test",
            title=MAINTENANCE_CONFIG_LABELS["water_test"],
            occurred_at=occurred_at,
        )
        self.session.commit()
        return event.id

    def get_quick_log_context(self, user_id: int, tank_id: int) -> QuickLogContext | None:
        if self._get_owned_tank(user_id, tank_id) is None:
            return None
        last_water_change_liters = self.session.scalar(
            select(MaintenanceEventDetailModel.volume_changed_liters)
            .join(EventModel, EventModel.id == MaintenanceEventDetailModel.event_id)
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                MaintenanceEventDetailModel.maintenance_type == MaintenanceType.WATER_CHANGE.value,
                MaintenanceEventDetailModel.volume_changed_liters.is_not(None),
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(1)
        )
        water_change_metadata = self.session.scalars(
            select(EventModel.metadata_json)
            .join(
                MaintenanceEventDetailModel,
                MaintenanceEventDetailModel.event_id == EventModel.id,
            )
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                MaintenanceEventDetailModel.maintenance_type == MaintenanceType.WATER_CHANGE.value,
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(20)
        )
        equipment_rows = self.session.scalars(
            select(MaintenanceEventDetailModel.equipment_name)
            .join(EventModel, EventModel.id == MaintenanceEventDetailModel.event_id)
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                MaintenanceEventDetailModel.equipment_name.is_not(None),
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(20)
        )
        recent_equipment = []
        for equipment_name in equipment_rows:
            normalized = (equipment_name or "").strip()
            if normalized and normalized not in recent_equipment:
                recent_equipment.append(normalized)
            if len(recent_equipment) == 5:
                break
        feeding_rows = self.session.execute(
            select(FeedingEventDetailModel, EventModel)
            .join(EventModel, EventModel.id == FeedingEventDetailModel.event_id)
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                FeedingEventDetailModel.food_name != "Skipped",
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(20)
        )
        feedings = list(feeding_rows)
        last_food_names = tuple(_event_food_names(*feedings[0])) if feedings else ()
        last_feeding = (
            RecentFeeding(
                food_name=" + ".join(last_food_names),
                food_names=last_food_names,
                amount=feedings[0][0].amount,
                unit=feedings[0][0].unit,
                target_livestock=feedings[0][0].target_livestock,
            )
            if feedings
            else None
        )
        observation_titles = self.session.scalars(
            select(EventModel.title)
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                EventModel.event_type == EventType.NOTE.value,
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(20)
        )
        dose_rows = list(
            self.session.execute(
                select(FertilizerEventDetailModel, FertilizerProductModel)
                .join(EventModel, EventModel.id == FertilizerEventDetailModel.event_id)
                .join(
                    FertilizerProductModel,
                    FertilizerProductModel.id == FertilizerEventDetailModel.product_id,
                )
                .where(
                    EventModel.user_id == user_id,
                    EventModel.tank_id == tank_id,
                )
                .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
                .limit(20)
            )
        )
        last_dose = (
            RecentDose(
                product_name=dose_rows[0][1].name,
                dose_amount=dose_rows[0][0].dose_amount,
                dose_unit=dose_rows[0][0].dose_unit,
                location=dose_rows[0][0].location,
            )
            if dose_rows
            else None
        )
        available_dose_products = self.session.scalars(
            select(FertilizerProductModel.name)
            .where(FertilizerProductModel.user_id == user_id)
            .order_by(FertilizerProductModel.updated_at.desc())
            .limit(20)
        )
        return QuickLogContext(
            last_water_change_liters=last_water_change_liters,
            recent_conditioner_names=_recent_distinct(
                (metadata or {}).get("conditioner_name") for metadata in water_change_metadata
            ),
            recent_equipment_names=recent_equipment,
            last_feeding=last_feeding,
            recent_food_names=_recent_distinct(
                food_name
                for detail, event in feedings
                for food_name in _event_food_names(detail, event)
            ),
            recent_feeding_units=_recent_distinct(detail.unit for detail, _ in feedings),
            recent_feeding_targets=_recent_distinct(
                detail.target_livestock for detail, _ in feedings
            ),
            recent_observation_titles=_recent_distinct(observation_titles),
            last_dose=last_dose,
            recent_dose_products=_recent_distinct(
                chain(
                    (product.name for _, product in dose_rows),
                    available_dose_products,
                )
            ),
            recent_dose_locations=_recent_distinct(detail.location for detail, _ in dose_rows),
        )

    def log_feeding(self, user_id: int, tank_id: int, data: FeedingLog) -> int | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        food_names = _normalized_food_names(data)
        food_name = " + ".join(food_names) if not data.skipped else "Skipped"
        skip_reason = (data.skip_reason or "").strip()
        event = EventModel(
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.FEEDING.value,
            title=("Skipped feeding" if data.skipped else _truncate_text(f"Fed {food_name}", 180)),
            notes=(data.notes or skip_reason) if data.skipped else (data.notes or ""),
            occurred_at=data.occurred_at,
            metadata_json={
                "skipped": data.skipped,
                "skip_reason": skip_reason or None,
                "food_names": food_names,
            },
        )
        self.session.add(event)
        self.session.flush()
        self.session.add(
            FeedingEventDetailModel(
                event_id=event.id,
                food_name=_truncate_text(food_name, 160),
                amount=data.amount,
                unit=data.unit,
                target_livestock=data.target_livestock,
            )
        )
        self._refresh_scheduled_reminder(
            user_id=user_id,
            tank_id=tank_id,
            source_event_id=event.id,
            config_type="feeding",
            title="Feeding",
            occurred_at=data.occurred_at,
        )
        self.session.commit()
        return event.id

    def log_maintenance(self, user_id: int, tank_id: int, data: MaintenanceLog) -> int | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        metadata = {}
        if data.maintenance_type == MaintenanceType.WATER_CHANGE.value:
            metadata = {
                key: value
                for key, value in {
                    "conditioner_name": (data.conditioner_name or "").strip() or None,
                    "nitrate_before": _decimal_string(data.nitrate_before),
                    "nitrate_after": _decimal_string(data.nitrate_after),
                    "tds_before": _decimal_string(data.tds_before),
                    "tds_after": _decimal_string(data.tds_after),
                }.items()
                if value is not None
            }
        event = EventModel(
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.MAINTENANCE.value,
            title=_maintenance_title(data.maintenance_type),
            notes=data.notes or "",
            occurred_at=data.occurred_at,
            metadata_json=metadata,
        )
        self.session.add(event)
        self.session.flush()
        self.session.add(
            MaintenanceEventDetailModel(
                event_id=event.id,
                maintenance_type=data.maintenance_type,
                duration_minutes=data.duration_minutes,
                volume_changed_liters=data.volume_changed_liters,
                equipment_name=data.equipment_name,
            )
        )
        self._refresh_scheduled_reminder(
            user_id=user_id,
            tank_id=tank_id,
            source_event_id=event.id,
            config_type=data.maintenance_type,
            title=_maintenance_title(data.maintenance_type),
            occurred_at=data.occurred_at,
        )
        self.session.commit()
        return event.id

    def log_note(self, user_id: int, tank_id: int, data: NoteLog) -> int | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        title = data.title.strip() or "Observation"
        event = EventModel(
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.NOTE.value,
            title=title,
            notes=data.notes or "",
            occurred_at=data.occurred_at,
            metadata_json={},
        )
        self.session.add(event)
        self.session.commit()
        return event.id

    def log_dose(self, user_id: int, tank_id: int, data: DoseLog) -> int | None:
        tank = self._get_owned_tank(user_id, tank_id)
        if tank is None:
            return None

        product_name = data.product_name.strip()
        product = self.session.execute(
            select(FertilizerProductModel).where(
                FertilizerProductModel.user_id == user_id,
                func.lower(FertilizerProductModel.name) == product_name.lower(),
            )
        ).scalar_one_or_none()
        if product is None:
            product = FertilizerProductModel(
                user_id=user_id,
                product_key=_custom_product_key(product_name),
                name=product_name,
                default_interval_days=None,
                default_dose_amount=data.dose_amount,
                default_dose_unit=data.dose_unit.strip(),
                is_builtin=False,
            )
            self.session.add(product)
            self.session.flush()
        else:
            product.default_dose_amount = data.dose_amount
            product.default_dose_unit = data.dose_unit.strip()

        event = EventModel(
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.FERTILIZER.value,
            title=f"Dosed {product.name}",
            notes=data.notes or "",
            occurred_at=data.occurred_at,
            metadata_json={},
        )
        self.session.add(event)
        self.session.flush()
        self.session.add(
            FertilizerEventDetailModel(
                event_id=event.id,
                product_id=product.id,
                dose_amount=data.dose_amount,
                dose_unit=data.dose_unit.strip(),
                location=(data.location or "").strip() or None,
                next_due_at=None,
                interval_days_override=None,
            )
        )
        self._refresh_scheduled_reminder(
            user_id=user_id,
            tank_id=tank_id,
            source_event_id=event.id,
            config_type="fertilizer",
            title="Fertilizer",
            occurred_at=data.occurred_at,
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

    def _ensure_default_maintenance_configs(self, tank_id: int) -> None:
        existing_types = set(
            self.session.scalars(
                select(TankMaintenanceConfigModel.config_type).where(
                    TankMaintenanceConfigModel.tank_id == tank_id
                )
            )
        )
        for config_type, interval_days in MAINTENANCE_CONFIG_DEFAULT_INTERVALS.items():
            if config_type not in existing_types:
                self.session.add(
                    TankMaintenanceConfigModel(
                        tank_id=tank_id,
                        config_type=config_type,
                        enabled=False,
                        interval_days=interval_days,
                    )
                )

    def _seed_maintenance_profile(
        self,
        user_id: int,
        tank_id: int,
        schedule_intervals: dict[str, int],
        reminders_enabled: bool,
    ) -> None:
        now = utc_now()
        immediate_types = {"feeding", "fertilizer", "water_test"}
        for config_type, default_interval in MAINTENANCE_CONFIG_DEFAULT_INTERVALS.items():
            enabled = reminders_enabled and config_type in schedule_intervals
            interval_days = schedule_intervals.get(config_type, default_interval)
            self.session.add(
                TankMaintenanceConfigModel(
                    tank_id=tank_id,
                    config_type=config_type,
                    enabled=enabled,
                    interval_days=interval_days,
                )
            )
            if enabled:
                due_at = (
                    now if config_type in immediate_types else now + timedelta(days=interval_days)
                )
                self.session.add(
                    ReminderModel(
                        user_id=user_id,
                        tank_id=tank_id,
                        reminder_type=config_type,
                        title=f"{MAINTENANCE_CONFIG_LABELS[config_type]} due",
                        due_at=due_at,
                    )
                )

    def _maintenance_configs_for_tank(self, tank_id: int) -> list[MaintenanceConfig]:
        configs_by_type = {
            config.config_type: config
            for config in self.session.scalars(
                select(TankMaintenanceConfigModel)
                .where(TankMaintenanceConfigModel.tank_id == tank_id)
                .order_by(TankMaintenanceConfigModel.config_type.asc())
            )
        }
        return [
            MaintenanceConfig(
                config_type=config_type,
                label=label,
                enabled=bool(configs_by_type[config_type].enabled),
                interval_days=configs_by_type[config_type].interval_days,
                last_completed_at=self._last_completed_for_config(tank_id, config_type),
                next_due_at=self._next_due_for_config(tank_id, config_type),
                status=self._maintenance_status(configs_by_type[config_type]),
            )
            for config_type, label in MAINTENANCE_CONFIG_LABELS.items()
            if config_type in configs_by_type
        ]

    def _last_completed_for_config(self, tank_id: int, config_type: str) -> datetime | None:
        if config_type == "feeding":
            return self.session.scalar(
                select(func.max(EventModel.occurred_at)).where(
                    EventModel.tank_id == tank_id,
                    EventModel.event_type == EventType.FEEDING.value,
                )
            )
        if config_type == "fertilizer":
            return self.session.scalar(
                select(func.max(EventModel.occurred_at)).where(
                    EventModel.tank_id == tank_id,
                    EventModel.event_type == EventType.FERTILIZER.value,
                )
            )
        return self.session.scalar(
            select(func.max(EventModel.occurred_at))
            .join(
                MaintenanceEventDetailModel,
                MaintenanceEventDetailModel.event_id == EventModel.id,
            )
            .where(
                EventModel.tank_id == tank_id,
                EventModel.event_type == EventType.MAINTENANCE.value,
                MaintenanceEventDetailModel.maintenance_type == config_type,
            )
        )

    def _next_due_for_config(self, tank_id: int, config_type: str) -> datetime | None:
        return self.session.scalar(
            select(func.min(ReminderModel.due_at)).where(
                ReminderModel.tank_id == tank_id,
                ReminderModel.reminder_type == config_type,
                ReminderModel.completed_at.is_(None),
            )
        )

    def _maintenance_status(self, config: TankMaintenanceConfigModel) -> str:
        if not config.enabled:
            return "off"
        due_at = self._next_due_for_config(config.tank_id, config.config_type)
        if due_at is None:
            return "waiting"
        today = utc_now().date()
        if due_at.date() < today:
            return "overdue"
        if due_at.date() == today:
            return "due_today"
        return "upcoming"

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

    def _refresh_scheduled_reminder(
        self,
        user_id: int,
        tank_id: int,
        source_event_id: int,
        config_type: str,
        title: str,
        occurred_at: datetime,
    ) -> None:
        config = self.session.execute(
            select(TankMaintenanceConfigModel).where(
                TankMaintenanceConfigModel.tank_id == tank_id,
                TankMaintenanceConfigModel.config_type == config_type,
                TankMaintenanceConfigModel.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if config is None or not config.interval_days:
            return

        due_at = occurred_at + timedelta(days=config.interval_days)
        reminder = self._open_reminder(user_id, tank_id, config_type)
        reminder_title = f"{title} due"
        if reminder is None:
            self.session.add(
                ReminderModel(
                    user_id=user_id,
                    tank_id=tank_id,
                    source_event_id=source_event_id,
                    reminder_type=config_type,
                    title=reminder_title,
                    due_at=due_at,
                )
            )
        else:
            reminder.source_event_id = source_event_id
            reminder.title = reminder_title
            reminder.due_at = due_at
            reminder.snoozed_until = None

    def _create_nitrate_recommendation(
        self,
        user_id: int,
        tank_id: int,
        source_event_id: int,
        measurements: dict[str, Decimal],
    ) -> None:
        nitrate = measurements.get("nitrate")
        if nitrate is None:
            return

        target = self.session.execute(
            select(TankParameterTargetModel).where(
                TankParameterTargetModel.tank_id == tank_id,
                TankParameterTargetModel.metric_key == "nitrate",
            )
        ).scalar_one_or_none()
        if target is None or target.max_value is None:
            return

        threshold = target.max_value * Decimal("1.20")
        if nitrate < threshold:
            return

        reminder_type = "water_change_recommendation"
        reminder = self._open_reminder(user_id, tank_id, reminder_type)
        title = (
            f"Water change recommended: nitrate {_format_decimal(nitrate)} "
            f"{target.unit} above {_format_decimal(target.max_value)} {target.unit}"
        )
        due_at = utc_now()
        if reminder is None:
            self.session.add(
                ReminderModel(
                    user_id=user_id,
                    tank_id=tank_id,
                    source_event_id=source_event_id,
                    reminder_type=reminder_type,
                    title=title,
                    due_at=due_at,
                )
            )
        else:
            reminder.source_event_id = source_event_id
            reminder.title = title
            reminder.due_at = due_at
            reminder.snoozed_until = None

    def _open_reminder(
        self,
        user_id: int,
        tank_id: int,
        reminder_type: str,
    ) -> ReminderModel | None:
        return self.session.execute(
            select(ReminderModel).where(
                ReminderModel.user_id == user_id,
                ReminderModel.tank_id == tank_id,
                ReminderModel.reminder_type == reminder_type,
                ReminderModel.completed_at.is_(None),
            )
        ).scalar_one_or_none()


def _classify_reading(value: Decimal, target: ParameterTarget | None) -> str:
    if target is None:
        return "unknown"
    if target.min_value is not None and value < target.min_value:
        return "low"
    if target.max_value is not None and value > target.max_value:
        return "high"
    return "ok"


def _maintenance_title(maintenance_type: str) -> str:
    return maintenance_type.replace("_", " ").title()


def _recent_distinct(values: Iterable[str | None], limit: int = 5) -> list[str]:
    recent = []
    for value in values:
        normalized = (value or "").strip()
        if normalized and normalized not in recent:
            recent.append(normalized)
        if len(recent) == limit:
            break
    return recent


def _normalized_food_names(data: FeedingLog) -> list[str]:
    values = data.food_names if data.food_names else (data.food_name,)
    return _unique_names(values)


def _event_food_names(
    detail: FeedingEventDetailModel,
    event: EventModel,
) -> list[str]:
    metadata_foods = (event.metadata_json or {}).get("food_names", [])
    if isinstance(metadata_foods, list):
        normalized = _unique_names(metadata_foods)
        if normalized:
            return normalized
    return _unique_names((detail.food_name,))


def _unique_names(values: Iterable[object]) -> list[str]:
    names = []
    normalized_names = set()
    for value in values:
        name = str(value).strip()
        normalized = name.casefold()
        if name and normalized not in normalized_names:
            names.append(name)
            normalized_names.add(normalized)
    return names


def _truncate_text(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"


def _custom_product_key(product_name: str) -> str:
    digest = sha256(product_name.casefold().encode()).hexdigest()[:16]
    return f"custom_{digest}"


def _format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _decimal_string(value: Decimal | None) -> str | None:
    return _format_decimal(value) if value is not None else None
