"""Trajectory rendering via the connected viser client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import imageio

from services.scene_core.project_manifest import TrajectoryRecord, utc_now
from services.storage.local_fs import ProjectRepository
from services.trajectory.interpolation import sample_trajectory


@dataclass
class RenderedVideo:
    """Metadata for a rendered trajectory video."""

    filename: str
    relative_path: str
    frame_count: int
    fps: int


class TrajectoryRenderService:
    """Render trajectory samples to an MP4 using a live viewer client."""

    def __init__(self, repo: ProjectRepository) -> None:
        self.repo = repo

    def render_trajectory(
        self,
        *,
        project_id: str,
        trajectory: TrajectoryRecord,
        client,
        width: int,
        height: int,
        fps: int,
    ) -> RenderedVideo:
        """Render sampled frames and encode them as an MP4."""
        samples = sample_trajectory(trajectory, fps=fps)
        render_dir = self.repo.project_dir(project_id) / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)

        timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        safe_name = trajectory.name.lower().replace(" ", "_") or trajectory.id
        filename = f"{safe_name}_{timestamp}.mp4"
        output_path = render_dir / filename

        writer = imageio.get_writer(output_path, fps=fps, codec="libx264", quality=8)
        try:
            for sample in samples:
                frame = client.get_render(
                    height=height,
                    width=width,
                    wxyz=sample.wxyz,
                    position=sample.position,
                    fov=sample.fov_radians,
                    transport_format="jpeg",
                )
                writer.append_data(frame)
        finally:
            writer.close()

        return RenderedVideo(
            filename=filename,
            relative_path=str(output_path.relative_to(self.repo.root)),
            frame_count=len(samples),
            fps=fps,
        )
