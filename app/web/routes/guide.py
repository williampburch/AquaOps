from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.web.dependencies import CurrentUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(tags=["guide"])
templates = Jinja2Templates(directory=get_settings().templates_dir)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/guide")
def user_guide(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
):
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "guide/index.html",
        {
            "title": "User Guide",
            "active_nav": "guide",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
        },
    )
