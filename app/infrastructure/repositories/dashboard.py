from __future__ import annotations

from datetime import timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.application.ports.dashboard import (
    DashboardSnapshot,
    LatestMeasurement,
    RecentEvent,
    UpcomingReminder,
)
from app.core.time import utc_now
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    LivestockModel,
    PlantModel,
    ReminderModel,
    TankModel,
)
from app.infrastructure.repositories.feature_flags import (
    filter_plant_care_events,
    filter_plant_care_reminders,
    plant_care_is_active,
)


class SqlAlchemyDashboardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_snapshot(
        self,
        user_id: int | None,
        reminder_window_days: int = 14,
        plant_care_mode: str = "auto",
    ) -> DashboardSnapshot:
        if user_id is None:
            return DashboardSnapshot(
                tank_count=0,
                event_count=0,
                livestock_count=0,
                plant_count=0,
                recent_events=[],
                upcoming_reminders=[],
                latest_measurements=[],
            )

        include_plant_care = plant_care_is_active(self.session, user_id, plant_care_mode)
        return DashboardSnapshot(
            tank_count=self._count_tanks(user_id),
            event_count=self._count_events(user_id, include_plant_care),
            livestock_count=self._count_livestock(user_id),
            plant_count=self._count_plants(user_id),
            recent_events=self._recent_events(user_id, include_plant_care),
            upcoming_reminders=self._upcoming_reminders(
                user_id,
                reminder_window_days,
                include_plant_care,
            ),
            latest_measurements=self._latest_measurements(user_id),
            plant_care_active=include_plant_care,
        )

    def _scalar_count(self, statement: Select[tuple[int]]) -> int:
        return int(self.session.execute(statement).scalar_one())

    def _count_tanks(self, user_id: int) -> int:
        return self._scalar_count(
            select(func.count()).select_from(TankModel).where(TankModel.user_id == user_id)
        )

    def _count_events(self, user_id: int, include_plant_care: bool) -> int:
        statement = (
            select(func.count()).select_from(EventModel).where(EventModel.user_id == user_id)
        )
        statement = filter_plant_care_events(statement, include_plant_care)
        return self._scalar_count(statement)

    def _count_livestock(self, user_id: int) -> int:
        statement = (
            select(func.coalesce(func.sum(LivestockModel.quantity), 0))
            .select_from(LivestockModel)
            .join(TankModel, TankModel.id == LivestockModel.tank_id)
            .where(TankModel.user_id == user_id, LivestockModel.retired_on.is_(None))
        )
        return self._scalar_count(statement)

    def _count_plants(self, user_id: int) -> int:
        statement = (
            select(func.coalesce(func.sum(func.coalesce(PlantModel.quantity, 1)), 0))
            .select_from(PlantModel)
            .join(TankModel, TankModel.id == PlantModel.tank_id)
            .where(TankModel.user_id == user_id, PlantModel.removed_on.is_(None))
        )
        return self._scalar_count(statement)

    def _recent_events(self, user_id: int, include_plant_care: bool) -> list[RecentEvent]:
        statement = (
            select(EventModel, TankModel.name)
            .outerjoin(TankModel, TankModel.id == EventModel.tank_id)
            .where(EventModel.user_id == user_id)
            .order_by(EventModel.occurred_at.desc())
            .limit(8)
        )
        statement = filter_plant_care_events(statement, include_plant_care)
        rows = self.session.execute(statement).all()
        return [
            RecentEvent(
                id=event.id,
                event_type=event.event_type,
                title=event.title,
                occurred_at=event.occurred_at,
                tank_name=tank_name,
            )
            for event, tank_name in rows
        ]

    def _upcoming_reminders(
        self,
        user_id: int,
        window_days: int,
        include_plant_care: bool,
    ) -> list[UpcomingReminder]:
        soon = utc_now() + timedelta(days=window_days)
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
            .limit(8)
        )
        statement = filter_plant_care_reminders(statement, include_plant_care)
        rows = self.session.execute(statement).all()
        return [
            UpcomingReminder(
                id=reminder.id,
                title=reminder.title,
                due_at=reminder.due_at,
                tank_name=tank_name,
            )
            for reminder, tank_name in rows
        ]

    def _latest_measurements(self, user_id: int) -> list[LatestMeasurement]:
        statement = (
            select(EventMeasurementModel, EventModel.occurred_at, TankModel.name)
            .join(EventModel, EventModel.id == EventMeasurementModel.event_id)
            .outerjoin(TankModel, TankModel.id == EventModel.tank_id)
            .where(EventModel.user_id == user_id)
            .order_by(EventModel.occurred_at.desc())
            .limit(8)
        )
        rows = self.session.execute(statement).all()
        return [
            LatestMeasurement(
                metric_key=measurement.metric_key,
                value=measurement.value,
                unit=measurement.unit,
                occurred_at=occurred_at,
                tank_name=tank_name,
            )
            for measurement, occurred_at, tank_name in rows
        ]
