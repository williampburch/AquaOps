from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.inventory.service import InventoryService
from app.application.ports.inventory import (
    InventoryQuantityChange,
    LivestockCreate,
    PlantCreate,
)
from app.application.ports.tanks import DoseLog, FeedingLog, MaintenanceLog, NoteLog
from app.application.tanks.service import TankService
from app.core.config import get_settings
from app.core.time import utc_now
from app.domain.enums import MaintenanceType
from app.domain.preferences import volume_from_liters, volume_to_liters
from app.domain.water import WATER_METRICS
from app.infrastructure.repositories.feature_flags import plant_care_is_active
from app.infrastructure.repositories.inventory import SqlAlchemyInventoryRepository
from app.infrastructure.repositories.tanks import SqlAlchemyTankRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/quick-log", tags=["quick-log"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]
QUICK_LOG_ACTIONS = {
    "water_change",
    "water_test",
    "maintenance",
    "feeding",
    "observation",
    "dose",
    "livestock_change",
    "plant_change",
    "photo",
}
OBSERVATION_PRESETS = (
    "Behavior change",
    "Health concern",
    "Algae update",
    "Plant growth",
    "Water clarity",
    "Spawning activity",
)
COMMON_FEEDING_UNITS = ("pinch", "pellet", "cube", "scoop", "portion")


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
    form_values = {}
    maintenance_type = request.query_params.get("maintenance_type")
    valid_maintenance_types = {
        item.value for item in MaintenanceType if item is not MaintenanceType.WATER_CHANGE
    }
    if action == "maintenance" and maintenance_type in valid_maintenance_types:
        form_values["maintenance_type"] = maintenance_type
    return _render_quick_log(
        request,
        db,
        current_user,
        action=action,
        tank_id=tank_id,
        saved=request.query_params.get("saved"),
        error=request.query_params.get("error"),
        form_values=form_values,
    )


@router.post("/livestock/add")
async def quick_add_livestock(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        tank_id = _required_tank_id(values)
        item_id = service.add_livestock(
            current_user.id,
            LivestockCreate(
                tank_id=tank_id,
                catalog_entry_id=_optional_int(values.get("catalog_entry_id")),
                common_name=values.get("common_name") or None,
                species=values.get("species") or None,
                quantity=_optional_int(values.get("quantity")) or 1,
                sex=None,
                notes=values.get("notes") or None,
                acquired_on=_optional_date(values.get("occurred_on")),
            ),
        )
        if item_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="livestock_change",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _saved_redirect("livestock_change", tank_id)


@router.post("/livestock/change")
async def quick_change_livestock(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        tank_id = _required_tank_id(values)
        item_id = _required_int(values.get("item_id"), "Choose livestock to update.")
        _require_item_in_tank(service.get_livestock(current_user.id).items, item_id, tank_id)
        changed = service.change_livestock_quantity(
            current_user.id,
            item_id,
            InventoryQuantityChange(
                direction=values.get("direction", ""),
                quantity=_required_int(values.get("quantity"), "Enter a quantity."),
                reason=values.get("reason") or None,
                notes=values.get("notes") or None,
                occurred_on=_optional_date(values.get("occurred_on")) or date.today(),
            ),
        )
        if not changed:
            raise ValueError("That livestock entry is no longer available.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="livestock_change",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _saved_redirect("livestock_change", tank_id)


@router.post("/plants/add")
async def quick_add_plant(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        tank_id = _required_tank_id(values)
        item_id = service.add_plant(
            current_user.id,
            PlantCreate(
                tank_id=tank_id,
                catalog_entry_id=_optional_int(values.get("catalog_entry_id")),
                common_name=values.get("common_name") or None,
                species=values.get("species") or None,
                quantity=_optional_int(values.get("quantity")) or 1,
                notes=values.get("notes") or None,
                planted_on=_optional_date(values.get("occurred_on")),
            ),
        )
        if item_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="plant_change",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _saved_redirect("plant_change", tank_id)


@router.post("/plants/change")
async def quick_change_plant(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    values = _form_values(form)
    tank_id = None
    service = InventoryService(SqlAlchemyInventoryRepository(db))
    try:
        tank_id = _required_tank_id(values)
        item_id = _required_int(values.get("item_id"), "Choose a plant to update.")
        _require_item_in_tank(service.get_plants(current_user.id).items, item_id, tank_id)
        changed = service.change_plant_quantity(
            current_user.id,
            item_id,
            InventoryQuantityChange(
                direction=values.get("direction", ""),
                quantity=_required_int(values.get("quantity"), "Enter a quantity."),
                reason=values.get("reason") or None,
                notes=values.get("notes") or None,
                occurred_on=_optional_date(values.get("occurred_on")) or date.today(),
            ),
        )
        if not changed:
            raise ValueError("That plant entry is no longer available.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="plant_change",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _saved_redirect("plant_change", tank_id)


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
                conditioner_name=values.get("conditioner_name") or None,
                nitrate_before=_optional_decimal(values.get("nitrate_before")),
                nitrate_after=_optional_decimal(values.get("nitrate_after")),
                tds_before=_optional_decimal(values.get("tds_before")),
                tds_after=_optional_decimal(values.get("tds_after")),
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
        food_names = _parse_food_names(
            values.get("food_names"),
            values.get("food_name"),
        )
        event_id = service.log_feeding(
            current_user.id,
            tank_id,
            FeedingLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                food_name=food_names[0] if len(food_names) == 1 else "",
                amount=_optional_decimal(values.get("amount")),
                unit=values.get("unit") or None,
                target_livestock=values.get("target_livestock") or None,
                notes=values.get("notes") or None,
                food_names=food_names,
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
                food_names=previous.food_names,
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


@router.post("/observation")
async def log_observation(
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
        event_id = service.log_note(
            current_user.id,
            tank_id,
            NoteLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                title=values.get("title", ""),
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
            action="observation",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("observation", tank_id)


@router.post("/dose")
async def log_dose(
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
        amount = _optional_decimal(values.get("dose_amount"))
        if amount is None:
            raise ValueError("Dose amount is required")
        event_id = service.log_dose(
            current_user.id,
            tank_id,
            DoseLog(
                occurred_at=_optional_datetime(values.get("occurred_at")) or utc_now(),
                product_name=values.get("product_name", ""),
                dose_amount=amount,
                dose_unit=values.get("dose_unit", ""),
                location=values.get("location") or None,
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
            action="dose",
            tank_id=tank_id,
            error=str(exc),
            form_values=values,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("dose", tank_id)


@router.post("/dose/repeat")
async def repeat_dose(
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
        if context is None or context.last_dose is None:
            raise ValueError("Log a fertilizer dose first before using repeat last dose.")
        previous = context.last_dose
        event_id = service.log_dose(
            current_user.id,
            tank_id,
            DoseLog(
                occurred_at=utc_now(),
                product_name=previous.product_name,
                dose_amount=previous.dose_amount,
                dose_unit=previous.dose_unit,
                location=previous.location,
            ),
        )
        if event_id is None:
            raise ValueError("Choose an available aquarium.")
    except ValueError as exc:
        return _render_quick_log(
            request,
            db,
            current_user,
            action="dose",
            tank_id=tank_id,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _saved_redirect("dose", tank_id)


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
    inventory_service = InventoryService(SqlAlchemyInventoryRepository(db))
    livestock_items = []
    plant_items = []
    if selected_id is not None:
        if preferences.enable_livestock:
            livestock_items = [
                item
                for item in inventory_service.get_livestock(current_user.id).items
                if item.tank_id == selected_id
            ]
        if preferences.enable_plants:
            plant_items = [
                item
                for item in inventory_service.get_plants(current_user.id).items
                if item.tank_id == selected_id
            ]
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
            "recent_conditioner_names": (
                quick_context.recent_conditioner_names if quick_context else []
            ),
            "latest_readings": latest_readings,
            "recent_equipment_names": (
                quick_context.recent_equipment_names if quick_context else []
            ),
            "last_feeding": quick_context.last_feeding if quick_context else None,
            "recent_food_names": quick_context.recent_food_names if quick_context else [],
            "feeding_unit_options": _unique_options(
                [
                    *(quick_context.recent_feeding_units if quick_context else []),
                    *COMMON_FEEDING_UNITS,
                ]
            ),
            "feeding_target_options": _unique_options(
                [
                    "Whole tank",
                    *(quick_context.recent_feeding_targets if quick_context else []),
                ]
            ),
            "recent_observation_titles": (
                quick_context.recent_observation_titles if quick_context else []
            ),
            "observation_presets": OBSERVATION_PRESETS,
            "last_dose": quick_context.last_dose if quick_context else None,
            "recent_dose_products": (quick_context.recent_dose_products if quick_context else []),
            "recent_dose_locations": (quick_context.recent_dose_locations if quick_context else []),
            "dose_enabled": preferences.enable_plants
            and plant_care_is_active(db, current_user.id, preferences.plant_care_mode),
            "livestock_enabled": preferences.enable_livestock,
            "plants_enabled": preferences.enable_plants,
            "livestock_items": livestock_items,
            "plant_items": plant_items,
            "livestock_catalog": (
                inventory_service.list_livestock_catalog() if preferences.enable_livestock else []
            ),
            "plant_catalog": (
                inventory_service.list_plant_catalog() if preferences.enable_plants else []
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


def _required_int(value: str | None, message: str) -> int:
    try:
        parsed = _optional_int(value)
    except ValueError as exc:
        raise ValueError(message) from exc
    if parsed is None:
        raise ValueError(message)
    return parsed


def _require_item_in_tank(items, item_id: int, tank_id: int) -> None:
    if not any(item.id == item_id and item.tank_id == tank_id for item in items):
        raise ValueError("Choose an active entry from this aquarium.")


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


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


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
    conditioner_name = values.get("conditioner_name", "").strip()
    if conditioner_name:
        details.append(f"Conditioner: {conditioner_name}")
    details.extend(
        reading
        for reading in (
            _before_after_note(
                "Nitrate",
                values.get("nitrate_before"),
                values.get("nitrate_after"),
                "ppm",
            ),
            _before_after_note(
                "TDS",
                values.get("tds_before"),
                values.get("tds_after"),
                "ppm",
            ),
        )
        if reading
    )
    notes = values.get("notes", "").strip()
    if details and notes:
        return f"{', '.join(details)}. {notes}"
    if details:
        return ", ".join(details)
    return notes or None


def _before_after_note(
    label: str,
    before: str | None,
    after: str | None,
    unit: str,
) -> str | None:
    if before and after:
        return f"{label} {before} to {after} {unit}"
    if before:
        return f"{label} before {before} {unit}"
    if after:
        return f"{label} after {after} {unit}"
    return None


def _parse_food_names(
    serialized_foods: str | None,
    typed_food: str | None,
) -> tuple[str, ...]:
    foods: list[object] = []
    if serialized_foods:
        try:
            decoded = json.loads(serialized_foods)
        except json.JSONDecodeError:
            decoded = []
        if isinstance(decoded, list):
            foods.extend(decoded)
    if typed_food:
        foods.append(typed_food)

    unique = []
    normalized = set()
    for food in foods:
        if not isinstance(food, str):
            continue
        name = food.strip()
        key = name.casefold()
        if name and key not in normalized:
            unique.append(name)
            normalized.add(key)
    return tuple(unique)


def _unique_options(values: list[str]) -> list[str]:
    options = []
    seen = set()
    for value in values:
        normalized = value.casefold()
        if value and normalized not in seen:
            options.append(value)
            seen.add(normalized)
    return options
