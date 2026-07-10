from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.notifications.service import NotificationService
from app.core.config import get_settings
from app.infrastructure.repositories.notifications import SqlAlchemyNotificationRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def notifications_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = NotificationService(SqlAlchemyNotificationRepository(db))
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "notifications/index.html",
        {
            "title": "Notifications",
            "active_nav": "notifications",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "snapshot": service.get_notifications(
                current_user.id,
                preferences.reminder_window_days,
                preferences.plant_care_mode,
            ),
        },
    )
