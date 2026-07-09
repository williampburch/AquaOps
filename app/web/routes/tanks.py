from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.ports.tanks import TankCreate
from app.application.tanks.service import TankService
from app.core.config import get_settings
from app.core.time import utc_now
from app.domain.water import WATER_METRICS
from app.infrastructure.repositories.tanks import SqlAlchemyTankRepository
from app.web.dependencies import AuthenticatedUser, get_db

router = APIRouter(prefix="/tanks", tags=["tanks"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def list_tanks(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = TankService(SqlAlchemyTankRepository(db))
    return templates.TemplateResponse(
        request,
        "tanks/index.html",
        {
            "title": "Tanks",
            "active_nav": "tanks",
            "current_user": current_user,
            "tanks": service.list_tanks(current_user.id),
        },
    )


@router.get("/new")
def new_tank_form(request: Request, current_user: AuthenticatedUser):
    return templates.TemplateResponse(
        request,
        "tanks/new.html",
        {
            "title": "New Tank",
            "active_nav": "tanks",
            "current_user": current_user,
            "error": None,
        },
    )


@router.post("")
async def create_tank(
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = TankService(SqlAlchemyTankRepository(db))
    try:
        tank_id = service.create_tank(
            current_user.id,
            TankCreate(
                name=_form_text(form, "name") or "",
                tank_type=_form_text(form, "tank_type") or "freshwater",
                volume_liters=_optional_decimal(_form_text(form, "volume_liters")),
                started_on=_optional_date(_form_text(form, "started_on")),
                description=_form_text(form, "description"),
                lighting=_form_text(form, "lighting"),
                filtration=_form_text(form, "filtration"),
                substrate=_form_text(form, "substrate"),
            ),
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "tanks/new.html",
            {
                "title": "New Tank",
                "active_nav": "tanks",
                "current_user": current_user,
                "error": str(exc),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(f"/tanks/{tank_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{tank_id}")
def tank_detail(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    service = TankService(SqlAlchemyTankRepository(db))
    tank = service.get_tank_detail(current_user.id, tank_id)
    if tank is None:
        return RedirectResponse("/tanks", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request,
        "tanks/detail.html",
        {
            "title": tank.name,
            "active_nav": "tanks",
            "current_user": current_user,
            "tank": tank,
            "water_metrics": WATER_METRICS,
            "chart_payload": _chart_payload(tank.chart_series),
            "error": None,
        },
    )


@router.post("/{tank_id}/water-tests")
async def log_water_test(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = TankService(SqlAlchemyTankRepository(db))
    try:
        measurements = {}
        for metric in WATER_METRICS:
            value = _optional_decimal(_form_text(form, metric.key.value))
            if value is not None:
                measurements[metric.key.value] = value

        event_id = service.log_water_test(
            user_id=current_user.id,
            tank_id=tank_id,
            occurred_at=_optional_datetime(_form_text(form, "occurred_at")) or utc_now(),
            measurements=measurements,
            notes=_form_text(form, "notes"),
        )
    except ValueError:
        event_id = None

    if event_id is None:
        return RedirectResponse(f"/tanks/{tank_id}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(f"/tanks/{tank_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{tank_id}/targets")
async def update_targets(
    tank_id: int,
    request: Request,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    try:
        raw_targets = {}
        for metric in WATER_METRICS:
            metric_key = metric.key.value
            raw_targets[metric_key] = (
                _optional_decimal(_form_text(form, f"{metric_key}_min")),
                _optional_decimal(_form_text(form, f"{metric_key}_max")),
                _form_text(form, f"{metric_key}_unit") or metric.default_unit,
            )

        service = TankService(SqlAlchemyTankRepository(db))
        service.update_targets(current_user.id, tank_id, raw_targets)
    except ValueError:
        pass
    return RedirectResponse(f"/tanks/{tank_id}", status_code=status.HTTP_303_SEE_OTHER)


def _form_text(form, key: str) -> str | None:
    value = form.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {value}") from exc


def _optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)


def _chart_payload(chart_series):
    return [
        {
            "metric": series.metric_key,
            "label": series.label,
            "unit": series.unit,
            "labels": [point.occurred_at for point in series.points],
            "values": [point.value for point in series.points],
        }
        for series in chart_series
    ]
