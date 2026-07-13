from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.ports.tanks import FeedingLog, MaintenanceLog
from app.application.tanks.service import TankService
from app.core.config import get_settings
from app.core.time import utc_now
from app.domain.enums import MaintenanceType
from app.domain.preferences import volume_from_liters, volume_to_liters
from app.domain.water import WATER_METRICS
from app.infrastructure.repositories.tanks import SqlAlchemyTankRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/quick-log", tags=["quick-log"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]
QUICK_LOG_ACTIONS = {"water_change", "water_test", "maintenance", "feeding"}


@router.get("")
def quick_log(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    action = request.query_params.get("action", "water_change")
    if action not in QUICK_LOG_ACTIONS:
        action = "water_change"
    tank_id = _query_int(request.query_params.get("tank_id"))
    return _render_quick_log(
        request,
        db,
        current_user,
        action=action,
        tank_id=tank_id,
        saved=request.query_params.get("saved"),
    )


@router.post("/water-change")
async def log_water_change(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))
    preferences = preferences_for_user(db, current_user)

    try:
        tank_id = _required_tank_id(values)
        tank = service.get_tank_detail(current_user.id, tank_id)
        if tank is None:
            raise ValueError("Choose an aquarium to log this water change.")
        percentage = _optional_decimal(values.get("percentage"))
        volume = _optional_decimal(values.get("volume_changed"))
        if percentage is not None:
            if percentage <= 0 or percentage > 100:
                raise ValueError("Water change percentage must be between 1 and 100.")
            if tank.volume_liters is None:
                raise ValueError("Add the tank volume before logging a percentage-based change.")
            volume_liters = tank.volume_liters * percentage / Decimal("100")
        elif volume is not None:
            if volume <= 0:
                raise ValueError("Water change volume must be greater than zero.")
            volume_liters = volume_to_liters(volume, preferences.volume_unit)
        else:
            raise ValueError("Enter a percentage or volume changed.")

        notes = _water_change_notes(values)
        event_id = service.log_maintenance(
            current_user.id,
            tank_id,
            MaintenanceLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                maintenance_type=MaintenanceType.WATER_CHANGE.value,
                duration_minutes=_optional_int(values.get("duration_minutes")),
                volume_changed_liters=volume_liters,
                equipment_name=None,
                notes=notes,
            ),
        )
        if event_id is None:
            raise ValueError("That aquarium is not available.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="water_change",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("water_change", tank_id)


@router.post("/water-test")
async def log_water_test(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))

    try:
        tank_id = _required_tank_id(values)
        measurements = {
            metric.key.value: value
            for metric in WATER_METRICS
            if (value := _optional_decimal(values.get(metric.key.value))) is not None
        }
        event_id = service.log_water_test(
            current_user.id,
            tank_id,
            _optional_datetime(values.get("occurred_at")) or utc_now(),
            measurements,
            values.get("notes"),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="water_test",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("water_test", tank_id)


@router.post("/maintenance")
async def log_maintenance(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))

    try:
        tank_id = _required_tank_id(values)
        maintenance_type = values.get("maintenance_type") or ""
        if maintenance_type == MaintenanceType.WATER_CHANGE.value:
            raise ValueError("Use the Water Change tab for water changes.")
        event_id = service.log_maintenance(
            current_user.id,
            tank_id,
            MaintenanceLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                maintenance_type=maintenance_type,
                duration_minutes=_optional_int(values.get("duration_minutes")),
                equipment_name=values.get("equipment_name"),
                notes=values.get("notes"),
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="maintenance",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("maintenance", tank_id)


@router.post("/feeding")
async def log_feeding(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))

    try:
        tank_id = _required_tank_id(values)
        event_id = service.log_feeding(
            current_user.id,
            tank_id,
            FeedingLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                food_name=values.get("food_name", ""),
                amount=_optional_decimal(values.get("amount")),
                unit=values.get("unit") or None,
                target_livestock=values.get("target_livestock") or None,
                notes=values.get("notes") or None,
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="feeding",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("feeding", tank_id)


@router.post("/feeding/repeat")
async def repeat_feeding(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))

    try:
        tank_id = _required_tank_id(values)
        context = service.get_quick_log_context(current_user.id, tank_id)
        if context is None or context.last_feeding is None:
            raise ValueError("Log a feeding first before using repeat last feeding.")
        previous = context.last_feeding
        event_id = service.log_feeding(
            current_user.id,
            tank_id,
            FeedingLog(
                occurred_at=utc_now(),
                food_name=previous.food_name,
                amount=previous.amount,
                unit=previous.unit,
                target_livestock=previous.target_livestock,
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="feeding",
            tank_id=tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("feeding", tank_id)


@router.post("/feeding/skip")
async def skip_feeding(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = TankService(SqlAlchemyTankRepository(db))

    try:
        tank_id = _required_tank_id(values)
        event_id = service.log_feeding(
            current_user.id,
            tank_id,
            FeedingLog(
                occurred_at=utc_now(),
                food_name="",
                skipped=True,
                skip_reason=values.get("skip_reason") or None,
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="feeding",
            tank_id=tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("feeding", tank_id)


def _render_quick_log(
    request: Request,
    db: Session,
    current_user,
    *,
    action: str,
    tank_id: int | None,
    saved: str | None = None,
    error: str | None = None,
    form_values: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
):
    service = TankService(SqlAlchemyTankRepository(db))
    tanks = service.list_tanks(current_user.id)
    selected_id = tank_id if any(tank.id == tank_id for tank in tanks) else None
    if selected_id is None and tanks:
        selected_id = tanks[0].id
    selected_tank = (
        service.get_tank_detail(current_user.id, selected_id) if selected_id is not None else None
    )
    preferences = preferences_for_user(db, current_user)
    display = UserDisplay(preferences)
    water_change_schedule = None
    quick_context = None
    latest_readings = {}
    if selected_tank:
        water_change_schedule = next(
            (
                config
                for config in selected_tank.maintenance_configs
                if config.config_type == "water_change"
            ),
            None,
        )
        quick_context = service.get_quick_log_context(current_user.id, selected_tank.id)
        latest_readings = {reading.metric_key: reading for reading in selected_tank.latest_readings}
    last_water_change_volume = (
        volume_from_liters(quick_context.last_water_change_liters, preferences.volume_unit)
        if quick_context
        else None
    )
    return templates.TemplateResponse(
        request,
        "quick_log/index.html",
        {
            "title": "Quick Log",
            "active_nav": "quick_log",
            "current_user": current_user,
            "preferences": preferences,
            "display": display,
            "tanks": tanks,
            "selected_tank": selected_tank,
            "selected_tank_id": selected_id,
            "action": action,
            "saved": saved if saved in QUICK_LOG_ACTIONS else None,
            "error": error,
            "form_values": form_values or {},
            "water_metrics": display.visible_water_items(WATER_METRICS),
            "water_change_schedule": water_change_schedule,
            "last_water_change_volume": last_water_change_volume,
            "latest_readings": latest_readings,
            "recent_equipment_names": (
                quick_context.recent_equipment_names if quick_context else []
            ),
            "last_feeding": quick_context.last_feeding if quick_context else None,
            "recent_food_names": quick_context.recent_food_names if quick_context else [],
            "recent_feeding_targets": (
                quick_context.recent_feeding_targets if quick_context else []
            ),
            "maintenance_types": [
                (item.value, item.value.replace("_", " ").title())
                for item in MaintenanceType
                if item is not MaintenanceType.WATER_CHANGE
            ],
        },
        status_code=status_code,
    )


def _saved_redirect(action: str, tank_id: int) -> RedirectResponse:
    query = urlencode({"action": action, "tank_id": tank_id, "saved": action})
    return RedirectResponse(f"/quick-log?{query}", status_code=status.HTTP_303_SEE_OTHER)


def _required_tank_id(values: dict[str, str]) -> int:
    tank_id = _optional_int(values.get("tank_id"))
    if tank_id is None:
        raise ValueError("Choose an aquarium.")
    return tank_id


def _form_values(form) -> dict[str, str]:
    return {str(key): str(value).strip() for key, value in form.items()}


def _optional_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid number.") from exc


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None


def _query_int(value: str | None) -> int | None:
    try:
        return _optional_int(value)
    except ValueError:
        return None


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)


def _water_change_notes(values: dict[str, str]) -> str | None:
    details = [
        label
        for key, label in (
            ("conditioner_used", "Conditioner used"),
            ("substrate_vacuum", "Substrate vacuumed"),
            ("glass_cleaned", "Glass cleaned"),
            ("filter_cleaned", "Filter cleaned"),
            ("temperature_matched", "Temperature matched"),
        )
        if values.get(key)
    ]
    notes = values.get("notes", "").strip()
    if details and notes:
        return f"{', '.join(details)}. {notes}"
    if details:
        return ", ".join(details)
    return notes or None
