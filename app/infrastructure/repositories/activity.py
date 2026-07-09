from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.ports.activity import (
    ActivityEvent,
    EventTypeSummary,
    NitrateTrendPoint,
    ReportMetric,
    ReportsSnapshot,
)
from app.domain.enums import EventType
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    ReminderModel,
    TankModel,
)


class SqlAlchemyActivityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent_events(self, user_id: int, limit: int = 50) -> list[ActivityEvent]:
        statement = (
            select(EventModel, TankModel.name)
            .outerjoin(TankModel, TankModel.id == EventModel.tank_id)
            .where(EventModel.user_id == user_id)
            .order_by(EventModel.occurred_at.desc())
            .limit(limit)
        )
        return [
            ActivityEvent(
                id=event.id,
                event_type=event.event_type,
                title=event.title,
                occurred_at=event.occurred_at,
                tank_name=tank_name,
                notes=event.notes,
            )
            for event, tank_name in self.session.execute(statement).all()
        ]

    def get_reports_snapshot(self, user_id: int) -> ReportsSnapshot:
        tank_count = self._count_tanks(user_id)
        event_count = self._count_events(user_id)
        water_tests = self._count_events(user_id, EventType.WATER_TEST.value)
        open_reminders = self._count_open_reminders(user_id)

        return ReportsSnapshot(
            metrics=[
                ReportMetric("Active tanks", str(tank_count), "Aquariums currently tracked"),
                ReportMetric("Timeline events", str(event_count), "All logged aquarium activity"),
                ReportMetric(
                    "Water tests",
                    str(water_tests),
                    "Parameter events",
                ),
                ReportMetric("Open reminders", str(open_reminders), "Upcoming care actions"),
            ],
            event_type_summary=self._event_type_summary(user_id),
            nitrate_trend=self._nitrate_trend(user_id),
        )

    def _count_tanks(self, user_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(TankModel).where(TankModel.user_id == user_id)
            )
            or 0
        )

    def _count_events(self, user_id: int, event_type: str | None = None) -> int:
        statement = (
            select(func.count()).select_from(EventModel).where(EventModel.user_id == user_id)
        )
        if event_type is not None:
            statement = statement.where(EventModel.event_type == event_type)
        return int(self.session.scalar(statement) or 0)

    def _count_open_reminders(self, user_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(ReminderModel)
                .where(ReminderModel.user_id == user_id, ReminderModel.completed_at.is_(None))
            )
            or 0
        )

    def _event_type_summary(self, user_id: int) -> list[EventTypeSummary]:
        statement = (
            select(EventModel.event_type, func.count(EventModel.id))
            .where(EventModel.user_id == user_id)
            .group_by(EventModel.event_type)
            .order_by(func.count(EventModel.id).desc())
        )
        return [
            EventTypeSummary(event_type=event_type, count=count)
            for event_type, count in self.session.execute(statement).all()
        ]

    def _nitrate_trend(self, user_id: int) -> list[NitrateTrendPoint]:
        statement = (
            select(EventMeasurementModel, EventModel.occurred_at, TankModel.name)
            .join(EventModel, EventModel.id == EventMeasurementModel.event_id)
            .join(TankModel, TankModel.id == EventModel.tank_id)
            .where(
                EventModel.user_id == user_id,
                EventMeasurementModel.metric_key == "nitrate",
            )
            .order_by(EventModel.occurred_at.asc())
            .limit(160)
        )
        return [
            NitrateTrendPoint(
                occurred_at=occurred_at.strftime("%Y-%m-%d"),
                value=float(measurement.value),
                tank_name=tank_name,
            )
            for measurement, occurred_at, tank_name in self.session.execute(statement).all()
        ]
