from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import LivestockModel, PlantModel, TankModel, UserModel
from app.infrastructure.repositories.inventory import SqlAlchemyInventoryRepository


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


def test_inventory_repository_groups_species_and_sums_quantities(session: Session) -> None:
    user = UserModel(
        email="inventory@example.com",
        username="inventory",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="planted")
    second_tank = TankModel(user=user, name="Shrimp Garden", tank_type="nano")
    session.add_all(
        [
            user,
            tank,
            second_tank,
            LivestockModel(
                tank=tank,
                common_name="Neon Tetra",
                species="Paracheirodon innesi",
                quantity=6,
            ),
            LivestockModel(
                tank=second_tank,
                common_name="Neon Tetra",
                species="Paracheirodon innesi",
                quantity=4,
            ),
            LivestockModel(
                tank=tank,
                common_name="Amano Shrimp",
                species="Caridina multidentata",
                quantity=3,
            ),
            PlantModel(
                tank=tank,
                common_name="Java Fern",
                species="Microsorum pteropus",
                quantity=3,
            ),
            PlantModel(
                tank=second_tank,
                common_name="Java Fern",
                species="Microsorum pteropus",
                quantity=2,
            ),
            PlantModel(
                tank=tank,
                common_name="Crypt Wendtii",
                species="Cryptocoryne wendtii",
                quantity=3,
            ),
        ]
    )
    session.commit()

    repository = SqlAlchemyInventoryRepository(session)

    livestock = repository.get_livestock(user.id)
    plants = repository.get_plants(user.id)

    assert livestock.summary.total_count == 13
    assert livestock.summary.species_count == 2
    assert livestock.summary.tank_count == 2
    assert livestock.groups[0].common_name == "Neon Tetra"
    assert livestock.groups[0].quantity == 10
    assert livestock.groups[0].tank_names == ["Display Tank", "Shrimp Garden"]
    assert plants.summary.total_count == 8
    assert plants.summary.species_count == 2
    assert plants.groups[0].common_name == "Java Fern"
    assert plants.groups[0].quantity == 5
