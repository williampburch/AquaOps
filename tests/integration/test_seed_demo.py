from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import verify_password
from app.demo.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_data
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    LivestockModel,
    PlantModel,
    ReminderModel,
    TankModel,
    UserModel,
)


def test_seed_demo_creates_realistic_demo_account(session: Session) -> None:
    settings = Settings(
        secret_key="test-secret-key-that-is-long-enough",
        app_env="development",
    )

    result = seed_demo_data(session, settings)

    assert result.email == DEMO_EMAIL
    assert result.password == DEMO_PASSWORD
    assert result.tank_count == 3
    assert result.event_count > 200
    assert result.reminder_count == 9

    user = session.scalar(select(UserModel).where(UserModel.email == DEMO_EMAIL))
    assert user is not None
    assert verify_password(DEMO_PASSWORD, user.password_hash)
    assert _count(session, TankModel) == 3
    assert _count(session, EventModel) > 200
    assert _count(session, EventMeasurementModel) > 240
    assert _count(session, LivestockModel) >= 7
    assert _count(session, PlantModel) >= 8
    assert _count(session, ReminderModel) == 9


def test_seed_demo_is_idempotent(session: Session) -> None:
    settings = Settings(
        secret_key="test-secret-key-that-is-long-enough",
        app_env="development",
    )

    first = seed_demo_data(session, settings)
    second = seed_demo_data(session, settings)

    assert second == first
    assert _count(session, UserModel) == 1
    assert _count(session, TankModel) == 3
    assert _count(session, ReminderModel) == 9


def test_seed_demo_refuses_production_without_override(session: Session) -> None:
    settings = Settings(
        secret_key="test-secret-key-that-is-long-enough",
        app_env="production",
    )

    with pytest.raises(RuntimeError, match="APP_ENV=production"):
        seed_demo_data(session, settings)


def _count(session: Session, model: type[Base]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
