from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.preferences.service import UserPreferenceService
from app.core.config import get_settings
from app.domain.preferences import UserPreferences
from app.infrastructure.repositories.preferences import SqlAlchemyUserPreferenceRepository
from app.web.dependencies import AuthenticatedUser, get_db
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory=get_settings().templates_dir)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def settings_index(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = UserPreferenceService(SqlAlchemyUserPreferenceRepository(db))
    preferences = service.get_preferences(current_user.id)
    return templates.TemplateResponse(
        request,
        "settings/index.html",
        {
            "title": "Settings",
            "active_nav": "settings",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("")
async def save_settings(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    preferences = UserPreferences(
        unit_system=_form_choice(form, "unit_system", "us"),
        volume_unit=_form_choice(form, "volume_unit", "gallon"),
        temperature_unit=_form_choice(form, "temperature_unit", "F"),
        date_format=_form_choice(form, "date_format", "mdy"),
        dashboard_density=_form_choice(form, "dashboard_density", "comfortable"),
        advanced_mode=_form_bool(form, "advanced_mode"),
        reminder_window_days=_form_int(form, "reminder_window_days", 14),
        enable_livestock=_form_bool(form, "enable_livestock"),
        enable_plants=_form_bool(form, "enable_plants"),
        enable_reports=_form_bool(form, "enable_reports"),
        enable_notifications=_form_bool(form, "enable_notifications"),
        enable_advanced_water=_form_bool(form, "enable_advanced_water"),
        plant_care_mode=_form_choice(form, "plant_care_mode", "auto"),
    )
    service = UserPreferenceService(SqlAlchemyUserPreferenceRepository(db))
    service.save_preferences(current_user.id, preferences)
    return RedirectResponse("/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)


def _form_choice(form, key: str, default: str) -> str:
    value = form.get(key)
    return str(value).strip() if value is not None else default


def _form_bool(form, key: str) -> bool:
    return form.get(key) == "on"


def _form_int(form, key: str, default: int) -> int:
    value = form.get(key)
    if value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default
