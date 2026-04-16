"""API schemas for scene objects."""

from __future__ import annotations

from pydantic import BaseModel, Field

from services.scene_core.project_manifest import Transform


class ObjectCreateRequest(BaseModel):
    """Payload for creating a scene object."""

    name: str
    asset_id: str
    transform: Transform = Field(default_factory=Transform)
    visible: bool = True
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ObjectUpdateRequest(BaseModel):
    """Patch payload for updating a scene object."""

    name: str | None = None
    asset_id: str | None = None
    transform: Transform | None = None
    visible: bool | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None

