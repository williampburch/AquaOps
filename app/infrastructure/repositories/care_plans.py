from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.care_plans import CarePlan, CareSchedule, CareScheduleUpdate
from app.core.time import utc_now
from app.domain.care_plans import CARE_TASKS, next_schedule_due_at, task_label
from app.domain.care_profiles import care_profile
from app.infrastructure.db.models import ReminderModel, TankMaintenanceConfigModel, TankModel


class SqlAlchemyCarePlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_care_plan(self, user_id: int, tank_id: int) -> CarePlan | None:
        tank = self._owned_tank(user_id, tank_id)
        if tank is None:
            return None
        self._ensure_standard_schedules(tank.id)
        self.session.commit()
        schedules = list(
            self.session.scalars(
                select(TankMaintenanceConfigModel)
                .where(TankMaintenanceConfigModel.tank_id == tank.id)
                .order_by(TankMaintenanceConfigModel.created_at, TankMaintenanceConfigModel.id)
            )
        )
        order = {key: index for index, key in enumerate(CARE_TASKS)}
        schedules.sort(key=lambda item: (order.get(item.config_key, 10_000), item.id))
        return CarePlan(
            tank_id=tank.id,
            tank_name=tank.name,
            care_profile=tank.care_profile,
            schedules=[self._care_schedule(schedule) for schedule in schedules],
        )

    def apply_profile(
        self,
        user_id: int,
        tank_id: int,
        profile_key: str,
        strategy: str,
    ) -> bool:
        tank = self._owned_tank(user_id, tank_id)
        if tank is None:
            return False
        profile = care_profile(profile_key)
        self._ensure_standard_schedules(tank.id)
        configs = self._configs(tank.id)
        changed_keys: set[str] = set()

        if strategy == "start_over":
            for config in configs.values():
                if config.enabled:
                    changed_keys.add(config.config_key)
                config.enabled = False
                config.reminders_enabled = False

        if strategy in {"replace_profile", "start_over"}:
            for config in configs.values():
                if strategy == "replace_profile" and config.provenance != "profile":
                    continue
                if config.config_key not in profile.schedule_intervals:
                    if config.enabled:
                        changed_keys.add(config.config_key)
                    config.enabled = False
                    config.reminders_enabled = False

        for config_key, interval_days in profile.schedule_intervals.items():
            config = configs.get(config_key)
            if config is None:
                config = self._new_standard_config(tank.id, config_key)
                self.session.add(config)
                configs[config_key] = config
            if strategy == "merge" and config.provenance != "system":
                continue
            if strategy == "replace_profile" and config.provenance in {"manual", "legacy"}:
                continue
            config.enabled = True
            config.interval_days = interval_days
            config.schedule_mode = "scheduled"
            config.reminders_enabled = True
            config.provenance = "profile"
            config.profile_key = profile.key
            changed_keys.add(config_key)

        tank.care_profile = profile.key
        self.session.flush()
        self._reconcile_reminders(user_id, tank.id, changed_keys)
        self.session.commit()
        return True

    def save_advanced_plan(
        self,
        user_id: int,
        tank_id: int,
        schedules: list[CareScheduleUpdate],
    ) -> bool:
        tank = self._owned_tank(user_id, tank_id)
        if tank is None:
            return False
        self._ensure_standard_schedules(tank.id)
        configs = self._configs(tank.id)
        changed_keys: set[str] = set()
        for update in schedules:
            config = configs.get(update.config_key)
            if config is None or config.config_type != update.config_type:
                continue
            before = self._config_values(config)
            self._apply_update(config, update)
            if before != self._config_values(config):
                changed_keys.add(config.config_key)
        tank.care_profile = "advanced_custom"
        self.session.flush()
        self._reconcile_reminders(user_id, tank.id, changed_keys)
        self.session.commit()
        return True

    def add_custom_task(
        self,
        user_id: int,
        tank_id: int,
        schedule: CareScheduleUpdate,
    ) -> bool:
        tank = self._owned_tank(user_id, tank_id)
        if tank is None:
            return False
        config = TankMaintenanceConfigModel(
            tank_id=tank.id,
            config_key=f"custom_{uuid4().hex}",
            config_type="custom",
            task_label=(schedule.label or "").strip(),
            enabled=schedule.enabled,
            interval_days=schedule.interval_days,
            schedule_mode=schedule.schedule_mode,
            preferred_weekday=schedule.preferred_weekday,
            start_date=schedule.start_date,
            reminders_enabled=(
                schedule.reminders_enabled and schedule.schedule_mode == "scheduled"
            ),
            notes=(schedule.notes or "").strip() or None,
            provenance="manual",
            profile_key=None,
        )
        self.session.add(config)
        tank.care_profile = "advanced_custom"
        self.session.flush()
        self._reconcile_reminders(user_id, tank.id, {config.config_key})
        self.session.commit()
        return True

    def _ensure_standard_schedules(self, tank_id: int) -> None:
        existing = set(
            self.session.scalars(
                select(TankMaintenanceConfigModel.config_key).where(
                    TankMaintenanceConfigModel.tank_id == tank_id
                )
            )
        )
        for config_key in CARE_TASKS:
            if config_key not in existing:
                self.session.add(self._new_standard_config(tank_id, config_key))

    def _new_standard_config(
        self,
        tank_id: int,
        config_key: str,
    ) -> TankMaintenanceConfigModel:
        task = CARE_TASKS[config_key]
        return TankMaintenanceConfigModel(
            tank_id=tank_id,
            config_key=config_key,
            config_type=config_key,
            task_label=None,
            enabled=False,
            interval_days=task.default_interval_days,
            schedule_mode="scheduled",
            preferred_weekday=None,
            start_date=None,
            reminders_enabled=False,
            notes=None,
            provenance="system",
            profile_key=None,
        )

    def _configs(self, tank_id: int) -> dict[str, TankMaintenanceConfigModel]:
        self.session.flush()
        return {
            config.config_key: config
            for config in self.session.scalars(
                select(TankMaintenanceConfigModel).where(
                    TankMaintenanceConfigModel.tank_id == tank_id
                )
            )
        }

    def _reconcile_reminders(
        self,
        user_id: int,
        tank_id: int,
        changed_keys: set[str],
    ) -> None:
        now = utc_now()
        configs = self._configs(tank_id)
        open_reminders = list(
            self.session.scalars(
                select(ReminderModel)
                .where(
                    ReminderModel.user_id == user_id,
                    ReminderModel.tank_id == tank_id,
                    ReminderModel.completed_at.is_(None),
                    ReminderModel.superseded_at.is_(None),
                )
                .order_by(ReminderModel.created_at, ReminderModel.id)
            )
        )
        for config in configs.values():
            matches = [
                reminder
                for reminder in open_reminders
                if reminder.maintenance_config_id == config.id
                or (
                    reminder.maintenance_config_id is None
                    and reminder.reminder_type == config.config_key
                )
            ]
            scheduled = (
                config.enabled
                and config.schedule_mode == "scheduled"
                and config.reminders_enabled
                and bool(config.interval_days)
            )
            if not scheduled:
                for reminder in matches:
                    self._supersede(reminder, "Care plan schedule disabled or changed", now)
                continue

            reminder = matches[0] if matches else None
            if reminder is None:
                reminder = ReminderModel(
                    user_id=user_id,
                    tank_id=tank_id,
                    maintenance_config_id=config.id,
                    reminder_type=config.config_key,
                    title=f"{task_label(config.config_type, config.task_label)} due",
                    due_at=next_schedule_due_at(
                        now,
                        config.interval_days or 1,
                        preferred_weekday=config.preferred_weekday,
                        start_date=config.start_date,
                    ),
                )
                self.session.add(reminder)
            else:
                reminder.maintenance_config_id = config.id
                reminder.reminder_type = config.config_key
                reminder.title = f"{task_label(config.config_type, config.task_label)} due"
                reminder.snoozed_until = None
                if config.config_key in changed_keys:
                    reminder.due_at = next_schedule_due_at(
                        now,
                        config.interval_days or 1,
                        preferred_weekday=config.preferred_weekday,
                        start_date=config.start_date,
                    )
            for duplicate in matches[1:]:
                self._supersede(duplicate, "Duplicate replaced by care plan editor", now)

    @staticmethod
    def _supersede(reminder: ReminderModel, reason: str, now) -> None:
        reminder.superseded_at = now
        reminder.superseded_reason = reason

    @staticmethod
    def _apply_update(
        config: TankMaintenanceConfigModel,
        update: CareScheduleUpdate,
    ) -> None:
        config.task_label = (update.label or "").strip() or None
        config.enabled = update.enabled
        config.interval_days = update.interval_days
        config.schedule_mode = update.schedule_mode
        config.preferred_weekday = update.preferred_weekday
        config.start_date = update.start_date
        config.reminders_enabled = update.reminders_enabled and update.schedule_mode == "scheduled"
        config.notes = (update.notes or "").strip() or None
        config.provenance = "manual"
        config.profile_key = None

    @staticmethod
    def _config_values(config: TankMaintenanceConfigModel) -> tuple:
        return (
            config.task_label,
            config.enabled,
            config.interval_days,
            config.schedule_mode,
            config.preferred_weekday,
            config.start_date,
            config.reminders_enabled,
            config.notes,
        )

    def _care_schedule(self, config: TankMaintenanceConfigModel) -> CareSchedule:
        next_due = self.session.scalar(
            select(ReminderModel.due_at)
            .where(
                ReminderModel.maintenance_config_id == config.id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
            )
            .order_by(ReminderModel.due_at)
            .limit(1)
        )
        return CareSchedule(
            id=config.id,
            config_key=config.config_key,
            config_type=config.config_type,
            label=task_label(config.config_type, config.task_label),
            enabled=config.enabled,
            interval_days=config.interval_days,
            schedule_mode=config.schedule_mode,
            preferred_weekday=config.preferred_weekday,
            start_date=config.start_date,
            reminders_enabled=config.reminders_enabled,
            notes=config.notes,
            provenance=config.provenance,
            profile_key=config.profile_key,
            next_due_at=next_due,
        )

    def _owned_tank(self, user_id: int, tank_id: int) -> TankModel | None:
        return self.session.scalar(
            select(TankModel).where(
                TankModel.id == tank_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
            )
        )
