from __future__ import annotations

from collections.abc import Generator

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.db import session as db_session_module
from app.infrastructure.db.session import create_database_engine, get_session


def test_postgresql_engine_uses_conservative_queue_pool() -> None:
    engine = create_database_engine(
        "postgresql+psycopg://aquaops:password@localhost:5432/aquaops",
        pool_size=3,
        max_overflow=1,
        pool_timeout=7,
        connect_timeout=4,
    )

    assert engine.dialect.name == "postgresql"
    assert engine.pool.size() == 3
    assert engine.pool.timeout() == 7
    assert engine.pool._max_overflow == 1
    engine.dispose()


@pytest.mark.parametrize(
    ("auto_create_tables", "database_url"),
    [
        (True, "postgresql+psycopg://aquaops:password@db:5432/aquaops"),
        (False, "sqlite:///./data/aquaops.db"),
    ],
)
def test_production_rejects_unsafe_database_settings(
    auto_create_tables: bool,
    database_url: str,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            auto_create_tables=auto_create_tables,
            database_url=database_url,
        )


def test_request_session_rolls_back_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(db_session_module, "SessionLocal", lambda: fake_session)

    generator: Generator = get_session()
    assert next(generator) is fake_session
    with pytest.raises(RuntimeError, match="statement failed"):
        generator.throw(RuntimeError("statement failed"))

    assert fake_session.rollback_called
    assert fake_session.exited


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_called = False
        self.exited = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.exited = True

    def rollback(self) -> None:
        self.rollback_called = True
