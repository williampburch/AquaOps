from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.photos import PhotoCreate, StoredMedia
from app.domain.enums import EventType
from app.infrastructure.db.models import (
    EventModel,
    MediaAssetModel,
    PhotoEventDetailModel,
    TankModel,
)


class SqlAlchemyPhotoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_photo(self, user_id: int, data: PhotoCreate) -> int | None:
        tank = self.session.execute(
            select(TankModel).where(
                TankModel.id == data.tank_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
            )
        ).scalar_one_or_none()
        if tank is None:
            return None

        media = MediaAssetModel(
            user_id=user_id,
            storage_path=data.storage_path,
            original_filename=data.original_filename,
            content_type=data.content_type,
            byte_size=data.byte_size,
            checksum_sha256=data.checksum_sha256,
        )
        event = EventModel(
            user_id=user_id,
            tank_id=tank.id,
            event_type=EventType.PHOTO.value,
            title=data.title.strip()[:180],
            notes=data.caption or "",
            occurred_at=data.occurred_at,
            metadata_json={},
        )
        self.session.add_all([media, event])
        self.session.flush()
        self.session.add(
            PhotoEventDetailModel(
                event_id=event.id,
                media_asset_id=media.id,
                caption=(data.caption or "").strip()[:240] or None,
            )
        )
        self.session.commit()
        return event.id

    def get_media(self, user_id: int, asset_id: int) -> StoredMedia | None:
        media = self.session.execute(
            select(MediaAssetModel).where(
                MediaAssetModel.id == asset_id,
                MediaAssetModel.user_id == user_id,
            )
        ).scalar_one_or_none()
        if media is None:
            return None
        return StoredMedia(
            storage_path=media.storage_path,
            original_filename=media.original_filename,
            content_type=media.content_type,
        )
