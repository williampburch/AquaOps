from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.inventory import InventoryReadRepository, InventorySnapshot


@dataclass(frozen=True, slots=True)
class InventoryService:
    repository: InventoryReadRepository

    def get_livestock(self, user_id: int) -> InventorySnapshot:
        return self.repository.get_livestock(user_id)

    def get_plants(self, user_id: int) -> InventorySnapshot:
        return self.repository.get_plants(user_id)
