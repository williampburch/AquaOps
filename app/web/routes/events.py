from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.activity.service import ActivityService
from app.core.config import get_settings
from app.infrastructure.db.models import UserModel
from app.infrastructure.repositories.activity import SqlAlchemyActivityRepository
from app.web.dependencies import AuthenticatedUser, get_current_user, get_db

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def events_index(
    request: Request,
    db: DbSession,
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    if current_user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    service = ActivityService(SqlAlchemyActivityRepository(db))
    return templates.TemplateResponse(
        request,
        "events/index.html",
        {
            "title": "Events",
            "active_nav": "events",
            "current_user": current_user,
            "events": service.list_recent_events(current_user.id),
        },
    )
