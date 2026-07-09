from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.activity.service import ActivityService
from app.core.config import get_settings
from app.infrastructure.repositories.activity import SqlAlchemyActivityRepository
from app.web.dependencies import AuthenticatedUser, get_db

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def reports_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = ActivityService(SqlAlchemyActivityRepository(db))
    snapshot = service.get_reports_snapshot(current_user.id)
    return templates.TemplateResponse(
        request,
        "reports/index.html",
        {
            "title": "Reports",
            "active_nav": "reports",
            "current_user": current_user,
            "snapshot": snapshot,
            "event_mix_payload": [
                {"label": item.event_type.replace("_", " ").title(), "value": item.count}
                for item in snapshot.event_type_summary
            ],
            "nitrate_payload": [
                {
                    "date": point.occurred_at,
                    "value": point.value,
                    "tank": point.tank_name,
                }
                for point in snapshot.nitrate_trend
            ],
        },
    )
