from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.inventory import (
    InventoryArchive,
    InventoryQuantityChange,
    InventoryReadRepository,
    InventorySnapshot,
    InventoryUpdate,
    LivestockCreate,
    PlantCreate,
    SpeciesCatalogEntry,
)


@dataclass(frozen=True)
class InventoryService:
    repository: InventoryReadRepository

    def get_livestock(self, user_id: int) -> InventorySnapshot:
        return self.repository.get_livestock(user_id)

    def get_plants(self, user_id: int) -> InventorySnapshot:
        return self.repository.get_plants(user_id)

    def list_livestock_catalog(self) -> list[SpeciesCatalogEntry]:
        return self.repository.list_catalog(("fish", "invertebrate"))

    def list_plant_catalog(self) -> list[SpeciesCatalogEntry]:
        return self.repository.list_catalog(("plant",))

    def add_livestock(self, user_id: int, data: LivestockCreate) -> int | None:
        if data.catalog_entry_id is None and not (data.common_name or "").strip():
            raise ValueError("Common name is required")
        if data.quantity < 1:
            raise ValueError("Quantity must be at least 1")
        return self.repository.add_livestock(user_id, data)

    def add_plant(self, user_id: int, data: PlantCreate) -> int | None:
        if data.catalog_entry_id is None and not (data.common_name or "").strip():
            raise ValueError("Common name is required")
        if data.quantity is not None and data.quantity < 1:
            raise ValueError("Quantity must be at least 1")
        return self.repository.add_plant(user_id, data)

    def update_livestock(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        self._validate_update(data)
        return self.repository.update_livestock(user_id, item_id, data)

    def update_plant(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        self._validate_update(data)
        return self.repository.update_plant(user_id, item_id, data)

    def archive_livestock(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        if data.reason not in {"death", "rehomed", "sold", "moved_out", "other"}:
            raise ValueError("Choose what happened to this livestock")
        return self.repository.archive_livestock(user_id, item_id, data)

    def archive_plant(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        if data.reason not in {"removed", "melted", "propagated", "moved_out", "other"}:
            raise ValueError("Choose what happened to this plant")
        return self.repository.archive_plant(user_id, item_id, data)

    def change_livestock_quantity(
        self, user_id: int, item_id: int, data: InventoryQuantityChange
    ) -> bool:
        self._validate_quantity_change(
            data,
            removal_reasons={"death", "rehomed", "sold", "moved_out", "other"},
            missing_reason="Choose what happened to this livestock",
        )
        return self.repository.change_livestock_quantity(user_id, item_id, data)

    def change_plant_quantity(
        self, user_id: int, item_id: int, data: InventoryQuantityChange
    ) -> bool:
        self._validate_quantity_change(
            data,
            removal_reasons={"removed", "melted", "propagated", "moved_out", "other"},
            missing_reason="Choose what happened to this plant",
        )
        return self.repository.change_plant_quantity(user_id, item_id, data)

    def _validate_update(self, data: InventoryUpdate) -> None:
        if not data.common_name.strip():
            raise ValueError("Common name is required")
        if data.quantity < 1:
            raise ValueError("Quantity must be at least 1")

    def _validate_quantity_change(
        self,
        data: InventoryQuantityChange,
        *,
        removal_reasons: set[str],
        missing_reason: str,
    ) -> None:
        if data.direction not in {"add", "remove"}:
            raise ValueError("Choose whether you added or removed inventory")
        if data.quantity < 1:
            raise ValueError("Quantity must be at least 1")
        if data.direction == "remove" and data.reason not in removal_reasons:
            raise ValueError(missing_reason)
