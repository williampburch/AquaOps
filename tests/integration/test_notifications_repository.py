from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.time import utc_now
from app.infrastructure.db.models import ReminderModel, TankModel, UserModel
from app.infrastructure.repositories.notifications import SqlAlchemyNotificationRepository


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


def test_notification_repository_auto_hides_plant_care_without_plant_signal(
    session: Session,
) -> None:
    now = utc_now()
    user = UserModel(
        email="quiet@example.com",
        username="quiet",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="freshwater")
    session.add_all([user, tank])
    session.flush()

    session.add_all(
        [
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="water_change",
                title="Water change",
                due_at=now,
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="root_tabs",
                title="Root tabs",
                due_at=now + timedelta(days=2),
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="fertilizer",
                title="Weekly fertilizer",
                due_at=now + timedelta(days=3),
            ),
        ]
    )
    session.commit()

    snapshot = SqlAlchemyNotificationRepository(session).get_snapshot(
        user.id,
        plant_care_mode="auto",
    )

    assert snapshot.plant_care_active is False
    assert [item.title for item in snapshot.items] == ["Water change"]


def test_notification_repository_can_force_plant_care_off_for_planted_tank(
    session: Session,
) -> None:
    now = utc_now()
    user = UserModel(
        email="planted@example.com",
        username="planted",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Planted Tank", tank_type="planted")
    session.add_all([user, tank])
    session.flush()

    session.add_all(
        [
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="water_change",
                title="Water change",
                due_at=now,
            ),
            ReminderModel(
                user_id=user.id,
                tank_id=tank.id,
                reminder_type="fertilizer",
                title="Weekly fertilizer",
                due_at=now + timedelta(days=3),
            ),
        ]
    )
    session.commit()

    snapshot = SqlAlchemyNotificationRepository(session).get_snapshot(
        user.id,
        plant_care_mode="off",
    )

    assert snapshot.plant_care_active is False
    assert [item.title for item in snapshot.items] == ["Water change"]


def test_notification_repository_completes_reminder(session: Session) -> None:
    now = utc_now()
    user = UserModel(
        email="complete@example.com",
        username="complete",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="freshwater")
    session.add_all([user, tank])
    session.flush()
    reminder = ReminderModel(
        user_id=user.id,
        tank_id=tank.id,
        reminder_type="water_change",
        title="Water change",
        due_at=now,
    )
    session.add(reminder)
    session.commit()

    repository = SqlAlchemyNotificationRepository(session)

    assert repository.complete_reminder(user.id, reminder.id) is True

    snapshot = repository.get_snapshot(user.id)
    assert snapshot.items == []


def test_notification_repository_snoozes_reminder(session: Session) -> None:
    now = utc_now()
    user = UserModel(
        email="snooze@example.com",
        username="snooze",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="freshwater")
    session.add_all([user, tank])
    session.flush()
    reminder = ReminderModel(
        user_id=user.id,
        tank_id=tank.id,
        reminder_type="feeding",
        title="Feed fish",
        due_at=now,
    )
    session.add(reminder)
    session.commit()

    repository = SqlAlchemyNotificationRepository(session)

    assert repository.snooze_reminder(user.id, reminder.id, 3) is True

    session.refresh(reminder)
    assert reminder.snoozed_until is not None
    assert reminder.due_at == reminder.snoozed_until
    assert reminder.due_at.date() > now.date()
