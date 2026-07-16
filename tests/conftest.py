from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.infrastructure.db.session import create_database_engine


@pytest.fixture(scope="session")
def postgres_engine() -> Generator[Engine]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration and web tests")
    if not database_url.startswith("postgresql+"):
        pytest.fail("TEST_DATABASE_URL must use a PostgreSQL SQLAlchemy dialect")

    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        alembic_config = Config("alembic.ini")
        alembic_config.attributes["connection"] = connection
        command.upgrade(alembic_config, "head")

    assert "alembic_version" in inspect(engine).get_table_names()
    yield engine
    engine.dispose()


@pytest.fixture
def clean_database(postgres_engine: Engine) -> Generator[None]:
    _truncate_application_tables(postgres_engine)
    yield
    _truncate_application_tables(postgres_engine)


@pytest.fixture
def session(postgres_engine: Engine, clean_database: None) -> Generator[Session]:
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    with testing_session() as db_session:
        yield db_session


def _truncate_application_tables(engine: Engine) -> None:
    preserved = {"alembic_version", "species_catalog", "species_aliases"}
    table_names = [name for name in inspect(engine).get_table_names() if name not in preserved]
    if not table_names:
        return
    quoted_names = ", ".join(f'"{name}"' for name in table_names)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted_names} RESTART IDENTITY CASCADE"))
