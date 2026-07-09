from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.dashboard.service import DashboardService
from app.core.config import get_settings
from app.infrastructure.db.models import UserModel
from app.infrastructure.repositories.dashboard import SqlAlchemyDashboardRepository
from app.web.dependencies import get_current_user, get_db

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/")
def dashboard(
    request: Request,
    db: DbSession,
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    service = DashboardService(SqlAlchemyDashboardRepository(db))
    snapshot = service.get_dashboard(current_user.id if current_user else None)
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "title": "Dashboard",
            "active_nav": "dashboard",
            "current_user": current_user,
            "snapshot": snapshot,
        },
    )
