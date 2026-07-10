from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.dashboard.service import DashboardService
from app.core.config import get_settings
from app.infrastructure.repositories.dashboard import SqlAlchemyDashboardRepository
from app.web.dependencies import CurrentUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/")
def dashboard(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
):
    service = DashboardService(SqlAlchemyDashboardRepository(db))
    preferences = preferences_for_user(db, current_user)
    snapshot = service.get_dashboard(
        current_user.id if current_user else None,
        preferences.reminder_window_days,
        preferences.plant_care_mode,
    )
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "title": "Dashboard",
            "active_nav": "dashboard",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "snapshot": snapshot,
        },
    )
