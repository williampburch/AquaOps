from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.ports.inventory import (
    InventoryArchive,
    InventoryGroup,
    InventoryItem,
    InventoryQuantityChange,
    InventorySnapshot,
    InventorySummary,
    InventoryUpdate,
    LivestockCreate,
    PlantCreate,
    SpeciesCatalogEntry,
)
from app.core.time import utc_now
from app.domain.enums import EventType
from app.infrastructure.db.models import (
    EventModel,
    LivestockModel,
    PlantModel,
    SpeciesCatalogModel,
    TankModel,
)


class SqlAlchemyInventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_livestock(self, user_id: int) -> InventorySnapshot:
        quantity_expression = LivestockModel.quantity
        return self._build_snapshot(
            user_id=user_id,
            model=LivestockModel,
            quantity_expression=quantity_expression,
            inactive_column=LivestockModel.retired_on,
        )

    def get_plants(self, user_id: int) -> InventorySnapshot:
        quantity_expression = func.coalesce(PlantModel.quantity, 1)
        return self._build_snapshot(
            user_id=user_id,
            model=PlantModel,
            quantity_expression=quantity_expression,
            inactive_column=PlantModel.removed_on,
        )

    def list_catalog(self, categories: tuple[str, ...]) -> list[SpeciesCatalogEntry]:
        statement = (
            select(SpeciesCatalogModel)
            .where(SpeciesCatalogModel.category.in_(categories))
            .order_by(SpeciesCatalogModel.category.asc(), SpeciesCatalogModel.common_name.asc())
        )
        return [
            SpeciesCatalogEntry(
                id=entry.id,
                category=entry.category,
                common_name=entry.common_name,
                scientific_name=entry.scientific_name,
                care_level=entry.care_level,
                detail=_catalog_detail(entry),
            )
            for entry in self.session.scalars(statement)
        ]

    def add_livestock(self, user_id: int, data: LivestockCreate) -> int | None:
        if not self._owns_tank(user_id, data.tank_id):
            return None
        catalog_entry = self._catalog_entry(data.catalog_entry_id, ("fish", "invertebrate"))
        common_name = (data.common_name or "").strip() or (
            catalog_entry.common_name if catalog_entry else ""
        )
        if not common_name:
            raise ValueError("Common name is required")
        model = LivestockModel(
            tank_id=data.tank_id,
            species_catalog_id=catalog_entry.id if catalog_entry else None,
            common_name=common_name,
            species=(data.species or "").strip()
            or (catalog_entry.scientific_name if catalog_entry else None),
            quantity=data.quantity,
            sex=data.sex,
            notes=data.notes,
            acquired_on=data.acquired_on,
        )
        self.session.add(model)
        self.session.flush()
        self._record_change(
            user_id,
            data.tank_id,
            EventType.LIVESTOCK_CHANGE.value,
            f"Added {data.quantity} {common_name}",
            data.notes,
            {"action": "acquired", "livestock_id": model.id, "quantity": data.quantity},
        )
        self.session.commit()
        return model.id

    def add_plant(self, user_id: int, data: PlantCreate) -> int | None:
        if not self._owns_tank(user_id, data.tank_id):
            return None
        catalog_entry = self._catalog_entry(data.catalog_entry_id, ("plant",))
        common_name = (data.common_name or "").strip() or (
            catalog_entry.common_name if catalog_entry else ""
        )
        if not common_name:
            raise ValueError("Common name is required")
        model = PlantModel(
            tank_id=data.tank_id,
            species_catalog_id=catalog_entry.id if catalog_entry else None,
            common_name=common_name,
            species=(data.species or "").strip()
            or (catalog_entry.scientific_name if catalog_entry else None),
            quantity=data.quantity,
            notes=data.notes,
            planted_on=data.planted_on,
        )
        self.session.add(model)
        self.session.flush()
        self._record_change(
            user_id,
            data.tank_id,
            EventType.PLANT_CHANGE.value,
            f"Added {data.quantity or 1} {common_name}",
            data.notes,
            {"action": "added", "plant_id": model.id, "quantity": data.quantity or 1},
        )
        self.session.commit()
        return model.id

    def update_livestock(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        item = self._active_item(user_id, item_id, LivestockModel, LivestockModel.retired_on)
        destination = self._owned_tank(user_id, data.tank_id)
        if item is None or destination is None:
            return False
        old_tank = item.tank.name
        old_quantity = item.quantity
        changes = _change_notes(item, data, old_tank, destination.name)
        item.tank_id = destination.id
        item.common_name = data.common_name.strip()
        item.species = (data.species or "").strip() or None
        item.quantity = data.quantity
        item.notes = data.notes
        item.acquired_on = data.started_on
        if changes:
            self._record_change(
                user_id,
                destination.id,
                EventType.LIVESTOCK_CHANGE.value,
                f"Updated {item.common_name}",
                "; ".join(changes),
                {
                    "action": "updated",
                    "livestock_id": item.id,
                    "quantity_before": old_quantity,
                    "quantity_after": data.quantity,
                },
            )
        self.session.commit()
        return True

    def update_plant(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        item = self._active_item(user_id, item_id, PlantModel, PlantModel.removed_on)
        destination = self._owned_tank(user_id, data.tank_id)
        if item is None or destination is None:
            return False
        old_tank = item.tank.name
        old_quantity = item.quantity or 1
        changes = _change_notes(item, data, old_tank, destination.name)
        item.tank_id = destination.id
        item.common_name = data.common_name.strip()
        item.species = (data.species or "").strip() or None
        item.quantity = data.quantity
        item.notes = data.notes
        item.planted_on = data.started_on
        if changes:
            self._record_change(
                user_id,
                destination.id,
                EventType.PLANT_CHANGE.value,
                f"Updated {item.common_name}",
                "; ".join(changes),
                {
                    "action": "updated",
                    "plant_id": item.id,
                    "quantity_before": old_quantity,
                    "quantity_after": data.quantity,
                },
            )
        self.session.commit()
        return True

    def archive_livestock(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        item = self._active_item(user_id, item_id, LivestockModel, LivestockModel.retired_on)
        if item is None:
            return False
        item.retired_on = data.ended_on
        self._record_change(
            user_id,
            item.tank_id,
            EventType.LIVESTOCK_CHANGE.value,
            f"{_reason_label(data.reason)}: {item.common_name}",
            data.notes,
            {
                "action": data.reason,
                "livestock_id": item.id,
                "quantity": item.quantity,
            },
        )
        self.session.commit()
        return True

    def archive_plant(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        item = self._active_item(user_id, item_id, PlantModel, PlantModel.removed_on)
        if item is None:
            return False
        item.removed_on = data.ended_on
        self._record_change(
            user_id,
            item.tank_id,
            EventType.PLANT_CHANGE.value,
            f"{_reason_label(data.reason)}: {item.common_name}",
            data.notes,
            {"action": data.reason, "plant_id": item.id, "quantity": item.quantity or 1},
        )
        self.session.commit()
        return True

    def change_livestock_quantity(
        self, user_id: int, item_id: int, data: InventoryQuantityChange
    ) -> bool:
        item = self._active_item(user_id, item_id, LivestockModel, LivestockModel.retired_on)
        if item is None:
            return False
        self._change_quantity(
            user_id=user_id,
            item=item,
            data=data,
            event_type=EventType.LIVESTOCK_CHANGE.value,
            item_key="livestock_id",
            inactive_field="retired_on",
        )
        return True

    def change_plant_quantity(
        self, user_id: int, item_id: int, data: InventoryQuantityChange
    ) -> bool:
        item = self._active_item(user_id, item_id, PlantModel, PlantModel.removed_on)
        if item is None:
            return False
        self._change_quantity(
            user_id=user_id,
            item=item,
            data=data,
            event_type=EventType.PLANT_CHANGE.value,
            item_key="plant_id",
            inactive_field="removed_on",
        )
        return True

    def _change_quantity(
        self,
        *,
        user_id: int,
        item,
        data: InventoryQuantityChange,
        event_type: str,
        item_key: str,
        inactive_field: str,
    ) -> None:
        quantity_before = item.quantity or 1
        if data.direction == "remove" and data.quantity > quantity_before:
            raise ValueError(f"Only {quantity_before} {item.common_name} are currently recorded")

        quantity_after = (
            quantity_before + data.quantity
            if data.direction == "add"
            else quantity_before - data.quantity
        )
        if quantity_after == 0:
            setattr(item, inactive_field, data.occurred_on)
        else:
            item.quantity = quantity_after

        if data.direction == "add":
            title = f"Added {data.quantity} {item.common_name}"
            action = "acquired"
        else:
            title = f"{_reason_label(data.reason or 'removed')}: {data.quantity} {item.common_name}"
            action = data.reason or "removed"
        self._record_change(
            user_id,
            item.tank_id,
            event_type,
            title,
            data.notes,
            {
                "action": action,
                item_key: item.id,
                "quantity_changed": data.quantity,
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
            },
        )
        self.session.commit()

    def _build_snapshot(
        self,
        *,
        user_id: int,
        model: type[LivestockModel] | type[PlantModel],
        quantity_expression,
        inactive_column,
    ) -> InventorySnapshot:
        base_filters = (TankModel.user_id == user_id, inactive_column.is_(None))
        summary = InventorySummary(
            total_count=self._total_count(model, quantity_expression, base_filters),
            species_count=self._species_count(model, base_filters),
            tank_count=self._tank_count(model, base_filters),
        )
        return InventorySnapshot(
            summary=summary,
            groups=self._groups(model, quantity_expression, base_filters),
            items=self._items(model, quantity_expression, base_filters),
        )

    def _items(self, model, quantity_expression, base_filters) -> list[InventoryItem]:
        date_column = model.acquired_on if model is LivestockModel else model.planted_on
        statement = (
            select(model, TankModel.name, quantity_expression, date_column)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
            .order_by(TankModel.name.asc(), model.common_name.asc(), model.id.asc())
        )
        return [
            InventoryItem(
                id=item.id,
                tank_id=item.tank_id,
                tank_name=tank_name,
                common_name=item.common_name,
                species=item.species,
                quantity=int(quantity or 1),
                notes=item.notes,
                started_on=started_on,
            )
            for item, tank_name, quantity, started_on in self.session.execute(statement).all()
        ]

    def _total_count(self, model, quantity_expression, base_filters) -> int:
        statement = (
            select(func.coalesce(func.sum(quantity_expression), 0))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _species_count(self, model, base_filters) -> int:
        species_key = func.coalesce(model.species, model.common_name)
        statement = (
            select(func.count(func.distinct(species_key)))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _tank_count(self, model, base_filters) -> int:
        statement = (
            select(func.count(func.distinct(model.tank_id)))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _groups(self, model, quantity_expression, base_filters) -> list[InventoryGroup]:
        statement = (
            select(
                model.common_name,
                model.species,
                func.sum(quantity_expression),
                func.group_concat(func.distinct(TankModel.name)),
            )
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
            .group_by(model.common_name, model.species)
            .order_by(func.sum(quantity_expression).desc(), model.common_name.asc())
        )
        return [
            InventoryGroup(
                common_name=common_name,
                species=species,
                quantity=int(quantity or 0),
                tank_names=self._split_tank_names(tank_names),
            )
            for common_name, species, quantity, tank_names in self.session.execute(statement).all()
        ]

    def _split_tank_names(self, tank_names: str | None) -> list[str]:
        if not tank_names:
            return []
        return sorted(tank_names.split(","))

    def _owns_tank(self, user_id: int, tank_id: int) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(TankModel)
                .where(
                    TankModel.id == tank_id,
                    TankModel.user_id == user_id,
                    TankModel.archived_at.is_(None),
                )
            )
            or 0
        ) > 0

    def _owned_tank(self, user_id: int, tank_id: int) -> TankModel | None:
        return self.session.execute(
            select(TankModel).where(
                TankModel.id == tank_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
            )
        ).scalar_one_or_none()

    def _active_item(self, user_id: int, item_id: int, model, inactive_column):
        return self.session.execute(
            select(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(
                model.id == item_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
                inactive_column.is_(None),
            )
        ).scalar_one_or_none()

    def _record_change(
        self,
        user_id: int,
        tank_id: int,
        event_type: str,
        title: str,
        notes: str | None,
        metadata: dict,
    ) -> None:
        self.session.add(
            EventModel(
                user_id=user_id,
                tank_id=tank_id,
                event_type=event_type,
                title=title,
                notes=notes or "",
                occurred_at=utc_now(),
                metadata_json=metadata,
            )
        )

    def _catalog_entry(
        self,
        catalog_entry_id: int | None,
        categories: tuple[str, ...],
    ) -> SpeciesCatalogModel | None:
        if catalog_entry_id is None:
            return None
        return self.session.execute(
            select(SpeciesCatalogModel).where(
                SpeciesCatalogModel.id == catalog_entry_id,
                SpeciesCatalogModel.category.in_(categories),
            )
        ).scalar_one_or_none()


def _catalog_detail(entry: SpeciesCatalogModel) -> str | None:
    details = []
    if entry.care_level:
        details.append(entry.care_level.title())
    if entry.category in {"fish", "invertebrate"} and entry.social_group_min:
        details.append(f"Group {entry.social_group_min}+")
    if entry.category == "plant" and entry.light_requirement:
        details.append(f"{entry.light_requirement.title()} light")
    return " - ".join(details) if details else None


def _change_notes(item, data: InventoryUpdate, old_tank: str, new_tank: str) -> list[str]:
    changes = []
    old_quantity = item.quantity or 1
    if old_quantity != data.quantity:
        changes.append(f"Quantity {old_quantity} to {data.quantity}")
    if old_tank != new_tank:
        changes.append(f"Moved from {old_tank} to {new_tank}")
    if item.common_name != data.common_name.strip():
        changes.append(f"Renamed from {item.common_name} to {data.common_name.strip()}")
    if (item.species or "") != (data.species or "").strip():
        changes.append("Scientific name updated")
    if item.notes != data.notes:
        changes.append("Notes updated")
    date_value = item.acquired_on if isinstance(item, LivestockModel) else item.planted_on
    if date_value != data.started_on:
        changes.append("Start date updated")
    return changes


def _reason_label(reason: str) -> str:
    return reason.replace("_", " ").title()
