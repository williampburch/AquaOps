from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.web.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(db: DbSession):
    return _readiness_response(db)


@router.get("/health")
def compatibility_health_check(db: DbSession):
    """Compatibility alias for database-aware readiness."""
    return _readiness_response(db)


def _readiness_response(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable"},
        )
    return {"status": "ok"}
