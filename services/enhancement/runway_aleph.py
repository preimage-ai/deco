"""Runway Aleph video-to-video enhancement integration."""

from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from runwayml import RunwayML

from services.storage.local_fs import ProjectRepository


class EnhancementUnavailableError(RuntimeError):
    """Raised when enhancement is not configured."""


class EnhancementFailedError(RuntimeError):
    """Raised when the remote enhancement task fails."""


@dataclass(frozen=True)
class RunwayAlephEnhancementConfig:
    """Runtime configuration for Runway Aleph enhancement."""

    api_key: str | None
    api_version: str
    model: str
    prompt_text: str
    poll_interval_seconds: float = 5.0


@dataclass(frozen=True)
class EnhancedVideoArtifact:
    """A downloaded or pending AI-enhanced video result."""

    provider: str
    model: str
    prompt: str
    task_id: str
    status: str
    filename: str | None = None
    relative_path: str | None = None


class RunwayAlephEnhancementService:
    """Submit rendered videos to Runway Aleph and store the enhanced output."""

    _ALEPH_RATIOS = (
        "1280:720",
        "720:1280",
        "1104:832",
        "960:960",
        "832:1104",
        "1584:672",
        "848:480",
        "640:480",
    )

    def __init__(self, repo: ProjectRepository, config: RunwayAlephEnhancementConfig) -> None:
        self.repo = repo
        self.config = config

    def enhance_video(
        self,
        *,
        project_id: str,
        source_relative_path: str,
        output_stem: str,
        width: int,
        height: int,
        wait_timeout_seconds: int,
        prompt: str | None = None,
    ) -> EnhancedVideoArtifact:
        """Upload a local render, wait for enhancement, and download the result."""
        prompt_text = (prompt or "").strip() or self.config.prompt_text
        try:
            client = self._client()
            source_path = self.repo.root / source_relative_path
            if not source_path.exists():
                raise FileNotFoundError(source_path)

            with source_path.open("rb") as source_file:
                upload = client.uploads.create_ephemeral(
                    file=(source_path.name, source_file, self._content_type_for(source_path)),
                )

            task = client.video_to_video.create(
                model=self.config.model,
                prompt_text=prompt_text,
                video_uri=upload.uri,
                ratio=self._closest_ratio(width, height),
            )
            task_id = task.id

            deadline = time.monotonic() + max(wait_timeout_seconds, 1)
            last_status = "PENDING"
            while time.monotonic() < deadline:
                task_state = client.tasks.retrieve(task_id)
                last_status = task_state.status
                if task_state.status == "SUCCEEDED":
                    output_url = task_state.output[0]
                    artifact_path = self._artifact_path(project_id, output_stem, output_url)
                    self._download_file(output_url, artifact_path)
                    return EnhancedVideoArtifact(
                        provider="runwayml",
                        model=self.config.model,
                        prompt=prompt_text,
                        task_id=task_id,
                        status=task_state.status,
                        filename=artifact_path.name,
                        relative_path=str(artifact_path.relative_to(self.repo.root)),
                    )
                if task_state.status == "FAILED":
                    raise EnhancementFailedError(task_state.failure)
                if task_state.status == "CANCELLED":
                    raise EnhancementFailedError("Runway enhancement task was cancelled")
                time.sleep(self.config.poll_interval_seconds)

            return EnhancedVideoArtifact(
                provider="runwayml",
                model=self.config.model,
                prompt=prompt_text,
                task_id=task_id,
                status=last_status,
            )
        except EnhancementFailedError:
            raise
        except Exception as exc:
            raise EnhancementFailedError(str(exc)) from exc

    def _client(self) -> RunwayML:
        if not self.config.api_key:
            raise EnhancementUnavailableError(
                "Runway enhancement is not configured; set DECO_RUNWAY_API_KEY or RUNWAYML_API_SECRET"
            )
        return RunwayML(api_key=self.config.api_key, runway_version=self.config.api_version)

    def _artifact_path(self, project_id: str, output_stem: str, output_url: str) -> Path:
        render_dir = self.repo.project_dir(project_id) / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(urlparse(output_url).path).suffix or ".mp4"
        return render_dir / f"{output_stem}_enhanced{suffix}"

    @staticmethod
    def _content_type_for(path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    @classmethod
    def _closest_ratio(cls, width: int, height: int) -> str:
        target = width / height
        return min(
            cls._ALEPH_RATIOS,
            key=lambda ratio: abs(target - cls._parse_ratio(ratio)),
        )

    @staticmethod
    def _parse_ratio(value: str) -> float:
        left, right = value.split(":")
        return int(left) / int(right)

    @staticmethod
    def _download_file(url: str, destination: Path) -> None:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
