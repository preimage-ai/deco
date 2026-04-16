"""File upload ingest and project asset storage helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from services.assets.glb_ingest import GlbMetadata, inspect_glb
from services.assets.gltf_ingest import GltfMetadata, inspect_gltf
from services.gsplat.ply_parser import PlyMetadata, inspect_ply
from services.scene_core.project_manifest import AssetRecord
from services.storage.local_fs import ProjectNotFoundError, ProjectRepository


class AssetIngestService:
    """Persist uploaded files and register them as project assets."""

    def __init__(self, repo: ProjectRepository) -> None:
        self.repo = repo

    def ingest_room_gsplat(self, project_id: str, name: str, source_path: Path) -> AssetRecord:
        """Store a room gsplat PLY file and register it as the active room asset."""
        self.repo.get_project(project_id)
        stored_path = self._copy_into_project(project_id, source_path, "rooms")
        metadata = inspect_ply(stored_path)
        asset = AssetRecord(
            name=name,
            kind="gsplat_ply",
            role="room",
            source_uri=self._relative_uri(stored_path),
            metadata=self._ply_metadata_dict(metadata),
        )
        manifest = self.repo.add_asset(project_id, asset)
        return next(item for item in manifest.assets if item.id == asset.id)

    def ingest_object_glb(self, project_id: str, name: str, source_path: Path) -> AssetRecord:
        """Store a GLB object file and register it as an object asset."""
        return self.ingest_object_mesh(project_id=project_id, name=name, source_path=source_path)

    def ingest_object_mesh(self, project_id: str, name: str, source_path: Path) -> AssetRecord:
        """Store a GLB or self-contained GLTF object file and register it as an object asset."""
        self.repo.get_project(project_id)
        stored_path = self._copy_into_project(project_id, source_path, "objects")
        suffix = stored_path.suffix.lower()
        if suffix == ".gltf":
            metadata = inspect_gltf(stored_path)
            kind = "gltf"
            metadata_dict = self._gltf_metadata_dict(metadata)
        else:
            metadata = inspect_glb(stored_path)
            kind = "glb"
            metadata_dict = self._glb_metadata_dict(metadata)
        asset = AssetRecord(
            name=name,
            kind=kind,
            role="object",
            source_uri=self._relative_uri(stored_path),
            metadata=metadata_dict,
        )
        manifest = self.repo.add_asset(project_id, asset)
        return next(item for item in manifest.assets if item.id == asset.id)

    def _copy_into_project(self, project_id: str, source_path: Path, category: str) -> Path:
        project_dir = self.repo.project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        asset_dir = project_dir / "assets" / category
        asset_dir.mkdir(parents=True, exist_ok=True)
        destination = asset_dir / source_path.name
        destination = self._dedupe_path(destination)
        shutil.copy2(source_path, destination)
        return destination

    def _relative_uri(self, path: Path) -> str:
        return str(path.relative_to(self.repo.root))

    @staticmethod
    def _dedupe_path(path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        index = 1
        while True:
            candidate = parent / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def _ply_metadata_dict(metadata: PlyMetadata) -> dict[str, str | int]:
        return {
            "format": metadata.format,
            "vertex_count": metadata.vertex_count or 0,
            "header_lines": metadata.header_lines,
            "properties": ",".join(metadata.properties),
        }

    @staticmethod
    def _glb_metadata_dict(metadata: GlbMetadata) -> dict[str, int]:
        return {
            "version": metadata.version,
            "declared_length": metadata.declared_length,
            "file_size": metadata.file_size,
        }

    @staticmethod
    def _gltf_metadata_dict(metadata: GltfMetadata) -> dict[str, str | int]:
        return {
            "version": metadata.version,
            "mesh_count": metadata.mesh_count,
            "node_count": metadata.node_count,
            "buffer_count": metadata.buffer_count,
            "image_count": metadata.image_count,
            "embedded_resource_count": metadata.embedded_resource_count,
        }
