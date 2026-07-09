from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.notifications import NotificationItem, NotificationSnapshot
from app.core.time import utc_now
from app.infrastructure.db.models import ReminderModel, TankModel


class SqlAlchemyNotificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_snapshot(self, user_id: int) -> NotificationSnapshot:
        now = utc_now()
        soon = now + timedelta(days=14)
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
        )

    def _status(self, due_at, now) -> str:
        if due_at.date() < now.date():
            return "overdue"
        if due_at.date() == now.date():
            return "due_today"
        return "upcoming"
