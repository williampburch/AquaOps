from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    TankModel,
    UserModel,
)


def test_full_migration_chain_reaches_current_head(session: Session) -> None:
    revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "20260715_0009"
    assert session.bind is not None
    assert session.bind.dialect.name == "postgresql"


def test_postgresql_persists_timezone_numeric_and_json_values(session: Session) -> None:
    occurred_at = datetime(2026, 7, 16, 12, 30, tzinfo=UTC)
    user = _user("types")
    tank = TankModel(user=user, name="Type Tank", tank_type="freshwater")
    event = EventModel(
        user=user,
        tank=tank,
        event_type="water_test",
        title="Typed values",
        occurred_at=occurred_at,
        metadata_json={"source": "postgresql", "flags": ["json", "round-trip"]},
    )
    measurement = EventMeasurementModel(
        event=event,
        metric_key="nitrate",
        value=Decimal("12.375"),
        unit="ppm",
    )
    session.add(measurement)
    session.commit()
    session.expire_all()

    stored = session.get(EventMeasurementModel, measurement.id)
    assert stored is not None
    assert stored.value == Decimal("12.375")
    assert stored.event.occurred_at == occurred_at
    assert stored.event.occurred_at.tzinfo is not None
    assert stored.event.metadata_json == {
        "source": "postgresql",
        "flags": ["json", "round-trip"],
    }


def test_constraints_fail_and_session_recovers_after_rollback(session: Session) -> None:
    session.add(_user("unique"))
    session.commit()
    session.add(_user("unique"))

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(TankModel(user_id=999999, name="Missing owner", tank_type="freshwater"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(_user("recovered"))
    session.commit()
    assert session.execute(text("SELECT 1")).scalar_one() == 1


def _user(key: str) -> UserModel:
    return UserModel(
        email=f"{key}@example.com",
        username=key,
        password_hash=hash_password("a-long-test-password"),
    )
