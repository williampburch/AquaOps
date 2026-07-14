from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.application.photos.service import PhotoService
from app.application.ports.photos import PhotoCreate
from app.core.time import utc_now
from app.infrastructure.repositories.photos import SqlAlchemyPhotoRepository
from app.web.dependencies import AuthenticatedUser, get_db

router = APIRouter(tags=["photos"])
DbSession = Annotated[Session, Depends(get_db)]

MAX_PHOTO_BYTES = 12 * 1024 * 1024
IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
)


@router.post("/quick-log/photo")
async def quick_log_photo(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form(max_part_size=MAX_PHOTO_BYTES)
    upload = form.get("photo")
    tank_id = _optional_int(form.get("tank_id"))
    if tank_id is None or not isinstance(upload, UploadFile):
        return _photo_redirect(tank_id, error="Choose an aquarium and photo.")

    content = await upload.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        return _photo_redirect(tank_id, error="Photos must be 12 MB or smaller.")
    image_format = _image_format(content)
    if image_format is None:
        return _photo_redirect(tank_id, error="Use a JPEG, PNG, WebP, HEIC, or HEIF photo.")
    extension, content_type = image_format

    settings = request.app.state.settings
    relative_path = Path(str(current_user.id)) / f"{uuid4().hex}.{extension}"
    destination = settings.media_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    caption = _text(form.get("caption"))
    title = f"Photo: {caption}" if caption else "Tank photo"
    service = PhotoService(SqlAlchemyPhotoRepository(db))
    try:
        event_id = service.create_photo(
            current_user.id,
            PhotoCreate(
                tank_id=tank_id,
                title=title,
                caption=caption or None,
                occurred_at=_optional_datetime(_text(form.get("occurred_at"))) or utc_now(),
                storage_path=relative_path.as_posix(),
                original_filename=Path(upload.filename).name if upload.filename else None,
                content_type=content_type,
                byte_size=len(content),
                checksum_sha256=sha256(content).hexdigest(),
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except (ValueError, OSError):
        destination.unlink(missing_ok=True)
        return _photo_redirect(tank_id, error="The photo could not be saved. Please try again.")
    return _photo_redirect(tank_id, saved=True)


@router.get("/media/{asset_id}")
def serve_media(
    asset_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    media = PhotoService(SqlAlchemyPhotoRepository(db)).get_media(current_user.id, asset_id)
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    media_root = request.app.state.settings.media_root.resolve()
    path = (media_root / media.storage_path).resolve()
    if not path.is_relative_to(media_root) or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type=media.content_type or "application/octet-stream")


def _image_format(content: bytes) -> tuple[str, str] | None:
    for signature, extension, content_type in IMAGE_SIGNATURES:
        if content.startswith(signature):
            return extension, content_type
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp", "image/webp"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return "heic", "image/heic"
        if brand in {b"mif1", b"msf1", b"heif"}:
            return "heif", "image/heif"
    return None


def _photo_redirect(
    tank_id: int | None,
    *,
    saved: bool = False,
    error: str | None = None,
) -> RedirectResponse:
    from urllib.parse import urlencode

    query = urlencode(
        {
            key: value
            for key, value in {
                "action": "photo",
                "tank_id": tank_id,
                "saved": "photo" if saved else None,
                "error": error,
            }.items()
            if value is not None
        }
    )
    return RedirectResponse(f"/quick-log?{query}", status_code=status.HTTP_303_SEE_OTHER)


def _optional_int(value) -> int | None:
    try:
        return int(_text(value))
    except ValueError:
        return None


def _text(value) -> str:
    return str(value or "").strip()


def _optional_datetime(value: str) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
