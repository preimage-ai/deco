"""Project manifest and scene schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Create a stable-ish prefixed identifier for project entities."""
    return f"{prefix}_{uuid4().hex[:12]}"


class Transform(BaseModel):
    """Basic transform for placed objects."""

    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])


class AssetRecord(BaseModel):
    """Asset metadata stored in the project manifest."""

    id: str = Field(default_factory=lambda: new_id("asset"))
    name: str
    kind: Literal["gsplat_ply", "glb", "generated_glb"] = "glb"
    role: Literal["room", "object"] = "object"
    source_uri: str | None = None
    preview_uri: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ObjectInstance(BaseModel):
    """A placed object instance inside the room scene."""

    id: str = Field(default_factory=lambda: new_id("obj"))
    name: str
    asset_id: str
    transform: Transform = Field(default_factory=Transform)
    visible: bool = True
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CameraKeyframe(BaseModel):
    """A single trajectory keyframe."""

    id: str = Field(default_factory=lambda: new_id("kf"))
    time_seconds: float
    position: list[float]
    target: list[float] | None = None
    up_direction: list[float] | None = None
    rotation_euler: list[float] | None = None
    fov_degrees: float | None = None


class VelocityProfile(BaseModel):
    """Velocity settings for trajectory sampling."""

    mode: Literal["constant", "ease_in_out", "custom"] = "ease_in_out"
    speed: float = 1.0


class TrajectoryRecord(BaseModel):
    """Stored camera trajectory definition."""

    id: str = Field(default_factory=lambda: new_id("traj"))
    name: str
    spline: Literal["linear", "catmull_rom"] = "catmull_rom"
    is_closed: bool = False
    duration_seconds: float = 5.0
    velocity: VelocityProfile = Field(default_factory=VelocityProfile)
    keyframes: list[CameraKeyframe] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SceneState(BaseModel):
    """Room scene state."""

    room_asset_id: str | None = None
    objects: list[ObjectInstance] = Field(default_factory=list)


class ProjectManifest(BaseModel):
    """Versioned top-level project manifest."""

    schema_version: str = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("proj"))
    name: str
    description: str | None = None
    assets: list[AssetRecord] = Field(default_factory=list)
    scene: SceneState = Field(default_factory=SceneState)
    trajectories: list[TrajectoryRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
