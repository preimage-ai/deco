"""Tests for trajectory capture, interpolation, and render output."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from services.rendering.trajectory_render import TrajectoryRenderService
from services.scene_core.project_manifest import CameraKeyframe, ProjectManifest, TrajectoryRecord
from services.storage.local_fs import ProjectRepository
from services.trajectory.interpolation import camera_wxyz_from_look_at, sample_trajectory


class _FakeClientCamera:
    def __init__(self) -> None:
        self.position = np.array([0.0, -2.0, 1.0], dtype=np.float64)
        self.look_at = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.up_direction = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        self.fov = np.deg2rad(60.0)


class _FakeClient:
    def __init__(self) -> None:
        self.camera = _FakeClientCamera()
        self.calls: list[tuple[int, int]] = []

    def get_render(self, height: int, width: int, **kwargs) -> np.ndarray:
        self.calls.append((height, width))
        return np.zeros((height, width, 3), dtype=np.uint8)


def _make_trajectory() -> TrajectoryRecord:
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


def test_sample_trajectory_interpolates_camera_path() -> None:
    samples = sample_trajectory(_make_trajectory(), fps=4)
    assert len(samples) == 4
    assert np.allclose(samples[0].position, np.array([0.0, -2.0, 1.0]))
    assert np.allclose(samples[-1].position, np.array([2.0, 0.0, 1.0]))
    assert samples[0].wxyz.shape == (4,)


def test_camera_wxyz_from_look_at_returns_quaternion() -> None:
    wxyz = camera_wxyz_from_look_at(
        np.array([0.0, -2.0, 1.0]),
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )
    assert wxyz.shape == (4,)
    assert np.isfinite(wxyz).all()


def test_render_trajectory_writes_mp4(tmp_path: Path) -> None:
    repo = ProjectRepository(tmp_path / "projects")
    project = repo.create_project(ProjectManifest(name="Render Demo"))
    trajectory = _make_trajectory()
    repo.add_trajectory(project.id, trajectory)

    service = TrajectoryRenderService(repo)
    client = _FakeClient()
    rendered = service.render_trajectory(
        project_id=project.id,
        trajectory=trajectory,
        client=client,
        width=160,
        height=90,
        fps=4,
    )

    output_path = repo.root / rendered.relative_path
    assert output_path.exists()
    assert output_path.suffix == ".mp4"
    assert rendered.frame_count == 4
    assert client.calls == [(90, 160)] * 4
