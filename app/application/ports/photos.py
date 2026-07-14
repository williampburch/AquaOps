from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class PhotoCreate:
    tank_id: int
    title: str
    caption: str | None
    occurred_at: datetime
    storage_path: str
    original_filename: str | None
    content_type: str
    byte_size: int
    checksum_sha256: str


@dataclass(frozen=True)
class StoredMedia:
    storage_path: str
    original_filename: str | None
    content_type: str | None


class PhotoRepository(Protocol):
    def create_photo(self, user_id: int, data: PhotoCreate) -> int | None:
        """Create a photo event and its media metadata for an owned tank."""

    def get_media(self, user_id: int, asset_id: int) -> StoredMedia | None:
        """Return an owned media asset."""
