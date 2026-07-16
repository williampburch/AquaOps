from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.inventory import (
    InventoryArchive,
    InventoryUpdate,
    LivestockCreate,
    PlantCreate,
)
from app.core.security import hash_password
from app.infrastructure.db.models import (
    EventModel,
    LivestockModel,
    PlantModel,
    SpeciesCatalogModel,
    TankModel,
    UserModel,
)
from app.infrastructure.repositories.inventory import SqlAlchemyInventoryRepository


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
    fish = session.scalar(
        select(SpeciesCatalogModel).where(SpeciesCatalogModel.common_name == "Neon Tetra")
    )
    plant = session.scalar(
        select(SpeciesCatalogModel).where(SpeciesCatalogModel.common_name == "Java Fern")
    )
    assert fish is not None
    assert plant is not None
    session.add_all([user, tank])
    session.commit()

    repository = SqlAlchemyInventoryRepository(session)
    livestock_catalog = repository.list_catalog(("fish", "invertebrate"))
    plant_catalog = repository.list_catalog(("plant",))

    neon_tetra = next(item for item in livestock_catalog if item.common_name == "Neon Tetra")
    java_fern = next(item for item in plant_catalog if item.common_name == "Java Fern")
    assert neon_tetra.detail == "Beginner - Group 6+"
    assert java_fern.detail == "Beginner - Low light"

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


def test_inventory_repository_updates_moves_and_archives_with_history(session: Session) -> None:
    user = UserModel(
        email="history@example.com",
        username="history",
        password_hash=hash_password("a-long-test-password"),
    )
    display_tank = TankModel(user=user, name="Display Tank", tank_type="planted")
    grow_out = TankModel(user=user, name="Grow Out", tank_type="freshwater")
    livestock = LivestockModel(
        tank=display_tank,
        common_name="Ember Tetra",
        species="Hyphessobrycon amandae",
        quantity=8,
    )
    plant = PlantModel(
        tank=display_tank,
        common_name="Java Fern",
        species="Microsorum pteropus",
        quantity=2,
    )
    session.add_all([user, display_tank, grow_out, livestock, plant])
    session.commit()

    repository = SqlAlchemyInventoryRepository(session)
    assert repository.get_livestock(user.id).items[0].id == livestock.id
    assert repository.get_plants(user.id).items[0].id == plant.id

    updated = repository.update_livestock(
        user.id,
        livestock.id,
        InventoryUpdate(
            tank_id=grow_out.id,
            common_name="Ember Tetra",
            species="Hyphessobrycon amandae",
            quantity=6,
            notes="Moved the smaller group",
            started_on=date(2026, 7, 1),
        ),
    )
    archived = repository.archive_plant(
        user.id,
        plant.id,
        InventoryArchive(
            reason="melted",
            notes="Did not adapt after planting",
            ended_on=date(2026, 7, 13),
        ),
    )

    assert updated is True
    assert archived is True
    assert repository.get_livestock(user.id).items[0].tank_name == "Grow Out"
    assert repository.get_livestock(user.id).items[0].quantity == 6
    assert repository.get_plants(user.id).summary.total_count == 0
    assert session.get(PlantModel, plant.id).removed_on == date(2026, 7, 13)

    events = session.query(EventModel).order_by(EventModel.id).all()
    assert events[0].event_type == "livestock_change"
    assert events[0].title == "Updated Ember Tetra"
    assert "Moved from Display Tank to Grow Out" in events[0].notes
    assert events[1].event_type == "plant_change"
    assert events[1].title == "Melted: Java Fern"


def test_inventory_repository_rejects_cross_user_lifecycle_changes(session: Session) -> None:
    owner = UserModel(
        email="owner@example.com",
        username="owner",
        password_hash=hash_password("a-long-test-password"),
    )
    other = UserModel(
        email="other@example.com",
        username="other",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=owner, name="Owner Tank", tank_type="freshwater")
    other_tank = TankModel(user=other, name="Other Tank", tank_type="freshwater")
    livestock = LivestockModel(tank=tank, common_name="Guppy", quantity=3)
    session.add_all([owner, other, tank, other_tank, livestock])
    session.commit()

    repository = SqlAlchemyInventoryRepository(session)
    updated = repository.update_livestock(
        other.id,
        livestock.id,
        InventoryUpdate(
            tank_id=other_tank.id,
            common_name="Guppy",
            species=None,
            quantity=1,
            notes=None,
            started_on=None,
        ),
    )
    archived = repository.archive_livestock(
        other.id,
        livestock.id,
        InventoryArchive(reason="other", notes=None, ended_on=date(2026, 7, 13)),
    )

    assert updated is False
    assert archived is False
    assert session.get(LivestockModel, livestock.id).quantity == 3
    assert session.get(LivestockModel, livestock.id).retired_on is None
