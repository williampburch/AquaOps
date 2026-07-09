from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InventorySummary:
    total_count: int
    species_count: int
    tank_count: int


@dataclass(frozen=True)
class InventoryGroup:
    common_name: str
    species: str | None
    quantity: int
    tank_names: list[str]


@dataclass(frozen=True)
class InventorySnapshot:
    summary: InventorySummary
    groups: list[InventoryGroup]


class InventoryReadRepository(Protocol):
    def get_livestock(self, user_id: int) -> InventorySnapshot:
        """Return grouped livestock inventory for a user."""

    def get_plants(self, user_id: int) -> InventorySnapshot:
        """Return grouped plant inventory for a user."""
