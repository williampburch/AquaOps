from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.inventory.service import InventoryService
from app.core.config import get_settings
from app.infrastructure.repositories.inventory import SqlAlchemyInventoryRepository
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
        },
    )


@router.get("/plants")
def plants_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = InventoryService(SqlAlchemyInventoryRepository(db))
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
        },
    )
