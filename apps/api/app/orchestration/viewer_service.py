"""Viser-based room viewer service."""

from __future__ import annotations

from dataclasses import dataclass

import viser

from services.preview.viser_scene import (
    GaussianSplatData,
    InvalidGaussianSplatError,
    load_gaussian_splat_ply,
)
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository


@dataclass
class ViewerSession:
    """Description of the active viewer state."""

    viewer_url: str
    project_id: str
    asset_id: str
    source_uri: str


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
        self._server: viser.ViserServer | None = None
        self._current_session: ViewerSession | None = None

    def ensure_server(self) -> viser.ViserServer:
        """Start the viser server if needed."""
        if self._server is None:
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

        viewer_url = f"http://{self.public_host}:{self.port}"
        self._current_session = ViewerSession(
            viewer_url=viewer_url,
            project_id=project_id,
            asset_id=asset.id,
            source_uri=asset.source_uri,
        )
        return self._current_session

    def get_session(self) -> ViewerSession | None:
        """Return the current viewer session if one exists."""
        return self._current_session
