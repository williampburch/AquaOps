from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

router = APIRouter(tags=["pwa"])


@router.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest(request: Request) -> FileResponse:
    return FileResponse(
        request.app.state.settings.static_dir / "pwa" / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/service-worker.js", include_in_schema=False)
def service_worker(request: Request) -> FileResponse:
    return FileResponse(
        request.app.state.settings.static_dir / "pwa" / "service-worker.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )


@router.get("/offline", include_in_schema=False)
def offline_fallback(request: Request) -> FileResponse:
    return FileResponse(
        request.app.state.settings.static_dir / "pwa" / "offline.html",
        media_type="text/html",
        headers={"Cache-Control": "public, max-age=3600"},
    )
