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
