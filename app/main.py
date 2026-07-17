from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine
from app.web.routes import (
    auth,
    care_plans,
    dashboard,
    events,
    guide,
    health,
    inventory,
    notifications,
    photos,
    problems,
    pwa,
    quick_log,
    reports,
    tank_history,
    tanks,
)
from app.web.routes import (
    settings as settings_routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.media_root.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=app.state.database_engine)
    yield


def create_app(
    settings: Settings | None = None,
    *,
    database_engine: Engine | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.database_engine = database_engine or engine
    app.state.static_version = str(
        max(
            (
                path.stat().st_mtime_ns
                for path in app_settings.static_dir.rglob("*")
                if path.is_file()
            ),
            default=0,
        )
    )

    app.mount(
        "/static",
        StaticFiles(directory=app_settings.static_dir),
        name="static",
    )

    app.include_router(health.router)
    app.include_router(pwa.router)
    app.include_router(auth.router)
    app.include_router(care_plans.router)
    app.include_router(tank_history.router)
    app.include_router(tanks.router)
    app.include_router(inventory.router)
    app.include_router(events.router)
    app.include_router(notifications.router)
    app.include_router(photos.router)
    app.include_router(problems.router)
    app.include_router(quick_log.router)
    app.include_router(reports.router)
    app.include_router(settings_routes.router)
    app.include_router(guide.router)
    app.include_router(dashboard.router)
    return app


app = create_app()
