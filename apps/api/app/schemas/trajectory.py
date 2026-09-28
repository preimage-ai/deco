"""API schemas for trajectories."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from services.scene_core.project_manifest import CameraKeyframe, VelocityProfile


class TrajectoryCreateRequest(BaseModel):
    """Payload for creating a camera trajectory."""

    name: str
    spline: Literal["linear", "catmull_rom"] = "catmull_rom"
    is_closed: bool = False
    duration_seconds: float = Field(default=5.0, gt=0, le=300, allow_inf_nan=False)
    velocity: VelocityProfile = Field(default_factory=VelocityProfile)
    keyframes: list[CameraKeyframe] = Field(default_factory=list)


class TrajectoryUpdateRequest(BaseModel):
    """Patch payload for updating a camera trajectory."""

    name: str | None = None
    spline: Literal["linear", "catmull_rom"] | None = None
    is_closed: bool | None = None
    duration_seconds: float | None = Field(default=None, gt=0, le=300, allow_inf_nan=False)
    velocity: VelocityProfile | None = None
    keyframes: list[CameraKeyframe] | None = None


class CaptureKeyframeRequest(BaseModel):
    """Payload for capturing a keyframe from the active viewer camera."""

    time_seconds: float | None = Field(default=None, ge=0, le=300, allow_inf_nan=False)


class RenderTrajectoryRequest(BaseModel):
    """Payload for rendering a saved trajectory to video."""

    width: int = Field(default=1280, ge=64, le=3840, multiple_of=2)
    height: int = Field(default=720, ge=64, le=2160, multiple_of=2)
    fps: int = Field(default=24, ge=1, le=60)


class EnhanceRenderRequest(BaseModel):
    """Payload for AI-enhancing an existing rendered video."""

    width: int = Field(default=1280, ge=64, le=3840, multiple_of=2)
    height: int = Field(default=720, ge=64, le=2160, multiple_of=2)
    ai_wait_timeout_seconds: int = 900
    prompt: str | None = None


class EnhancedVideoResponse(BaseModel):
    """Metadata for an AI-enhanced render artifact or pending task."""

    provider: str
    model: str
    prompt: str
    task_id: str
    status: str
    filename: str | None = None
    relative_path: str | None = None
    artifact_url: str | None = None


class RenderTrajectoryResponse(BaseModel):
    """Response payload for a rendered trajectory artifact."""

    filename: str
    relative_path: str
    artifact_url: str
    frame_count: int
    fps: int
