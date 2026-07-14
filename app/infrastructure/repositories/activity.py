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
    PhotoEventDetailModel,
    ReminderModel,
    TankModel,
)
from app.infrastructure.repositories.feature_flags import (
    filter_plant_care_events,
    filter_plant_care_reminders,
    plant_care_is_active,
)


class SqlAlchemyActivityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent_events(
        self,
        user_id: int,
        limit: int = 50,
        plant_care_mode: str = "auto",
    ) -> list[ActivityEvent]:
        include_plant_care = plant_care_is_active(self.session, user_id, plant_care_mode)
        statement = (
            select(
                EventModel,
                TankModel.name,
                PhotoEventDetailModel.media_asset_id,
                PhotoEventDetailModel.caption,
            )
            .outerjoin(TankModel, TankModel.id == EventModel.tank_id)
            .outerjoin(PhotoEventDetailModel, PhotoEventDetailModel.event_id == EventModel.id)
            .where(EventModel.user_id == user_id)
            .order_by(EventModel.occurred_at.desc())
            .limit(limit)
        )
        statement = filter_plant_care_events(statement, include_plant_care)
        return [
            ActivityEvent(
                id=event.id,
                event_type=event.event_type,
                title=event.title,
                occurred_at=event.occurred_at,
                tank_name=tank_name,
                notes=event.notes,
                media_asset_id=media_asset_id,
                photo_caption=photo_caption,
            )
            for event, tank_name, media_asset_id, photo_caption in self.session.execute(
                statement
            ).all()
        ]

    def get_reports_snapshot(
        self,
        user_id: int,
        plant_care_mode: str = "auto",
    ) -> ReportsSnapshot:
        include_plant_care = plant_care_is_active(self.session, user_id, plant_care_mode)
        tank_count = self._count_tanks(user_id)
        event_count = self._count_events(user_id, include_plant_care=include_plant_care)
        water_tests = self._count_events(user_id, EventType.WATER_TEST.value)
        open_reminders = self._count_open_reminders(user_id, include_plant_care)

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
            event_type_summary=self._event_type_summary(user_id, include_plant_care),
            nitrate_trend=self._nitrate_trend(user_id),
        )

    def _count_tanks(self, user_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(TankModel).where(TankModel.user_id == user_id)
            )
            or 0
        )

    def _count_events(
        self,
        user_id: int,
        event_type: str | None = None,
        include_plant_care: bool = True,
    ) -> int:
        statement = (
            select(func.count()).select_from(EventModel).where(EventModel.user_id == user_id)
        )
        if event_type is not None:
            statement = statement.where(EventModel.event_type == event_type)
        statement = filter_plant_care_events(statement, include_plant_care)
        return int(self.session.scalar(statement) or 0)

    def _count_open_reminders(self, user_id: int, include_plant_care: bool) -> int:
        statement = (
            select(func.count())
            .select_from(ReminderModel)
            .where(ReminderModel.user_id == user_id, ReminderModel.completed_at.is_(None))
        )
        statement = filter_plant_care_reminders(statement, include_plant_care)
        return int(self.session.scalar(statement) or 0)

    def _event_type_summary(
        self,
        user_id: int,
        include_plant_care: bool,
    ) -> list[EventTypeSummary]:
        statement = (
            select(EventModel.event_type, func.count(EventModel.id))
            .where(EventModel.user_id == user_id)
            .group_by(EventModel.event_type)
            .order_by(func.count(EventModel.id).desc())
        )
        statement = filter_plant_care_events(statement, include_plant_care)
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
