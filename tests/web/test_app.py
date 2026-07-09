from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.main import create_app
from app.web.dependencies import get_db


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    settings = Settings(
        secret_key="test-secret-key-that-is-long-enough",
        database_url="sqlite+pysqlite:///:memory:",
        auto_create_tables=False,
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders_public_empty_state(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "AquaOps" in response.text
    assert "No events yet" in response.text
    assert "Latest Water Parameters" in response.text


def test_register_creates_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "username": "will",
            "email": "will@example.com",
            "password": "a-long-test-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "aquaops_session" in response.cookies


def test_tanks_require_authentication(client: TestClient) -> None:
    response = client.get("/tanks", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_tank_seeds_target_ranges(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/tanks",
        data={
            "name": "Display Tank",
            "tank_type": "planted",
            "volume_liters": "75",
            "started_on": "2026-07-09",
            "description": "Office aquarium",
            "lighting": "LED",
            "filtration": "Canister",
            "substrate": "Aquasoil",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/tanks/1"

    detail = client.get("/tanks/1")
    assert detail.status_code == 200
    assert "Display Tank" in detail.text
    assert "Target Ranges" in detail.text
    assert "Ammonia" in detail.text
    assert "Nitrate" in detail.text


def test_log_water_test_updates_latest_readings_and_charts(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    response = client.post(
        "/tanks/1/water-tests",
        data={
            "occurred_at": "2026-07-09T08:30",
            "ammonia": "0",
            "nitrite": "0",
            "nitrate": "20",
            "ph": "7.4",
            "temperature": "78",
            "kh": "5",
            "gh": "8",
            "tds": "180",
            "notes": "First full test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    detail = client.get("/tanks/1")
    assert "20.000 ppm" in detail.text
    assert "Water Trends" in detail.text
    assert "chartSeries" in detail.text
    assert "First full test" not in detail.text


def test_target_range_status_flags_high_reading(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    client.post(
        "/tanks/1/targets",
        data={
            "ammonia_min": "0",
            "ammonia_max": "0",
            "ammonia_unit": "ppm",
            "nitrite_min": "0",
            "nitrite_max": "0",
            "nitrite_unit": "ppm",
            "nitrate_min": "0",
            "nitrate_max": "10",
            "nitrate_unit": "ppm",
            "ph_min": "6.5",
            "ph_max": "8.0",
            "ph_unit": "pH",
            "temperature_min": "74",
            "temperature_max": "80",
            "temperature_unit": "F",
            "kh_min": "3",
            "kh_max": "8",
            "kh_unit": "dKH",
            "gh_min": "4",
            "gh_max": "12",
            "gh_unit": "dGH",
            "tds_min": "50",
            "tds_max": "400",
            "tds_unit": "ppm",
        },
    )
    client.post(
        "/tanks/1/water-tests",
        data={
            "nitrate": "25",
        },
    )

    detail = client.get("/tanks/1")

    assert "status-high" in detail.text
    assert "25.000 ppm" in detail.text


def _register(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "username": "aquarist",
            "email": "aquarist@example.com",
            "password": "a-long-test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _create_tank(client: TestClient) -> None:
    response = client.post(
        "/tanks",
        data={
            "name": "Display Tank",
            "tank_type": "planted",
            "volume_liters": "75",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
