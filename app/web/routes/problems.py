from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.ports.problems import ProblemCreate
from app.application.problems.service import ProblemService
from app.application.tanks.service import TankService
from app.core.config import get_settings
from app.core.time import utc_now
from app.domain.problems import (
    PROBLEM_SEVERITY_LABELS,
    PROBLEM_STATUS_LABELS,
    PROBLEM_TYPE_LABELS,
)
from app.infrastructure.repositories.problems import SqlAlchemyProblemRepository
from app.infrastructure.repositories.tanks import SqlAlchemyTankRepository
from app.web.dependencies import AuthenticatedUser, get_db, preferences_for_user
from app.web.presentation import UserDisplay

router = APIRouter(prefix="/problems", tags=["problems"])
templates = Jinja2Templates(directory=get_settings().templates_dir)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def problem_index(request: Request, db: DbSession, current_user: AuthenticatedUser):
    service = ProblemService(SqlAlchemyProblemRepository(db))
    return _template_context(
        request,
        db,
        current_user,
        "problems/index.html",
        {
            "title": "Problems",
            "problems": service.list_problems(current_user.id),
            "problem_types": PROBLEM_TYPE_LABELS,
            "severity_labels": PROBLEM_SEVERITY_LABELS,
            "status_labels": PROBLEM_STATUS_LABELS,
        },
    )


@router.get("/new")
def new_problem(request: Request, db: DbSession, current_user: AuthenticatedUser):
    tanks = TankService(SqlAlchemyTankRepository(db)).list_tanks(current_user.id)
    selected_tank_id = _optional_int(request.query_params.get("tank_id"))
    if selected_tank_id is None and tanks:
        selected_tank_id = tanks[0].id
    started_at = utc_now()
    context_events = (
        ProblemService(SqlAlchemyProblemRepository(db)).list_tank_context(
            current_user.id,
            selected_tank_id,
            started_at,
        )
        if selected_tank_id
        else []
    )
    return _render_new_problem(
        request,
        db,
        current_user,
        tanks=tanks,
        selected_tank_id=selected_tank_id,
        context_events=context_events,
        form_values={"started_at": started_at.strftime("%Y-%m-%dT%H:%M")},
    )


@router.post("")
async def create_problem(request: Request, db: DbSession, current_user: AuthenticatedUser):
    form = await request.form()
    values = {key: str(value).strip() for key, value in form.items() if key != "event_ids"}
    service = ProblemService(SqlAlchemyProblemRepository(db))
    tanks = TankService(SqlAlchemyTankRepository(db)).list_tanks(current_user.id)
    tank_id = _optional_int(values.get("tank_id"))
    problem_type = values.get("problem_type", "")
    try:
        if tank_id is None:
            raise ValueError("Choose an aquarium")
        started_at = _optional_datetime(values.get("started_at")) or utc_now()
        title = values.get("title") or PROBLEM_TYPE_LABELS.get(problem_type, "")
        problem_id = service.create_problem(
            current_user.id,
            ProblemCreate(
                tank_id=tank_id,
                problem_type=problem_type,
                title=title,
                description=values.get("description") or None,
                severity=values.get("severity", "medium"),
                started_at=started_at,
                event_ids=tuple(
                    event_id
                    for value in form.getlist("event_ids")
                    if (event_id := _optional_int(str(value))) is not None
                ),
            ),
        )
        if problem_id is None:
            raise ValueError("Choose an available aquarium")
    except ValueError as exc:
        context_events = (
            service.list_tank_context(
                current_user.id,
                tank_id,
                _optional_datetime(values.get("started_at")) or utc_now(),
            )
            if tank_id
            else []
        )
        return _render_new_problem(
            request,
            db,
            current_user,
            tanks=tanks,
            selected_tank_id=tank_id,
            context_events=context_events,
            form_values=values,
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(f"/problems/{problem_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{problem_id}")
def problem_detail(
    request: Request,
    problem_id: int,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    detail = ProblemService(SqlAlchemyProblemRepository(db)).get_problem(
        current_user.id, problem_id
    )
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _template_context(
        request,
        db,
        current_user,
        "problems/detail.html",
        {
            "title": detail.problem.title,
            "detail": detail,
            "problem_types": PROBLEM_TYPE_LABELS,
            "severity_labels": PROBLEM_SEVERITY_LABELS,
            "status_labels": PROBLEM_STATUS_LABELS,
        },
    )


@router.post("/{problem_id}/status")
async def update_problem_status(
    request: Request,
    problem_id: int,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    service = ProblemService(SqlAlchemyProblemRepository(db))
    try:
        updated = service.update_status(
            current_user.id,
            problem_id,
            str(form.get("status", "")),
            str(form.get("resolution_notes", "")).strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RedirectResponse(f"/problems/{problem_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{problem_id}/events")
async def link_problem_events(
    request: Request,
    problem_id: int,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    form = await request.form()
    event_ids = tuple(
        event_id
        for value in form.getlist("event_ids")
        if (event_id := _optional_int(str(value))) is not None
    )
    if not ProblemService(SqlAlchemyProblemRepository(db)).link_events(
        current_user.id, problem_id, event_ids
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RedirectResponse(f"/problems/{problem_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{problem_id}/events/{event_id}/unlink")
def unlink_problem_event(
    problem_id: int,
    event_id: int,
    db: DbSession,
    current_user: AuthenticatedUser,
):
    if not ProblemService(SqlAlchemyProblemRepository(db)).unlink_event(
        current_user.id, problem_id, event_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RedirectResponse(f"/problems/{problem_id}", status_code=status.HTTP_303_SEE_OTHER)


def _render_new_problem(
    request: Request,
    db: Session,
    current_user,
    *,
    tanks,
    selected_tank_id: int | None,
    context_events,
    form_values: dict[str, str],
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    return _template_context(
        request,
        db,
        current_user,
        "problems/new.html",
        {
            "title": "Start a Problem",
            "tanks": tanks,
            "selected_tank_id": selected_tank_id,
            "context_events": context_events,
            "problem_types": PROBLEM_TYPE_LABELS,
            "severity_labels": PROBLEM_SEVERITY_LABELS,
            "form_values": form_values,
            "error": error,
        },
        status_code=status_code,
    )


def _template_context(
    request: Request,
    db: Session,
    current_user,
    template_name: str,
    context: dict,
    *,
    status_code: int = status.HTTP_200_OK,
):
    preferences = preferences_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "active_nav": "problems",
            "current_user": current_user,
            "preferences": preferences,
            "display": UserDisplay(preferences),
            **context,
        },
        status_code=status_code,
    )


def _optional_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
    except ValueError:
        return None
