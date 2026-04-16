"""Tests for viewer-related app wiring."""

from __future__ import annotations

import os
from math import pi, sqrt
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

    assert 'id="room-dropzone"' in html
    assert 'id="mesh-dropzone"' in html
    assert 'id="object-list"' in html
    assert 'id="refresh-objects-button"' in html
    assert 'accept=".glb,.gltf"' in html
    assert 'id="new-scene-button"' in html
    assert 'id="enhance-button"' in html
    assert 'id="enhanced-render-video"' in html
    assert 'id="enhanced-render-meta"' in html
    assert "position: absolute;" in html
    assert "height: 100%;" in html


def test_viewer_service_loads_room_asset_and_visible_mesh_objects(repo, monkeypatch) -> None:
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
            self.transform_calls: list[tuple[tuple, dict, "FakeTransformHandle"]] = []
            self.glb_calls: list[tuple[tuple, dict]] = []

        def set_up_direction(self, direction: str) -> None:
            self.up_directions.append(direction)

        def reset(self) -> None:
            self.reset_called = True

        def add_gaussian_splats(self, *args, **kwargs) -> None:
            self.gaussian_calls.append((args, kwargs))

        def add_transform_controls(self, *args, **kwargs) -> "FakeTransformHandle":
            handle = FakeTransformHandle(
                position=kwargs["position"],
                wxyz=kwargs["wxyz"],
                visible=kwargs["visible"],
            )
            self.transform_calls.append((args, kwargs, handle))
            return handle

        def add_glb(self, *args, **kwargs) -> None:
            handle = FakeGlbHandle(
                position=kwargs.get("position", (0.0, 0.0, 0.0)),
                wxyz=kwargs.get("wxyz", (1.0, 0.0, 0.0, 0.0)),
            )
            self.glb_calls.append((args, kwargs))
            return handle

    class FakeTransformHandle:
        def __init__(self, *, position, wxyz, visible: bool) -> None:
            self.position = position
            self.wxyz = wxyz
            self.visible = visible
            self.removed = False
            self._update_callbacks = []
            self._drag_end_callbacks = []

        def on_update(self, callback):
            self._update_callbacks.append(callback)
            return callback

        def trigger_update(self) -> None:
            for callback in self._update_callbacks:
                callback(SimpleNamespace())

        def on_drag_end(self, callback):
            self._drag_end_callbacks.append(callback)
            return callback

        def trigger_drag_end(self) -> None:
            for callback in self._drag_end_callbacks:
                callback(SimpleNamespace())

        def remove(self) -> None:
            self.removed = True

    class FakeGlbHandle:
        def __init__(self, *, position, wxyz) -> None:
            self.removed = False
            self.position = position
            self.wxyz = wxyz
            self._click_callbacks = []

        def on_click(self, callback):
            self._click_callbacks.append(callback)
            return callback

        def trigger_click(self) -> None:
            for callback in self._click_callbacks:
                callback(SimpleNamespace())

        def remove(self) -> None:
            self.removed = True

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
    assert len(server.scene.transform_calls) == 2
    assert len(server.scene.glb_calls) == 2
    first_transform_args, first_transform_kwargs, _ = server.scene.transform_calls[0]
    assert first_transform_args[0] == f"/objects/{chair_obj.id}/control"
    assert first_transform_kwargs["position"] == (1.0, 2.0, 3.0)
    assert first_transform_kwargs["wxyz"] == (1.0, 0.0, 0.0, 0.0)
    first_glb_args, first_glb_kwargs = server.scene.glb_calls[0]
    assert first_glb_args[0] == f"/objects/{chair_obj.id}/mesh"
    assert first_glb_kwargs["position"] == (1.0, 2.0, 3.0)
    assert first_glb_kwargs["wxyz"] == (1.0, 0.0, 0.0, 0.0)
    assert first_glb_kwargs["scale"] == (1.5, 1.0, 0.5)

    chair_handles = viewer._object_handles[chair_obj.id]
    lamp_handles = viewer._object_handles[lamp_obj.id]
    assert chair_handles.transform.visible is False
    assert lamp_handles.transform.visible is False

    chair_handles.mesh.position = (1.0, 2.0, 3.0)
    chair_handles.mesh.wxyz = (1.0, 0.0, 0.0, 0.0)
    chair_handles.mesh.trigger_click()
    assert chair_handles.transform.visible is True
    assert lamp_handles.transform.visible is False

    chair_handles.transform.position = (4.0, 5.0, 6.0)
    chair_handles.transform.wxyz = (sqrt(0.5), 0.0, 0.0, sqrt(0.5))
    chair_handles.transform.trigger_update()
    chair_handles.transform.trigger_drag_end()

    assert chair_handles.mesh.position == (4.0, 5.0, 6.0)
    assert chair_handles.transform.visible is True

    viewer.persist_selected_object(project.id, chair_obj.id)

    updated_chair = repo.get_project(project.id).scene.objects[0]
    assert updated_chair.transform.position == [4.0, 5.0, 6.0]
    assert round(updated_chair.transform.rotation_euler[2], 6) == round(pi / 2.0, 6)
    assert chair_handles.transform.visible is False

    plant_path = project_dir / "assets" / "objects" / "plant.glb"
    plant_path.write_bytes(b"plant")
    plant_asset = repo.add_asset(
        project.id,
        AssetRecord(
            name="Plant",
            kind="glb",
            role="object",
            source_uri=str(plant_path.relative_to(repo.root)),
        ),
    ).assets[-1]
    plant_obj = ObjectInstance(name="Plant Instance", asset_id=plant_asset.id)
    repo.add_object(project.id, plant_obj)

    loaded_after_add = viewer.refresh_scene_objects(project.id, select_object_id=plant_obj.id)
    assert plant_obj.id in loaded_after_add
    assert viewer._object_handles[plant_obj.id].transform.visible is True

    repo.delete_object(project.id, lamp_obj.id)
    loaded_after_delete = viewer.refresh_scene_objects(project.id)
    assert lamp_obj.id not in loaded_after_delete
    assert lamp_obj.id not in viewer._object_handles

    server.stop()
    assert server.stopped is True
