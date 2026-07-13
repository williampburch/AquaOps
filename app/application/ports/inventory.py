from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
class InventoryItem:
    id: int
    tank_id: int
    tank_name: str
    common_name: str
    species: str | None
    quantity: int
    notes: str | None
    started_on: date | None


@dataclass(frozen=True)
class InventorySnapshot:
    summary: InventorySummary
    groups: list[InventoryGroup]
    items: list[InventoryItem]


@dataclass(frozen=True)
class SpeciesCatalogEntry:
    id: int
    category: str
    common_name: str
    scientific_name: str | None
    care_level: str | None
    detail: str | None = None


@dataclass(frozen=True)
class LivestockCreate:
    tank_id: int
    catalog_entry_id: int | None
    common_name: str | None
    species: str | None
    quantity: int
    sex: str | None
    notes: str | None
    acquired_on: date | None


@dataclass(frozen=True)
class PlantCreate:
    tank_id: int
    catalog_entry_id: int | None
    common_name: str | None
    species: str | None
    quantity: int | None
    notes: str | None
    planted_on: date | None


@dataclass(frozen=True)
class InventoryUpdate:
    tank_id: int
    common_name: str
    species: str | None
    quantity: int
    notes: str | None
    started_on: date | None


@dataclass(frozen=True)
class InventoryArchive:
    reason: str
    notes: str | None
    ended_on: date


class InventoryReadRepository(Protocol):
    def get_livestock(self, user_id: int) -> InventorySnapshot:
        """Return grouped livestock inventory for a user."""

    def get_plants(self, user_id: int) -> InventorySnapshot:
        """Return grouped plant inventory for a user."""

    def list_catalog(self, categories: tuple[str, ...]) -> list[SpeciesCatalogEntry]:
        """Return built-in species catalog rows for dropdowns."""

    def add_livestock(self, user_id: int, data: LivestockCreate) -> int | None:
        """Add livestock to a user's tank from catalog or custom text."""

    def add_plant(self, user_id: int, data: PlantCreate) -> int | None:
        """Add a plant to a user's tank from catalog or custom text."""

    def update_livestock(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        """Update or move an active livestock entry."""

    def update_plant(self, user_id: int, item_id: int, data: InventoryUpdate) -> bool:
        """Update or move an active plant entry."""

    def archive_livestock(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        """Retire an active livestock entry while preserving history."""

    def archive_plant(self, user_id: int, item_id: int, data: InventoryArchive) -> bool:
        """Remove an active plant entry while preserving history."""
