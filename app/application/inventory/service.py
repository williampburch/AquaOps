from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.inventory import (
    InventoryReadRepository,
    InventorySnapshot,
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
