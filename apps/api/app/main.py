"""FastAPI application bootstrap."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, Response

from apps.api.app.api.assets import router as assets_router
from apps.api.app.api.generation import router as generation_router
from apps.api.app.api.projects import router as projects_router
from apps.api.app.api.scene import router as scene_router
from apps.api.app.api.trajectory import render_router, router as trajectory_router
from apps.api.app.api.viewer import router as viewer_router
from apps.api.app.config import get_settings

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none">
<defs>
  <linearGradient id="bg" x1="14" y1="10" x2="81" y2="86" gradientUnits="userSpaceOnUse">
    <stop stop-color="#17365D"/>
    <stop offset="1" stop-color="#091321"/>
  </linearGradient>
  <linearGradient id="glow" x1="24" y1="22" x2="68" y2="71" gradientUnits="userSpaceOnUse">
    <stop stop-color="#6EE7C8"/>
    <stop offset="1" stop-color="#4DD2FF"/>
  </linearGradient>
</defs>
<rect x="8" y="8" width="80" height="80" rx="24" fill="url(#bg)"/>
<path d="M31 67V29H49C62 29 71 36 71 48C71 60 62 67 49 67H31Z" fill="#F2F7FF"/>
<path d="M42 39V57H49C55.8 57 60 53.5 60 48C60 42.5 55.8 39 49 39H42Z" fill="url(#glow)"/>
</svg>
"""


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", docs_url=None, redoc_url=None)

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> Response:
        return Response(content=FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/docs", include_in_schema=False)
    def custom_docs() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{settings.app_name} Docs",
            swagger_favicon_url="/favicon.svg",
        )

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(projects_router)
    app.include_router(assets_router)
    app.include_router(generation_router)
    app.include_router(scene_router)
    app.include_router(trajectory_router)
    app.include_router(render_router)
    app.include_router(viewer_router)
    return app


app = create_app()
