"""Tests for FastAPI app bootstrap and route registration."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from apps.api.app.deps import get_da3_generation_service, get_repo
from apps.api.app.main import create_app


def test_app_registers_core_routes(tmp_path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    get_da3_generation_service.cache_clear()

    app = create_app()
    routes = {route.path for route in app.routes}

    assert "/healthz" in routes
    assert "/projects" in routes
    assert "/generation/create-gsplat" in routes
    assert "/projects/{project_id}/assets/upload-room" in routes
    assert "/projects/{project_id}/assets/upload-object" in routes
    assert "/projects/{project_id}/assets/{asset_id}/download" in routes
    assert "/projects/{project_id}/objects" in routes
    assert "/projects/{project_id}/trajectories" in routes
    assert "/projects/{project_id}/trajectories/{trajectory_id}/capture-keyframe" in routes
    assert "/projects/{project_id}/trajectories/{trajectory_id}/render" in routes
    assert "/projects/{project_id}/renders/{filename}" in routes
    assert "/projects/{project_id}/renders/{filename}/enhance" in routes
    assert "/projects/{project_id}/viewer/select-object" in routes
    assert "/projects/{project_id}/viewer/save-object" in routes


def test_docs_and_favicon_have_custom_branding(tmp_path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    get_da3_generation_service.cache_clear()

    client = TestClient(create_app())

    favicon_response = client.get("/favicon.svg")
    assert favicon_response.status_code == 200
    assert favicon_response.headers["content-type"] == "image/svg+xml"
    assert "<svg" in favicon_response.text

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "Deco Room GSplat Studio Docs" in docs_response.text
    assert "/favicon.svg" in docs_response.text
