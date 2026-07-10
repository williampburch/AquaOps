from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.ports.inventory import LivestockCreate, PlantCreate
from app.core.security import hash_password
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    LivestockModel,
    PlantModel,
    SpeciesCatalogModel,
    TankModel,
    UserModel,
)
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


def test_inventory_repository_adds_entries_from_catalog(session: Session) -> None:
    user = UserModel(
        email="catalog@example.com",
        username="catalog",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=user, name="Display Tank", tank_type="planted")
    fish = SpeciesCatalogModel(
        category="fish",
        common_name="Neon Tetra",
        scientific_name="Paracheirodon innesi",
        care_level="beginner",
        social_group_min=6,
        source="test",
        is_builtin=True,
        external_refs={},
    )
    plant = SpeciesCatalogModel(
        category="plant",
        common_name="Java Fern",
        scientific_name="Microsorum pteropus",
        care_level="beginner",
        light_requirement="low",
        source="test",
        is_builtin=True,
        external_refs={},
    )
    session.add_all([user, tank, fish, plant])
    session.commit()

    repository = SqlAlchemyInventoryRepository(session)
    livestock_catalog = repository.list_catalog(("fish", "invertebrate"))
    plant_catalog = repository.list_catalog(("plant",))

    assert livestock_catalog[0].common_name == "Neon Tetra"
    assert livestock_catalog[0].detail == "Beginner - Group 6+"
    assert plant_catalog[0].detail == "Beginner - Low light"

    livestock_id = repository.add_livestock(
        user.id,
        LivestockCreate(
            tank_id=tank.id,
            catalog_entry_id=fish.id,
            common_name=None,
            species=None,
            quantity=8,
            sex=None,
            notes=None,
            acquired_on=None,
        ),
    )
    plant_id = repository.add_plant(
        user.id,
        PlantCreate(
            tank_id=tank.id,
            catalog_entry_id=plant.id,
            common_name=None,
            species=None,
            quantity=2,
            notes=None,
            planted_on=None,
        ),
    )

    assert livestock_id is not None
    assert plant_id is not None
    livestock = session.get(LivestockModel, livestock_id)
    stored_plant = session.get(PlantModel, plant_id)
    assert livestock.common_name == "Neon Tetra"
    assert livestock.species == "Paracheirodon innesi"
    assert livestock.species_catalog_id == fish.id
    assert stored_plant.common_name == "Java Fern"
    assert stored_plant.species == "Microsorum pteropus"
    assert stored_plant.species_catalog_id == plant.id
