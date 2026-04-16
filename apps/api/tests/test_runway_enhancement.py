"""Tests for Runway enhancement integration."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException

from apps.api.app.api.trajectory import enhance_rendered_video, render_trajectory_video
from apps.api.app.deps import get_repo
from apps.api.app.schemas.trajectory import EnhanceRenderRequest, RenderTrajectoryRequest
from services.enhancement import (
    EnhancedVideoArtifact,
    EnhancementUnavailableError,
    RunwayAlephEnhancementConfig,
    RunwayAlephEnhancementService,
)
from services.rendering.trajectory_render import RenderedVideo
from services.scene_core.project_manifest import CameraKeyframe, ProjectManifest, TrajectoryRecord


class _FakeViewerService:
    def __init__(self) -> None:
        self.selected: tuple[str, str | None] | None = None

    def set_selected_object(self, project_id: str, object_id: str | None) -> None:
        self.selected = (project_id, object_id)

    def get_active_client(self):
        return object()


class _FakeRenderService:
    def render_trajectory(self, **kwargs) -> RenderedVideo:
        return RenderedVideo(
            filename="orbit.mp4",
            relative_path=f"{kwargs['project_id']}/renders/orbit.mp4",
            frame_count=4,
            fps=kwargs["fps"],
        )


class _FakeEnhancementService:
    def enhance_video(self, **kwargs) -> EnhancedVideoArtifact:
        prompt = kwargs.get("prompt") or "enhance"
        return EnhancedVideoArtifact(
            provider="runwayml",
            model="gen4_aleph",
            prompt=prompt,
            task_id="task_123",
            status="SUCCEEDED",
            filename="orbit_enhanced.mp4",
            relative_path=f"{kwargs['project_id']}/renders/orbit_enhanced.mp4",
        )


def _trajectory() -> TrajectoryRecord:
    return TrajectoryRecord(
        name="Orbit",
        duration_seconds=1.0,
        keyframes=[
            CameraKeyframe(
                time_seconds=0.0,
                position=[0.0, -2.0, 1.0],
                target=[0.0, 0.0, 0.0],
                up_direction=[0.0, 0.0, 1.0],
                fov_degrees=60.0,
            ),
            CameraKeyframe(
                time_seconds=1.0,
                position=[2.0, 0.0, 1.0],
                target=[0.0, 0.0, 0.0],
                up_direction=[0.0, 0.0, 1.0],
                fov_degrees=60.0,
            ),
        ],
    )


def test_enhance_rendered_video_returns_artifact(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    repo = get_repo()
    project = repo.create_project(ProjectManifest(name="Runway Demo"))
    trajectory = _trajectory()
    repo.add_trajectory(project.id, trajectory)
    render_path = repo.project_dir(project.id) / "renders" / "orbit.mp4"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_bytes(b"mp4")

    response = enhance_rendered_video(
        project_id=project.id,
        filename="orbit.mp4",
        payload=EnhanceRenderRequest(prompt="make this more realistic"),
        repo=repo,
        enhancement_service=_FakeEnhancementService(),
    )

    assert response.provider == "runwayml"
    assert response.task_id == "task_123"
    assert response.prompt == "make this more realistic"
    assert response.artifact_url == f"/projects/{project.id}/renders/orbit_enhanced.mp4"


def test_enhance_rendered_video_surfaces_enhancement_unavailable(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    repo = get_repo()
    project = repo.create_project(ProjectManifest(name="Runway Demo"))
    trajectory = _trajectory()
    repo.add_trajectory(project.id, trajectory)
    render_path = repo.project_dir(project.id) / "renders" / "orbit.mp4"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_bytes(b"mp4")

    class _UnavailableEnhancementService:
        def enhance_video(self, **kwargs):
            raise EnhancementUnavailableError("missing runway key")

    try:
        enhance_rendered_video(
            project_id=project.id,
            filename="orbit.mp4",
            payload=EnhanceRenderRequest(),
            repo=repo,
            enhancement_service=_UnavailableEnhancementService(),
        )
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "missing runway key"
    else:
        raise AssertionError("Expected enhance_rendered_video to raise HTTPException")


def test_render_trajectory_stays_local_only(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    repo = get_repo()
    project = repo.create_project(ProjectManifest(name="Runway Demo"))
    trajectory = _trajectory()
    repo.add_trajectory(project.id, trajectory)

    response = render_trajectory_video(
        project_id=project.id,
        trajectory_id=trajectory.id,
        payload=RenderTrajectoryRequest(),
        repo=repo,
        viewer_service=_FakeViewerService(),
        render_service=_FakeRenderService(),
    )

    assert response.filename == "orbit.mp4"
    assert response.artifact_url == f"/projects/{project.id}/renders/orbit.mp4"


def test_runway_ratio_selection_and_download_path(tmp_path: Path) -> None:
    service = RunwayAlephEnhancementService(
        repo=type("Repo", (), {"root": tmp_path, "project_dir": lambda self, project_id: tmp_path / project_id})(),
        config=RunwayAlephEnhancementConfig(
            api_key="key",
            api_version="2024-11-06",
            model="gen4_aleph",
            prompt_text="enhance",
        ),
    )

    assert service._closest_ratio(1280, 720) == "1280:720"
    assert service._closest_ratio(720, 1280) == "720:1280"
    assert service._artifact_path("proj", "orbit", "https://example.com/out.mp4").name == "orbit_enhanced.mp4"
