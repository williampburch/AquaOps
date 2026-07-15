from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.care_plans.service import CarePlanService
from app.application.ports.care_plans import CareScheduleUpdate
from app.core.config import get_settings
from app.domain.care_plans import CARE_TASKS, WEEKDAY_LABELS
from app.domain.care_profiles import CARE_PROFILES, care_profile
from app.infrastructure.repositories.care_plans import SqlAlchemyCarePlanRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/tanks", tags=["care-plans"])
templates = Jinja2Templates(directory=get_settings().templates_dir)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{tank_id}/care-plan")
def care_plan_editor(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    return _render_editor(request, db, current_user, tank_id)


@router.post("/{tank_id}/care-plan/profile")
async def apply_care_profile(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    try:
        updated = CarePlanService(SqlAlchemyCarePlanRepository(db)).apply_profile(
            current_user.id,
            tank_id,
            _text(form, "profile_key") or "",
            _text(form, "strategy") or "",
            confirmed="confirm_start_over" in form,
        )
        if not updated:
            return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        return _render_editor(
            request,
            db,
            current_user,
            tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/tanks/{tank_id}/care-plan?saved=profile",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{tank_id}/care-plan/schedules")
async def save_advanced_care_plan(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = CarePlanService(SqlAlchemyCarePlanRepository(db))
    plan = service.get_care_plan(current_user.id, tank_id)
    if plan is None:
        return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)
    schedules = []
    for schedule in plan.schedules:
        prefix = f"schedule__{schedule.config_key}__"
        schedules.append(
            CareScheduleUpdate(
                config_key=schedule.config_key,
                config_type=schedule.config_type,
                label=(
                    _text(form, f"{prefix}label") or schedule.label
                    if schedule.config_type == "custom"
                    else None
                ),
                enabled=f"{prefix}enabled" in form,
                interval_days=_optional_int(_text(form, f"{prefix}interval_days")),
                schedule_mode=_text(form, f"{prefix}schedule_mode") or "scheduled",
                preferred_weekday=_optional_int(_text(form, f"{prefix}preferred_weekday")),
                start_date=_optional_date(_text(form, f"{prefix}start_date")),
                reminders_enabled=f"{prefix}reminders_enabled" in form,
                notes=_text(form, f"{prefix}notes"),
            )
        )
    try:
        service.save_advanced_plan(current_user.id, tank_id, schedules)
    except ValueError as exc:
        return _render_editor(
            request,
            db,
            current_user,
            tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/tanks/{tank_id}/care-plan?saved=advanced",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{tank_id}/care-plan/custom-tasks")
async def add_custom_care_task(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    try:
        added = CarePlanService(SqlAlchemyCarePlanRepository(db)).add_custom_task(
            current_user.id,
            tank_id,
            CareScheduleUpdate(
                config_key="new_custom",
                config_type="custom",
                label=_text(form, "label"),
                enabled=True,
                interval_days=_optional_int(_text(form, "interval_days")),
                schedule_mode=_text(form, "schedule_mode") or "scheduled",
                preferred_weekday=_optional_int(_text(form, "preferred_weekday")),
                start_date=_optional_date(_text(form, "start_date")),
                reminders_enabled="reminders_enabled" in form,
                notes=_text(form, "notes"),
            ),
        )
        if not added:
            return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        return _render_editor(
            request,
            db,
            current_user,
            tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/tanks/{tank_id}/care-plan?saved=custom",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _render_editor(
    request: Request,
    db: Session,
    current_user,
    tank_id: int,
    *,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    plan = CarePlanService(SqlAlchemyCarePlanRepository(db)).get_care_plan(current_user.id, tank_id)
    if plan is None:
        return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "care_plans/editor.html",
        {
            "title": f"{plan.tank_name} Care Plan",
            "active_nav": "tanks",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            "plan": plan,
            "current_profile": care_profile(plan.care_profile),
            "care_profiles": [
                profile
                for profile in CARE_PROFILES.values()
                if not profile.advanced and profile.key != "custom"
            ],
            "task_definitions": CARE_TASKS,
            "weekday_labels": WEEKDAY_LABELS,
            "error": error,
            "saved": request.query_params.get("saved"),
        },
        status_code=status_code,
    )


def _text(form, key: str) -> str | None:
    value = form.get(key)
    if value is None:
        return None
    return str(value).strip() or None


def _optional_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _optional_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None
