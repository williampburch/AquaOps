from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.activity.service import ActivityService
from app.core.config import get_settings
from app.infrastructure.repositories.activity import SqlAlchemyActivityRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def events_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = ActivityService(SqlAlchemyActivityRepository(db))
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "events/index.html",
        {
            "title": "Events",
            "active_nav": "events",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "events": service.list_recent_events(
                current_user.id,
                preferences.plant_care_mode,
            ),
        },
    )
