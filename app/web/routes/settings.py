from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.web.dependencies import AuthenticatedUser

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory=get_settings().templates_dir)


@router.get("")
def settings_index(
    request: Request,
    current_user: AuthenticatedUser,
):
    automation_cards = [
        {
            "title": "Water Alerts",
            "detail": "Ammonia, nitrite, nitrate, pH, temperature, KH, GH, and TDS thresholds.",
            "status": "Planned",
        },
        {
            "title": "Care Schedules",
            "detail": "Feeding, water changes, filter cleaning, trimming, and glass cleaning.",
            "status": "Planned",
        },
        {
            "title": "Fertilizer Cadence",
            "detail": "Root tabs, Flourish, Easy Green, and custom fertilizer intervals.",
            "status": "Active soon",
        },
        {
            "title": "Feature Modules",
            "detail": "Plants, livestock, photos, reports, reminders, and advanced analytics.",
            "status": "Planned",
        },
    ]
    return templates.TemplateResponse(
        request,
        "settings/index.html",
        {
            "title": "Settings",
            "active_nav": "settings",
            "current_user": current_user,
            "automation_cards": automation_cards,
        },
    )
