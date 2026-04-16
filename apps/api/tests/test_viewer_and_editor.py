"""Tests for viewer-related app wiring."""

from __future__ import annotations

import os
import struct
from pathlib import Path

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.main import create_app
from apps.api.app.orchestration.viewer_service import ViewerService
from services.assets.file_ingest import AssetIngestService
from services.scene_core.project_manifest import ProjectManifest


def test_editor_and_viewer_routes_registered(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    os.environ["DECO_VIEWER_PORT"] = "8095"
    get_repo.cache_clear()
    get_viewer_service.cache_clear()

    app = create_app()
    routes = {route.path for route in app.routes}
    assert "/editor" in routes
    assert "/projects/{project_id}/viewer/load-room" in routes


def test_viewer_service_loads_room_asset(repo, tmp_path: Path) -> None:
    project = repo.create_project(ProjectManifest(name="Viewer Demo"))
    ingest = AssetIngestService(repo)

    ply_path = tmp_path / "room.ply"
    header = (
        "\n".join(
            [
                "ply",
                "format binary_little_endian 1.0",
                "element vertex 1",
                "property float x",
                "property float y",
                "property float z",
                "property float f_dc_0",
                "property float f_dc_1",
                "property float f_dc_2",
                "property float opacity",
                "property float scale_0",
                "property float scale_1",
                "property float scale_2",
                "property float rot_0",
                "property float rot_1",
                "property float rot_2",
                "property float rot_3",
                "end_header",
            ]
        )
        + "\n"
    ).encode("utf-8")
    payload = struct.pack(
        "<ffffffffffffff",
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
    )
    ply_path.write_bytes(header + payload)
    room = ingest.ingest_room_gsplat(project.id, "Room", ply_path)

    viewer = ViewerService(repo=repo, host="127.0.0.1", port=8096, public_host="localhost")
    session = viewer.load_room(project.id)

    assert session.asset_id == room.id
    assert session.project_id == project.id
    assert session.viewer_url == "http://localhost:8096"

    server = viewer.ensure_server()
    server.stop()
