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
    duration_seconds: float = 5.0
    velocity: VelocityProfile = Field(default_factory=VelocityProfile)
    keyframes: list[CameraKeyframe] = Field(default_factory=list)


class TrajectoryUpdateRequest(BaseModel):
    """Patch payload for updating a camera trajectory."""

    name: str | None = None
    spline: Literal["linear", "catmull_rom"] | None = None
    is_closed: bool | None = None
    duration_seconds: float | None = None
    velocity: VelocityProfile | None = None
    keyframes: list[CameraKeyframe] | None = None

