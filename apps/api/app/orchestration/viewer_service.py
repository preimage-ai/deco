"""Viser-based room viewer service."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, atan2, cos, sin
from typing import Any

from services.preview.mesh_loader import (
    InvalidMeshAssetError,
    MissingMeshDependencyError,
    load_mesh_glb_bytes,
)
from services.preview.viser_scene import InvalidGaussianSplatError, load_gaussian_splat_ply
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository


@dataclass
class ViewerSession:
    """Description of the active viewer state."""

    viewer_url: str
    project_id: str
    asset_id: str
    source_uri: str
    loaded_object_ids: list[str]


@dataclass
class ViewerObjectHandles:
    """Scene handles associated with a placed object."""

    transform: Any
    mesh: Any
    scale: tuple[float, float, float]


class MissingViewerDependencyError(ImportError):
    """Raised when optional viewer dependencies are unavailable."""


class ViewerService:
    """Manage a single viser server used for room preview."""

    def __init__(
        self,
        repo: ProjectRepository,
        host: str = "0.0.0.0",
        port: int = 8080,
        public_host: str = "localhost",
    ) -> None:
        self.repo = repo
        self.host = host
        self.port = port
        self.public_host = public_host
        self._server: Any | None = None
        self._current_session: ViewerSession | None = None
        self._object_handles: dict[str, ViewerObjectHandles] = {}
        self._selected_object_id: str | None = None

    def ensure_server(self):
        """Start the viser server if needed."""
        if self._server is None:
            viser = _import_viser()
            self._server = viser.ViserServer(host=self.host, port=self.port, verbose=False)
            self._server.scene.set_up_direction("+z")
        return self._server

    def load_room(self, project_id: str, asset_id: str | None = None) -> ViewerSession:
        """Load a room gsplat asset into the viewer."""
        manifest = self.repo.get_project(project_id)
        room_asset_id = asset_id or manifest.scene.room_asset_id
        if room_asset_id is None:
            raise EntityNotFoundError("Project does not have an active room asset")

        asset = next((item for item in manifest.assets if item.id == room_asset_id), None)
        if asset is None:
            raise EntityNotFoundError(f"Asset not found: {room_asset_id}")
        if asset.kind != "gsplat_ply":
            raise InvalidGaussianSplatError("Viewer currently supports gsplat_ply room assets only")
        if not asset.source_uri:
            raise InvalidGaussianSplatError("Room asset is missing source_uri")

        source_path = self.repo.root / asset.source_uri
        if not source_path.exists():
            raise ProjectNotFoundError(f"Asset file is missing on disk: {source_path}")

        splat_data = load_gaussian_splat_ply(source_path)
        server = self.ensure_server()
        server.scene.reset()
        server.scene.set_up_direction("+z")
        self._object_handles = {}
        self._selected_object_id = None
        server.scene.add_gaussian_splats(
            "/room/gsplat",
            centers=splat_data.centers,
            rgbs=splat_data.rgbs,
            opacities=splat_data.opacities,
            covariances=splat_data.covariances,
        )
        loaded_object_ids = self._sync_scene_objects(server=server, manifest=manifest)

        viewer_url = f"http://{self.public_host}:{self.port}"
        self._current_session = ViewerSession(
            viewer_url=viewer_url,
            project_id=project_id,
            asset_id=asset.id,
            source_uri=asset.source_uri,
            loaded_object_ids=loaded_object_ids,
        )
        return self._current_session

    def get_session(self) -> ViewerSession | None:
        """Return the current viewer session if one exists."""
        return self._current_session

    def get_active_client(self):
        """Return the connected client that should drive capture and rendering."""
        server = self.ensure_server()
        clients = server.get_clients()
        if not clients:
            raise EntityNotFoundError("No active viewer client is connected")
        client_id = sorted(clients.keys())[0]
        return clients[client_id]

    def refresh_scene_objects(
        self,
        project_id: str,
        *,
        select_object_id: str | None = None,
    ) -> list[str]:
        """Reconcile placed objects into the active viewer without reloading the room."""
        if self._current_session is None or self._current_session.project_id != project_id:
            return []

        manifest = self.repo.get_project(project_id)
        loaded_object_ids = self._sync_scene_objects(
            server=self.ensure_server(),
            manifest=manifest,
            select_object_id=select_object_id,
        )
        self._current_session.loaded_object_ids = loaded_object_ids
        return loaded_object_ids

    def _sync_scene_objects(
        self,
        server,
        manifest,
        *,
        select_object_id: str | None = None,
    ) -> list[str]:
        """Add, update, and remove visible mesh objects in the active scene."""
        assets_by_id = {asset.id: asset for asset in manifest.assets}
        visible_objects = [obj for obj in manifest.scene.objects if obj.visible]
        visible_object_ids = {obj.id for obj in visible_objects}

        for object_id in list(self._object_handles):
            if object_id not in visible_object_ids:
                self._remove_object_handles(object_id)

        for obj in visible_objects:
            self._upsert_object_handles(server=server, manifest=manifest, obj=obj, assets_by_id=assets_by_id)

        if select_object_id is not None:
            self._select_object(select_object_id)
        elif self._selected_object_id is not None and self._selected_object_id not in self._object_handles:
            self._selected_object_id = None

        return [obj.id for obj in visible_objects]

    def set_selected_object(self, project_id: str, object_id: str | None) -> list[str]:
        """Show the gizmo for one object or hide gizmos entirely."""
        if self._current_session is None or self._current_session.project_id != project_id:
            return []

        if object_id is None:
            self._clear_selection()
        else:
            self._select_object(object_id)
        return list(self._object_handles.keys())

    def _upsert_object_handles(self, server, manifest, obj, assets_by_id: dict) -> None:
        """Create or replace the scene handles for a placed mesh object."""
        asset = assets_by_id.get(obj.asset_id)
        if asset is None:
            raise EntityNotFoundError(f"Asset not found: {obj.asset_id}")
        if asset.kind not in {"glb", "gltf", "generated_glb"}:
            raise InvalidMeshAssetError(
                f"Viewer supports GLB/GLTF object meshes only, got {asset.kind}"
            )
        if not asset.source_uri:
            raise InvalidMeshAssetError(f"Mesh asset is missing source_uri: {asset.id}")

        source_path = self.repo.root / asset.source_uri
        if not source_path.exists():
            raise ProjectNotFoundError(f"Asset file is missing on disk: {source_path}")

        self._remove_object_handles(obj.id)
        control_name = f"/objects/{obj.id}/control"
        mesh_name = f"/objects/{obj.id}/mesh"
        position = _vector3(obj.transform.position, fallback=0.0)
        wxyz = _euler_xyz_to_wxyz(obj.transform.rotation_euler)
        scale = _vector3(obj.transform.scale, fallback=1.0)
        transform_handle = server.scene.add_transform_controls(
            control_name,
            position=position,
            wxyz=wxyz,
            visible=obj.id == self._selected_object_id,
        )
        mesh_handle = server.scene.add_glb(
            mesh_name,
            glb_data=load_mesh_glb_bytes(source_path, kind=asset.kind),
            position=position,
            wxyz=wxyz,
            scale=scale,
            visible=obj.visible,
        )
        self._object_handles[obj.id] = ViewerObjectHandles(
            transform=transform_handle,
            mesh=mesh_handle,
            scale=scale,
        )

        @mesh_handle.on_click
        def _handle_click(_event, object_id: str = obj.id) -> None:
            self._select_object(object_id)

        @transform_handle.on_update
        def _handle_update(_event, object_id: str = obj.id) -> None:
            self._sync_mesh_to_transform(object_id)

        @transform_handle.on_drag_end
        def _handle_drag_end(_event, object_id: str = obj.id) -> None:
            self._sync_mesh_to_transform(object_id)

    def _remove_object_handles(self, object_id: str) -> None:
        """Remove existing scene handles for an object if present."""
        handles = self._object_handles.pop(object_id, None)
        if handles is None:
            return

        handles.mesh.remove()
        handles.transform.remove()
        if self._selected_object_id == object_id:
            self._selected_object_id = None

    def _select_object(self, object_id: str) -> None:
        """Show the transform gizmo for the selected object and hide the previous one."""
        if self._selected_object_id == object_id:
            return

        if self._selected_object_id is not None:
            previous = self._object_handles.get(self._selected_object_id)
            if previous is not None:
                previous.transform.visible = False

        current = self._object_handles.get(object_id)
        if current is None:
            self._selected_object_id = None
            return

        current.transform.position = current.mesh.position
        current.transform.wxyz = current.mesh.wxyz
        current.transform.visible = True
        self._selected_object_id = object_id

    def _clear_selection(self) -> None:
        """Hide all transform gizmos."""
        if self._selected_object_id is not None:
            previous = self._object_handles.get(self._selected_object_id)
            if previous is not None:
                previous.transform.visible = False
        self._selected_object_id = None

    def _sync_mesh_to_transform(self, object_id: str) -> None:
        """Apply the current gizmo pose to the visible mesh without persisting yet."""
        handles = self._object_handles.get(object_id)
        if handles is None:
            return
        handles.mesh.position = handles.transform.position
        handles.mesh.wxyz = handles.transform.wxyz

    def _persist_object_transform(self, project_id: str, object_id: str) -> None:
        """Write an interactively edited object transform back to the project manifest."""
        handles = self._object_handles.get(object_id)
        if handles is None:
            return

        self._sync_mesh_to_transform(object_id)
        manifest = self.repo.get_project(project_id)
        obj = next((item for item in manifest.scene.objects if item.id == object_id), None)
        if obj is None:
            raise EntityNotFoundError(f"Object not found: {object_id}")

        self.repo.update_object(
            project_id,
            object_id,
            {
                "transform": {
                    "position": list(_vector3(handles.mesh.position, fallback=0.0)),
                    "rotation_euler": list(_wxyz_to_euler_xyz(handles.mesh.wxyz)),
                    "scale": list(handles.scale),
                }
            },
        )
        self._clear_selection()

    def persist_selected_object(self, project_id: str, object_id: str) -> None:
        """Persist the current object pose and hide its gizmo."""
        self._persist_object_transform(project_id, object_id)


def _import_viser():
    try:
        import viser
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise MissingViewerDependencyError(
            "Viewer support requires the optional `viser` package. "
            "Install `viser` to launch the room viewer."
        ) from exc
    return viser


def _vector3(values: list[float], *, fallback: float) -> tuple[float, float, float]:
    """Normalize stored transform vectors to XYZ float tuples."""
    x, y, z = (list(values) + [fallback, fallback, fallback])[:3]
    return (float(x), float(y), float(z))


def _euler_xyz_to_wxyz(values: list[float]) -> tuple[float, float, float, float]:
    """Convert XYZ Euler radians into the quaternion ordering expected by viser."""
    rx, ry, rz = _vector3(values, fallback=0.0)
    cx, sx = cos(rx / 2.0), sin(rx / 2.0)
    cy, sy = cos(ry / 2.0), sin(ry / 2.0)
    cz, sz = cos(rz / 2.0), sin(rz / 2.0)

    return (
        cx * cy * cz + sx * sy * sz,
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz,
    )


def _wxyz_to_euler_xyz(values: tuple[float, float, float, float]) -> tuple[float, float, float]:
    """Convert a quaternion in WXYZ order into XYZ Euler radians."""
    w, x, y, z = values

    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    rx = atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        ry = (3.141592653589793 / 2.0) * (1.0 if sinp >= 0.0 else -1.0)
    else:
        ry = asin(sinp)

    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    rz = atan2(siny_cosp, cosy_cosp)

    return (rx, ry, rz)
