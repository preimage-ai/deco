"""FastAPI application bootstrap."""

from __future__ import annotations

from fastapi import FastAPI

from apps.api.app.api.assets import router as assets_router
from apps.api.app.api.projects import router as projects_router
from apps.api.app.api.scene import router as scene_router
from apps.api.app.api.trajectory import router as trajectory_router
from apps.api.app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(projects_router)
    app.include_router(assets_router)
    app.include_router(scene_router)
    app.include_router(trajectory_router)
    return app


app = create_app()
