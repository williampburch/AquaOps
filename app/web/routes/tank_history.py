from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.history.service import (
    CARE_HISTORY_FILTERS,
    MAINTENANCE_TASK_FILTERS,
    CareHistoryService,
)
from app.core.config import get_settings
from app.domain.water import metric_label
from app.infrastructure.repositories.history import SqlAlchemyCareHistoryRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/tanks", tags=["tank-history"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{tank_id}/history")
def tank_history(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
    category: str = Query("all", alias="filter"),
    task: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    preferences = preferences_for_user(db, current_user)
    display = UserDisplay(preferences)
    service = CareHistoryService(SqlAlchemyCareHistoryRepository(db))
    category, task = service.normalize_filters(category, task)
    history = service.list_tank_history(
        current_user.id,
        tank_id,
        category=category,
        maintenance_type=task,
        page=page,
        plant_care_mode=preferences.plant_care_mode,
    )
    if history is None:
        return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request,
        "history/index.html",
        {
            "title": f"{history.tank_name} Care History",
            "active_nav": "tanks",
            "current_user": current_user,
            "preferences": preferences,
            "display": display,
            "history": history,
            "history_filters": CARE_HISTORY_FILTERS,
            "maintenance_tasks": MAINTENANCE_TASK_FILTERS,
            "selected_filter": category,
            "selected_task": task,
            "metric_label": metric_label,
            "format_number": _format_number,
            "page_url": lambda target_page: _history_url(category, task, target_page),
        },
    )


def _history_url(category: str, task: str | None, page: int | None = None) -> str:
    query: dict[str, str | int] = {"filter": category}
    if task:
        query["task"] = task
    if page and page > 1:
        query["page"] = page
    return f"?{urlencode(query)}"


def _format_number(value: Decimal | str | int | None) -> str:
    if value is None:
        return ""
    decimal_value = Decimal(str(value))
    return format(decimal_value.normalize(), "f")
