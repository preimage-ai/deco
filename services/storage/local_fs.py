"""Local filesystem project manifest repository."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from services.scene_core.project_manifest import (
    AssetRecord,
    ObjectInstance,
    ProjectManifest,
    TrajectoryRecord,
    utc_now,
)


class ProjectNotFoundError(FileNotFoundError):
    """Raised when a project manifest cannot be found."""


class EntityNotFoundError(LookupError):
    """Raised when a nested manifest entity is not found."""


class ProjectRepository:
    """Persist project manifests under a local projects directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[ProjectManifest]:
        projects: list[ProjectManifest] = []
        for manifest_path in sorted(self.root.glob("*/manifest.json")):
            projects.append(ProjectManifest.model_validate_json(manifest_path.read_text()))
        return projects

    def project_dir(self, project_id: str) -> Path:
        """Return the on-disk directory for a project."""
        return self._project_dir(project_id)

    def create_project(self, manifest: ProjectManifest) -> ProjectManifest:
        project_dir = self._project_dir(manifest.id)
        project_dir.mkdir(parents=True, exist_ok=False)
        (project_dir / "assets").mkdir(exist_ok=True)
        (project_dir / "renders").mkdir(exist_ok=True)
        self._write_manifest(manifest)
        return manifest

    def get_project(self, project_id: str) -> ProjectManifest:
        manifest_path = self._manifest_path(project_id)
        if not manifest_path.exists():
            raise ProjectNotFoundError(project_id)
        return ProjectManifest.model_validate_json(manifest_path.read_text())

    def update_project(self, manifest: ProjectManifest) -> ProjectManifest:
        if not self._manifest_path(manifest.id).exists():
            raise ProjectNotFoundError(manifest.id)
        manifest.updated_at = utc_now()
        self._write_manifest(manifest)
        return manifest

    def delete_project(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)
        shutil.rmtree(project_dir)

    def add_asset(self, project_id: str, asset: AssetRecord) -> ProjectManifest:
        manifest = self.get_project(project_id)
        manifest.assets.append(asset)
        if asset.role == "room":
            manifest.scene.room_asset_id = asset.id
        return self.update_project(manifest)

    def update_asset(self, project_id: str, asset_id: str, patch: dict) -> ProjectManifest:
        manifest = self.get_project(project_id)
        asset = self._find_asset(manifest, asset_id)
        updated_asset = asset.model_copy(update={**patch, "updated_at": utc_now()})
        index = manifest.assets.index(asset)
        manifest.assets[index] = updated_asset
        if updated_asset.role == "room":
            manifest.scene.room_asset_id = updated_asset.id
        elif manifest.scene.room_asset_id == updated_asset.id:
            manifest.scene.room_asset_id = None
        return self.update_project(manifest)

    def delete_asset(self, project_id: str, asset_id: str) -> ProjectManifest:
        manifest = self.get_project(project_id)
        asset = self._find_asset(manifest, asset_id)
        manifest.assets.remove(asset)
        manifest.scene.objects = [
            obj for obj in manifest.scene.objects if obj.asset_id != asset_id
        ]
        if manifest.scene.room_asset_id == asset_id:
            manifest.scene.room_asset_id = None
        return self.update_project(manifest)

    def add_object(self, project_id: str, obj: ObjectInstance) -> ProjectManifest:
        manifest = self.get_project(project_id)
        self._find_asset(manifest, obj.asset_id)
        manifest.scene.objects.append(obj)
        return self.update_project(manifest)

    def update_object(self, project_id: str, object_id: str, patch: dict) -> ProjectManifest:
        manifest = self.get_project(project_id)
        obj = self._find_object(manifest, object_id)
        merged = {**patch, "updated_at": utc_now()}
        updated_object = obj.model_copy(update=merged)
        self._find_asset(manifest, updated_object.asset_id)
        index = manifest.scene.objects.index(obj)
        manifest.scene.objects[index] = updated_object
        return self.update_project(manifest)

    def delete_object(self, project_id: str, object_id: str) -> ProjectManifest:
        manifest = self.get_project(project_id)
        obj = self._find_object(manifest, object_id)
        manifest.scene.objects.remove(obj)
        return self.update_project(manifest)

    def add_trajectory(self, project_id: str, trajectory: TrajectoryRecord) -> ProjectManifest:
        manifest = self.get_project(project_id)
        manifest.trajectories.append(trajectory)
        return self.update_project(manifest)

    def update_trajectory(
        self,
        project_id: str,
        trajectory_id: str,
        patch: dict,
    ) -> ProjectManifest:
        manifest = self.get_project(project_id)
        trajectory = self._find_trajectory(manifest, trajectory_id)
        updated_trajectory = trajectory.model_copy(update={**patch, "updated_at": utc_now()})
        index = manifest.trajectories.index(trajectory)
        manifest.trajectories[index] = updated_trajectory
        return self.update_project(manifest)

    def delete_trajectory(self, project_id: str, trajectory_id: str) -> ProjectManifest:
        manifest = self.get_project(project_id)
        trajectory = self._find_trajectory(manifest, trajectory_id)
        manifest.trajectories.remove(trajectory)
        return self.update_project(manifest)

    def _project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def _manifest_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "manifest.json"

    def _write_manifest(self, manifest: ProjectManifest) -> None:
        manifest_path = self._manifest_path(manifest.id)
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n"
        )

    @staticmethod
    def _find_asset(manifest: ProjectManifest, asset_id: str) -> AssetRecord:
        for asset in manifest.assets:
            if asset.id == asset_id:
                return asset
        raise EntityNotFoundError(f"Asset not found: {asset_id}")

    @staticmethod
    def _find_object(manifest: ProjectManifest, object_id: str) -> ObjectInstance:
        for obj in manifest.scene.objects:
            if obj.id == object_id:
                return obj
        raise EntityNotFoundError(f"Object not found: {object_id}")

    @staticmethod
    def _find_trajectory(
        manifest: ProjectManifest,
        trajectory_id: str,
    ) -> TrajectoryRecord:
        for trajectory in manifest.trajectories:
            if trajectory.id == trajectory_id:
                return trajectory
        raise EntityNotFoundError(f"Trajectory not found: {trajectory_id}")
