from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.ports.care_plans import CareScheduleUpdate
from app.core.security import hash_password
from app.core.time import utc_now
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    EventModel,
    ReminderModel,
    TankMaintenanceConfigModel,
    TankModel,
    UserModel,
)
from app.infrastructure.repositories.care_plans import SqlAlchemyCarePlanRepository
from app.infrastructure.repositories.notifications import SqlAlchemyNotificationRepository


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with testing_session() as db_session:
        yield db_session
    Base.metadata.drop_all(bind=engine)


def test_profile_strategies_preserve_manual_and_legacy_schedules(session: Session) -> None:
    user, tank = _user_and_tank(session)
    legacy_water_change = _config(
        tank,
        "water_change",
        enabled=True,
        interval_days=10,
        provenance="legacy",
    )
    profile_filter = _config(
        tank,
        "filter_cleaning",
        enabled=True,
        interval_days=30,
        provenance="profile",
        profile_key="simple_care",
    )
    manual_custom = _config(
        tank,
        "custom_intake",
        config_type="custom",
        task_label="Rinse intake sponge",
        enabled=True,
        interval_days=21,
        provenance="manual",
    )
    session.add_all([legacy_water_change, profile_filter, manual_custom])
    session.commit()
    repository = SqlAlchemyCarePlanRepository(session)

    assert repository.apply_profile(user.id, tank.id, "high_tech_planted", "merge")
    session.refresh(legacy_water_change)
    session.refresh(manual_custom)
    fertilizer = _schedule(session, tank.id, "fertilizer")
    assert legacy_water_change.enabled
    assert legacy_water_change.interval_days == 10
    assert manual_custom.enabled
    assert fertilizer.enabled
    assert fertilizer.provenance == "profile"

    assert repository.apply_profile(user.id, tank.id, "quarantine", "replace_profile")
    session.refresh(legacy_water_change)
    session.refresh(profile_filter)
    session.refresh(manual_custom)
    session.refresh(fertilizer)
    assert legacy_water_change.enabled
    assert legacy_water_change.interval_days == 10
    assert manual_custom.enabled
    assert profile_filter.enabled
    assert profile_filter.interval_days == 7
    assert not fertilizer.enabled

    assert repository.apply_profile(user.id, tank.id, "simple_care", "start_over")
    session.refresh(legacy_water_change)
    session.refresh(manual_custom)
    assert legacy_water_change.enabled
    assert legacy_water_change.interval_days == 7
    assert legacy_water_change.provenance == "profile"
    assert not manual_custom.enabled
    assert session.get(TankMaintenanceConfigModel, manual_custom.id) is not None


def test_reminder_reconciliation_avoids_duplicates_and_preserves_completed_history(
    session: Session,
) -> None:
    user, tank = _user_and_tank(session)
    config = _config(
        tank,
        "water_change",
        enabled=True,
        interval_days=7,
        provenance="profile",
        profile_key="simple_care",
    )
    completed = ReminderModel(
        user_id=user.id,
        tank_id=tank.id,
        reminder_type="water_change",
        title="Earlier water change",
        due_at=utc_now() - timedelta(days=8),
        completed_at=utc_now() - timedelta(days=7),
    )
    first_open = ReminderModel(
        user_id=user.id,
        tank_id=tank.id,
        reminder_type="water_change",
        title="Water changes due",
        due_at=utc_now() + timedelta(days=1),
    )
    duplicate_open = ReminderModel(
        user_id=user.id,
        tank_id=tank.id,
        reminder_type="water_change",
        title="Duplicate water changes due",
        due_at=utc_now() + timedelta(days=2),
    )
    history_event = EventModel(
        user=user,
        tank=tank,
        event_type="maintenance",
        title="Historical water change",
        occurred_at=utc_now() - timedelta(days=7),
    )
    session.add_all([config, completed, first_open, duplicate_open, history_event])
    session.commit()

    repository = SqlAlchemyCarePlanRepository(session)
    assert repository.apply_profile(user.id, tank.id, "simple_care", "replace_profile")

    open_reminders = list(
        session.scalars(
            select(ReminderModel).where(
                ReminderModel.tank_id == tank.id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
                ReminderModel.reminder_type == "water_change",
            )
        )
    )
    session.refresh(completed)
    session.refresh(duplicate_open)
    assert len(open_reminders) == 1
    assert open_reminders[0].maintenance_config_id == config.id
    assert duplicate_open.superseded_at is not None
    assert completed.completed_at is not None
    assert session.get(EventModel, history_event.id) is not None

    advanced_update = CareScheduleUpdate(
        config_key="water_change",
        config_type="water_change",
        label="Water changes",
        enabled=False,
        interval_days=7,
        schedule_mode="scheduled",
        reminders_enabled=False,
    )
    assert repository.save_advanced_plan(user.id, tank.id, [advanced_update])
    assert not list(
        session.scalars(
            select(ReminderModel).where(
                ReminderModel.tank_id == tank.id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
                ReminderModel.reminder_type == "water_change",
            )
        )
    )
    assert session.get(ReminderModel, completed.id).completed_at is not None


def test_custom_task_completion_schedules_one_next_occurrence_and_enforces_ownership(
    session: Session,
) -> None:
    user, tank = _user_and_tank(session)
    other = UserModel(
        email="other@example.com",
        username="other",
        password_hash=hash_password("a-long-test-password"),
    )
    session.add(other)
    session.commit()
    repository = SqlAlchemyCarePlanRepository(session)
    schedule = CareScheduleUpdate(
        config_key="new_custom",
        config_type="custom",
        label="Inspect backup air pump",
        enabled=True,
        interval_days=30,
        schedule_mode="scheduled",
        reminders_enabled=True,
    )

    assert not repository.add_custom_task(other.id, tank.id, schedule)
    assert repository.add_custom_task(user.id, tank.id, schedule)
    custom = session.scalar(
        select(TankMaintenanceConfigModel).where(
            TankMaintenanceConfigModel.tank_id == tank.id,
            TankMaintenanceConfigModel.config_type == "custom",
        )
    )
    assert custom is not None
    reminder = session.scalar(
        select(ReminderModel).where(
            ReminderModel.maintenance_config_id == custom.id,
            ReminderModel.completed_at.is_(None),
            ReminderModel.superseded_at.is_(None),
        )
    )
    assert reminder is not None

    notification_repository = SqlAlchemyNotificationRepository(session)
    assert notification_repository.complete_reminder(user.id, reminder.id)
    assert not notification_repository.complete_reminder(user.id, reminder.id)
    future = list(
        session.scalars(
            select(ReminderModel).where(
                ReminderModel.maintenance_config_id == custom.id,
                ReminderModel.completed_at.is_(None),
                ReminderModel.superseded_at.is_(None),
            )
        )
    )
    assert len(future) == 1
    assert future[0].due_at > reminder.completed_at


def _user_and_tank(session: Session) -> tuple[UserModel, TankModel]:
    user = UserModel(
        email="care@example.com",
        username="carekeeper",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="planted")
    session.add_all([user, tank])
    session.commit()
    return user, tank


def _config(
    tank: TankModel,
    config_key: str,
    *,
    config_type: str | None = None,
    task_label: str | None = None,
    enabled: bool,
    interval_days: int,
    provenance: str,
    profile_key: str | None = None,
) -> TankMaintenanceConfigModel:
    return TankMaintenanceConfigModel(
        tank=tank,
        config_key=config_key,
        config_type=config_type or config_key,
        task_label=task_label,
        enabled=enabled,
        interval_days=interval_days,
        schedule_mode="scheduled",
        reminders_enabled=enabled,
        provenance=provenance,
        profile_key=profile_key,
    )


def _schedule(session: Session, tank_id: int, config_key: str) -> TankMaintenanceConfigModel:
    schedule = session.scalar(
        select(TankMaintenanceConfigModel).where(
            TankMaintenanceConfigModel.tank_id == tank_id,
            TankMaintenanceConfigModel.config_key == config_key,
        )
    )
    assert schedule is not None
    return schedule
