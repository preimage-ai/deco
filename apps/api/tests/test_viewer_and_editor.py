"""Tests for viewer-related app wiring."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.api.viewer import editor_page
from apps.api.app.main import create_app
import apps.api.app.orchestration.viewer_service as viewer_service_module
from apps.api.app.orchestration.viewer_service import ViewerService
from services.scene_core.project_manifest import AssetRecord, ObjectInstance, ProjectManifest, Transform


def test_editor_and_viewer_routes_registered(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    os.environ["DECO_VIEWER_PORT"] = "8095"
    get_repo.cache_clear()
    get_viewer_service.cache_clear()

    app = create_app()
    routes = {route.path for route in app.routes}
    assert "/editor" in routes
    assert "/projects/{project_id}/viewer/load-room" in routes


def test_editor_page_includes_mesh_object_workflow(repo) -> None:
    html = editor_page(repo)

    assert 'accept=".glb,.gltf"' in html
    assert 'id="upload-object-form"' in html
    assert 'id="place-object-form"' in html


def test_viewer_service_loads_room_asset_and_visible_mesh_objects(repo, tmp_path: Path, monkeypatch) -> None:
    project = repo.create_project(ProjectManifest(name="Viewer Demo"))
    project_dir = repo.project_dir(project.id)
    room_path = project_dir / "assets" / "rooms" / "room.ply"
    room_path.parent.mkdir(parents=True, exist_ok=True)
    room_path.write_text("ply\n")
    room = repo.add_asset(
        project.id,
        AssetRecord(
            name="Room",
            kind="gsplat_ply",
            role="room",
            source_uri=str(room_path.relative_to(repo.root)),
        ),
    ).assets[0]

    chair_path = project_dir / "assets" / "objects" / "chair.glb"
    chair_path.parent.mkdir(parents=True, exist_ok=True)
    chair_path.write_bytes(b"chair")
    chair_asset = repo.add_asset(
        project.id,
        AssetRecord(
            name="Chair",
            kind="glb",
            role="object",
            source_uri=str(chair_path.relative_to(repo.root)),
        ),
    ).assets[-1]

    lamp_path = project_dir / "assets" / "objects" / "lamp.gltf"
    lamp_path.write_text('{"asset":{"version":"2.0"}}')
    lamp_asset = repo.add_asset(
        project.id,
        AssetRecord(
            name="Lamp",
            kind="gltf",
            role="object",
            source_uri=str(lamp_path.relative_to(repo.root)),
        ),
    ).assets[-1]

    chair_obj = ObjectInstance(
        name="Chair Instance",
        asset_id=chair_asset.id,
        transform=Transform(
            position=[1.0, 2.0, 3.0],
            rotation_euler=[0.0, 0.0, 0.0],
            scale=[1.5, 1.0, 0.5],
        ),
    )
    lamp_obj = ObjectInstance(name="Lamp Instance", asset_id=lamp_asset.id)
    hidden_obj = ObjectInstance(name="Hidden", asset_id=chair_asset.id, visible=False)
    repo.add_object(project.id, chair_obj)
    repo.add_object(project.id, lamp_obj)
    repo.add_object(project.id, hidden_obj)

    mesh_kinds: list[str] = []

    class FakeScene:
        def __init__(self) -> None:
            self.up_directions: list[str] = []
            self.reset_called = False
            self.gaussian_calls: list[tuple[tuple, dict]] = []
            self.glb_calls: list[tuple[tuple, dict]] = []

        def set_up_direction(self, direction: str) -> None:
            self.up_directions.append(direction)

        def reset(self) -> None:
            self.reset_called = True

        def add_gaussian_splats(self, *args, **kwargs) -> None:
            self.gaussian_calls.append((args, kwargs))

        def add_glb(self, *args, **kwargs) -> None:
            self.glb_calls.append((args, kwargs))

    class FakeServer:
        instances: list["FakeServer"] = []

        def __init__(self, host: str, port: int, verbose: bool) -> None:
            self.host = host
            self.port = port
            self.verbose = verbose
            self.scene = FakeScene()
            self.stopped = False
            self.__class__.instances.append(self)

        def stop(self) -> None:
            self.stopped = True

    monkeypatch.setattr(
        viewer_service_module,
        "_import_viser",
        lambda: SimpleNamespace(ViserServer=FakeServer),
    )
    monkeypatch.setattr(
        viewer_service_module,
        "load_gaussian_splat_ply",
        lambda path: SimpleNamespace(
            centers=[[0.0, 0.0, 0.0]],
            rgbs=[[1.0, 1.0, 1.0]],
            opacities=[[1.0]],
            covariances=[[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]],
        ),
    )
    monkeypatch.setattr(
        viewer_service_module,
        "load_mesh_glb_bytes",
        lambda path, *, kind: mesh_kinds.append(kind) or b"mesh-bytes",
    )

    viewer = ViewerService(repo=repo, host="127.0.0.1", port=8096, public_host="localhost")
    session = viewer.load_room(project.id)

    assert session.asset_id == room.id
    assert session.project_id == project.id
    assert session.viewer_url == "http://localhost:8096"
    assert session.loaded_object_ids == [chair_obj.id, lamp_obj.id]
    assert mesh_kinds == ["glb", "gltf"]

    server = viewer.ensure_server()
    assert len(FakeServer.instances) == 1
    assert server.scene.reset_called is True
    assert len(server.scene.gaussian_calls) == 1
    assert len(server.scene.glb_calls) == 2
    first_glb_args, first_glb_kwargs = server.scene.glb_calls[0]
    assert first_glb_args[0] == f"/objects/{chair_obj.id}"
    assert first_glb_kwargs["position"] == (1.0, 2.0, 3.0)
    assert first_glb_kwargs["scale"] == (1.5, 1.0, 0.5)
    assert first_glb_kwargs["wxyz"] == (1.0, 0.0, 0.0, 0.0)
    server.stop()
    assert server.stopped is True
