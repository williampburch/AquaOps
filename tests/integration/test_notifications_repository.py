from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.core.time import utc_now
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import ReminderModel, TankModel, UserModel
from app.infrastructure.repositories.notifications import SqlAlchemyNotificationRepository


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db_session:
        yield db_session

    Base.metadata.drop_all(bind=engine)


def test_notification_repository_classifies_open_reminders(session: Session) -> None:
    now = utc_now()
    user = UserModel(
        email="notify@example.com",
        username="notify",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="planted")
    session.add_all([user, tank])
    session.flush()

    session.add_all(
        [
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="water_change",
                title="Water change",
                due_at=now - timedelta(days=1),
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="feeding",
                title="Feed fish",
                due_at=now,
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="root_tabs",
                title="Root tabs",
                due_at=now + timedelta(days=7),
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="filter_cleaning",
                title="Filter cleaning",
                due_at=now + timedelta(days=30),
            ),
        ]
    )
    session.commit()

    snapshot = SqlAlchemyNotificationRepository(session).get_snapshot(user.id)

    assert snapshot.overdue_count == 1
    assert snapshot.due_today_count == 1
    assert snapshot.upcoming_count == 1
    assert [item.title for item in snapshot.items] == [
        "Water change",
        "Feed fish",
        "Root tabs",
    ]
