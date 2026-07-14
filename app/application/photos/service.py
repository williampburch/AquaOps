from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.photos import PhotoCreate, PhotoRepository, StoredMedia


@dataclass(frozen=True)
class PhotoService:
    repository: PhotoRepository

    def create_photo(self, user_id: int, data: PhotoCreate) -> int | None:
        if not data.title.strip():
            raise ValueError("Add a short title or caption for this photo.")
        if data.byte_size < 1:
            raise ValueError("Choose a photo to upload.")
        return self.repository.create_photo(user_id, data)

    def get_media(self, user_id: int, asset_id: int) -> StoredMedia | None:
        return self.repository.get_media(user_id, asset_id)
