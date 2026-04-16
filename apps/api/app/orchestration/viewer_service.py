"""Viser-based room viewer service."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
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
        server.scene.add_gaussian_splats(
            "/room/gsplat",
            centers=splat_data.centers,
            rgbs=splat_data.rgbs,
            opacities=splat_data.opacities,
            covariances=splat_data.covariances,
        )
        loaded_object_ids = self._load_scene_objects(server=server, manifest=manifest)

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

    def _load_scene_objects(self, server, manifest) -> list[str]:
        """Add visible mesh objects into the active scene."""
        assets_by_id = {asset.id: asset for asset in manifest.assets}
        loaded_object_ids: list[str] = []

        for obj in manifest.scene.objects:
            if not obj.visible:
                continue

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

            server.scene.add_glb(
                f"/objects/{obj.id}",
                glb_data=load_mesh_glb_bytes(source_path, kind=asset.kind),
                position=_vector3(obj.transform.position, fallback=0.0),
                wxyz=_euler_xyz_to_wxyz(obj.transform.rotation_euler),
                scale=_vector3(obj.transform.scale, fallback=1.0),
                visible=obj.visible,
            )
            loaded_object_ids.append(obj.id)

        return loaded_object_ids


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
