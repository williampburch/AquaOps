from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExportTable:
    filename: str
    columns: tuple[str, ...]
    rows: list[tuple[object, ...]]


class DataExportRepository(Protocol):
    def get_export_tables(self, user_id: int) -> list[ExportTable]:
        """Return all portable, user-owned data grouped into flat tables."""
