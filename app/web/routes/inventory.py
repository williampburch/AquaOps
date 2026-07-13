from __future__ import annotations

from datetime import date
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.inventory.service import InventoryService
from app.application.ports.inventory import InventoryArchive, InventoryUpdate
from app.application.tanks.service import TankService
from app.core.config import get_settings
from app.infrastructure.repositories.inventory import SqlAlchemyInventoryRepository
from app.infrastructure.repositories.tanks import SqlAlchemyTankRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(tags=["inventory"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/livestock")
def livestock_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    tanks = TankService(SqlAlchemyTankRepository(db)).list_tanks(current_user.id)
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "inventory/livestock.html",
        {
            "title": "Livestock",
            "active_nav": "livestock",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "snapshot": service.get_livestock(current_user.id),
            "tanks": tanks,
            "saved": request.query_params.get("saved"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/plants")
def plants_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    tanks = TankService(SqlAlchemyTankRepository(db)).list_tanks(current_user.id)
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "inventory/plants.html",
        {
            "title": "Plants",
            "active_nav": "plants",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "snapshot": service.get_plants(current_user.id),
            "tanks": tanks,
            "saved": request.query_params.get("saved"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/livestock/{item_id}/update")
async def update_livestock(
    item_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        updated = service.update_livestock(
            current_user.id,
            item_id,
            InventoryUpdate(
                tank_id=_required_int(form.get("tank_id"), "Choose an aquarium"),
                common_name=_text(form.get("common_name")),
                species=_optional_text(form.get("species")),
                quantity=_required_int(form.get("quantity"), "Quantity is required"),
                notes=_optional_text(form.get("notes")),
                started_on=_optional_date(form.get("started_on")),
            ),
        )
        if not updated:
            raise ValueError("That livestock entry is no longer available")
    except ValueError as exc:
        return _inventory_redirect("livestock", error=str(exc))
    return _inventory_redirect("livestock", saved="Livestock updated")


@router.post("/livestock/{item_id}/archive")
async def archive_livestock(
    item_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        archived = service.archive_livestock(
            current_user.id,
            item_id,
            InventoryArchive(
                reason=_text(form.get("reason")),
                notes=_optional_text(form.get("notes")),
                ended_on=_optional_date(form.get("ended_on")) or date.today(),
            ),
        )
        if not archived:
            raise ValueError("That livestock entry is no longer available")
    except ValueError as exc:
        return _inventory_redirect("livestock", error=str(exc))
    return _inventory_redirect("livestock", saved="Livestock history updated")


@router.post("/plants/{item_id}/update")
async def update_plant(
    item_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        updated = service.update_plant(
            current_user.id,
            item_id,
            InventoryUpdate(
                tank_id=_required_int(form.get("tank_id"), "Choose an aquarium"),
                common_name=_text(form.get("common_name")),
                species=_optional_text(form.get("species")),
                quantity=_required_int(form.get("quantity"), "Quantity is required"),
                notes=_optional_text(form.get("notes")),
                started_on=_optional_date(form.get("started_on")),
            ),
        )
        if not updated:
            raise ValueError("That plant entry is no longer available")
    except ValueError as exc:
        return _inventory_redirect("plants", error=str(exc))
    return _inventory_redirect("plants", saved="Plant updated")


@router.post("/plants/{item_id}/archive")
async def archive_plant(
    item_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        archived = service.archive_plant(
            current_user.id,
            item_id,
            InventoryArchive(
                reason=_text(form.get("reason")),
                notes=_optional_text(form.get("notes")),
                ended_on=_optional_date(form.get("ended_on")) or date.today(),
            ),
        )
        if not archived:
            raise ValueError("That plant entry is no longer available")
    except ValueError as exc:
        return _inventory_redirect("plants", error=str(exc))
    return _inventory_redirect("plants", saved="Plant history updated")


def _inventory_redirect(
    page: str,
    *,
    saved: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    query = urlencode(
        {key: value for key, value in {"saved": saved, "error": error}.items() if value}
    )
    suffix = f"?{query}" if query else ""
    return RedirectResponse(f"/{page}{suffix}", status_code=status.HTTP_303_SEE_OTHER)


def _text(value) -> str:
    return str(value or "").strip()


def _optional_text(value) -> str | None:
    return _text(value) or None


def _required_int(value, message: str) -> int:
    try:
        return int(_text(value))
    except ValueError as exc:
        raise ValueError(message) from exc


def _optional_date(value) -> date | None:
    text = _text(value)
    return date.fromisoformat(text) if text else None
