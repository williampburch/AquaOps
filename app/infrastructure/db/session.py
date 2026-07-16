from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return None
    return Path(raw_path)


def create_database_engine(
    database_url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 2,
    pool_timeout: int = 10,
    connect_timeout: int = 5,
) -> Engine:
    sqlite_path = _sqlite_path(database_url)
    connect_args: dict[str, object] = {}
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args["check_same_thread"] = False
    elif database_url.startswith("postgresql+"):
        connect_args["connect_timeout"] = connect_timeout
        engine_options.update(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
        )
    return create_engine(database_url, connect_args=connect_args, **engine_options)


settings = get_settings()
engine = create_database_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout_seconds,
    connect_timeout=settings.database_connect_timeout_seconds,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session]:
    with SessionLocal() as session:
        try:
            yield session
        except BaseException:
            session.rollback()
            raise
