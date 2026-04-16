"""API schemas for project assets."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssetCreateRequest(BaseModel):
    """Payload for registering an asset in a project."""

    name: str
    kind: Literal["gsplat_ply", "glb", "gltf", "generated_glb"] = "glb"
    role: Literal["room", "object"] = "object"
    source_uri: str | None = None
    preview_uri: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AssetUpdateRequest(BaseModel):
    """Patch payload for asset updates."""

    name: str | None = None
    kind: Literal["gsplat_ply", "glb", "gltf", "generated_glb"] | None = None
    role: Literal["room", "object"] | None = None
    source_uri: str | None = None
    preview_uri: str | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None
