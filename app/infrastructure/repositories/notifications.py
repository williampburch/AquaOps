from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.notifications import NotificationItem, NotificationSnapshot
from app.core.time import utc_now
from app.infrastructure.db.models import ReminderModel, TankModel
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
                ReminderModel.due_at <= soon,
            )
            .order_by(ReminderModel.due_at.asc())
            .limit(40)
        )
        statement = filter_plant_care_reminders(statement, include_plant_care)
        items = [
            NotificationItem(
                id=reminder.id,
                title=reminder.title,
                reminder_type=reminder.reminder_type,
                due_at=reminder.due_at,
                tank_name=tank_name,
                status=self._status(reminder.due_at, now),
            )
            for reminder, tank_name in self.session.execute(statement).all()
        ]
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
            )
        ).scalar_one_or_none()

    def _status(self, due_at, now) -> str:
        if due_at.date() < now.date():
            return "overdue"
        if due_at.date() == now.date():
            return "due_today"
        return "upcoming"
