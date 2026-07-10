from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums import EventType
from app.domain.preferences import PLANT_CARE_REMINDER_TYPES
from app.infrastructure.db.models import EventModel, PlantModel, ReminderModel, TankModel


def plant_care_is_active(session: Session, user_id: int, plant_care_mode: str) -> bool:
    if plant_care_mode == "on":
        return True
    if plant_care_mode == "off":
        return False
    return _has_plant_care_signal(session, user_id)


def filter_plant_care_reminders(statement: Select, include_plant_care: bool) -> Select:
    if include_plant_care:
        return statement
    return statement.where(~ReminderModel.reminder_type.in_(PLANT_CARE_REMINDER_TYPES))


def filter_plant_care_events(statement: Select, include_plant_care: bool) -> Select:
    if include_plant_care:
        return statement
    return statement.where(EventModel.event_type != EventType.FERTILIZER.value)


def _has_plant_care_signal(session: Session, user_id: int) -> bool:
    return any(
        (
            _has_active_plants(session, user_id),
            _has_planted_tank(session, user_id),
            _has_fertilizer_history(session, user_id),
        )
    )


def _has_active_plants(session: Session, user_id: int) -> bool:
    count = session.scalar(
        select(func.count())
        .select_from(PlantModel)
        .join(TankModel, TankModel.id == PlantModel.tank_id)
        .where(TankModel.user_id == user_id, PlantModel.removed_on.is_(None))
    )
    return bool(count)


def _has_planted_tank(session: Session, user_id: int) -> bool:
    count = session.scalar(
        select(func.count())
        .select_from(TankModel)
        .where(
            TankModel.user_id == user_id,
            TankModel.archived_at.is_(None),
            func.lower(TankModel.tank_type).like("%plant%"),
        )
    )
    return bool(count)


def _has_fertilizer_history(session: Session, user_id: int) -> bool:
    count = session.scalar(
        select(func.count())
        .select_from(EventModel)
        .where(
            EventModel.user_id == user_id,
            EventModel.event_type == EventType.FERTILIZER.value,
        )
    )
    return bool(count)
