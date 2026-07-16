from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.notifications import NotificationItem, NotificationSnapshot
from app.core.time import utc_now
from app.domain.care_plans import next_schedule_due_at, quick_log_action, task_label
from app.domain.maintenance import MAINTENANCE_CONFIG_LABELS
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    ReminderModel,
    TankModel,
    TankParameterTargetModel,
)
from app.infrastructure.repositories.feature_flags import (
    filter_plant_care_reminders,
    plant_care_is_active,
)


class SqlAlchemyNotificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_snapshot(
        self,
        user_id: int,
        window_days: int = 14,
        plant_care_mode: str = "auto",
    ) -> NotificationSnapshot:
        now = utc_now()
        soon = now + timedelta(days=window_days)
        include_plant_care = plant_care_is_active(self.session, user_id, plant_care_mode)
        statement = (
            select(ReminderModel, TankModel.name)
            .outerjoin(TankModel, TankModel.id == ReminderModel.tank_id)
            .where(
                ReminderModel.user_id == user_id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
                ReminderModel.due_at <= soon,
            )
            .order_by(ReminderModel.due_at.asc())
            .limit(40)
        )
        statement = filter_plant_care_reminders(statement, include_plant_care)
        items = []
        for reminder, tank_name in self.session.execute(statement).all():
            task_type = self._task_type(reminder)
            action = quick_log_action(task_type)
            if reminder.reminder_type == "water_change_recommendation":
                action = "water_change"
            items.append(
                NotificationItem(
                    id=reminder.id,
                    title=reminder.title,
                    reminder_type=reminder.reminder_type,
                    due_at=reminder.due_at,
                    tank_id=reminder.tank_id,
                    tank_name=tank_name,
                    status=self._status(reminder.due_at, now),
                    reason=self._reason(reminder),
                    quick_log_action=action,
                    maintenance_type=task_type if action == "maintenance" else None,
                )
            )
        return NotificationSnapshot(
            overdue_count=sum(1 for item in items if item.status == "overdue"),
            due_today_count=sum(1 for item in items if item.status == "due_today"),
            upcoming_count=sum(1 for item in items if item.status == "upcoming"),
            items=items,
            plant_care_active=include_plant_care,
        )

    def complete_reminder(self, user_id: int, reminder_id: int) -> bool:
        reminder = self._open_reminder(user_id, reminder_id)
        if reminder is None:
            return False
        reminder.completed_at = utc_now()
        config = reminder.maintenance_config
        if (
            config is not None
            and config.enabled
            and config.schedule_mode == "scheduled"
            and config.reminders_enabled
            and config.interval_days
        ):
            duplicate = self.session.scalar(
                select(ReminderModel).where(
                    ReminderModel.maintenance_config_id == config.id,
                    ReminderModel.id != reminder.id,
                    ReminderModel.completed_at.is_(None),
                    ReminderModel.superseded_at.is_(None),
                )
            )
            if duplicate is None:
                self.session.add(
                    ReminderModel(
                        user_id=reminder.user_id,
                        tank_id=reminder.tank_id,
                        maintenance_config_id=config.id,
                        reminder_type=config.config_key,
                        title=f"{task_label(config.config_type, config.task_label)} due",
                        due_at=next_schedule_due_at(
                            reminder.completed_at,
                            config.interval_days,
                            preferred_weekday=config.preferred_weekday,
                            start_date=config.start_date,
                        ),
                    )
                )
        self.session.commit()
        return True

    def snooze_reminder(self, user_id: int, reminder_id: int, days: int) -> bool:
        reminder = self._open_reminder(user_id, reminder_id)
        if reminder is None:
            return False
        snoozed_until = utc_now() + timedelta(days=days)
        reminder.snoozed_until = snoozed_until
        reminder.due_at = snoozed_until
        self.session.commit()
        return True

    def _open_reminder(self, user_id: int, reminder_id: int) -> ReminderModel | None:
        return self.session.execute(
            select(ReminderModel).where(
                ReminderModel.id == reminder_id,
                ReminderModel.user_id == user_id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
            )
        ).scalar_one_or_none()

    def _status(self, due_at, now) -> str:
        if due_at.date() < now.date():
            return "overdue"
        if due_at.date() == now.date():
            return "due_today"
        return "upcoming"

    def _reason(self, reminder: ReminderModel) -> str | None:
        if reminder.reminder_type == "water_change_recommendation":
            return self._nitrate_reason(reminder)

        config = reminder.maintenance_config
        label = (
            task_label(config.config_type, config.task_label)
            if config is not None
            else MAINTENANCE_CONFIG_LABELS.get(reminder.reminder_type)
        )
        if label is None:
            return None

        event = self._source_event(reminder)
        if event is None:
            return f"Generated from the {label.lower()} schedule."
        return (
            f"Generated from the {label.lower()} schedule after "
            f"{event.title} on {event.occurred_at.date().isoformat()}."
        )

    def _task_type(self, reminder: ReminderModel) -> str:
        if reminder.maintenance_config is not None:
            return reminder.maintenance_config.config_type
        return reminder.reminder_type

    def _nitrate_reason(self, reminder: ReminderModel) -> str | None:
        if reminder.source_event_id is None or reminder.tank_id is None:
            return "Generated after a nitrate reading exceeded this tank's target range."

        nitrate = self.session.execute(
            select(EventMeasurementModel).where(
                EventMeasurementModel.event_id == reminder.source_event_id,
                EventMeasurementModel.metric_key == "nitrate",
            )
        ).scalar_one_or_none()
        target = self.session.execute(
            select(TankParameterTargetModel).where(
                TankParameterTargetModel.tank_id == reminder.tank_id,
                TankParameterTargetModel.metric_key == "nitrate",
            )
        ).scalar_one_or_none()
        if nitrate is None or target is None or target.max_value is None:
            return "Generated after a nitrate reading exceeded this tank's target range."

        return (
            f"Nitrate was {_format_decimal(nitrate.value)} {nitrate.unit}, above "
            f"target max {_format_decimal(target.max_value)} {target.unit}."
        )

    def _source_event(self, reminder: ReminderModel) -> EventModel | None:
        if reminder.source_event_id is None:
            return None
        return self.session.get(EventModel, reminder.source_event_id)


def _format_decimal(value) -> str:
    return format(value.normalize(), "f")
