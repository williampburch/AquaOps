from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
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
CARE_QUEUE_STATUSES = {"overdue", "due_today", "upcoming"}
QUICK_LOG_LABELS = {
    "water_change": "Log water change",
    "water_test": "Log water test",
    "feeding": "Log feeding",
    "maintenance": "Log maintenance",
    "dose": "Log dose",
}


@router.get("")
def notifications_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = NotificationService(SqlAlchemyNotificationRepository(db))
    preferences = preferences_for_user(db, current_user)
    status_filter = request.query_params.get("status")
    if status_filter not in CARE_QUEUE_STATUSES:
        status_filter = None
    snapshot = service.get_notifications(
        current_user.id,
        preferences.reminder_window_days,
        preferences.plant_care_mode,
    )
    visible_items = (
        [item for item in snapshot.items if item.status == status_filter]
        if status_filter
        else snapshot.items
    )
    return templates.TemplateResponse(
        request,
        "notifications/index.html",
        {
            "title": "Notifications",
            "active_nav": "notifications",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "snapshot": snapshot,
            "visible_items": visible_items,
            "status_filter": status_filter,
            "quick_log_labels": QUICK_LOG_LABELS,
        },
    )


@router.post("/{reminder_id}/complete")
def complete_reminder(
    reminder_id: int,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = NotificationService(SqlAlchemyNotificationRepository(db))
    service.complete_reminder(current_user.id, reminder_id)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/{reminder_id}/snooze")
async def snooze_reminder(
    reminder_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    try:
        days = int(str(form.get("days") or "1"))
        NotificationService(SqlAlchemyNotificationRepository(db)).snooze_reminder(
            current_user.id,
            reminder_id,
            days,
        )
    except ValueError:
        pass
    return RedirectResponse("/notifications", status_code=303)
