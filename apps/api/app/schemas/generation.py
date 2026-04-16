"""Schemas for generation workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from services.scene_core.project_manifest import AssetRecord


class TextTo3DRequest(BaseModel):
    """Request payload for prompt-driven mesh generation."""

    prompt: str = Field(min_length=1)
    name: str | None = None
    include_texture: bool = True
    remove_background: bool = True
    seed: int = 0
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    octree_resolution: int = 256
    num_chunks: int = 20000


class GeneratedGsplatResponse(BaseModel):
    """Response payload for image-to-gsplat generation."""

    project_id: str
    project_name: str
    asset: AssetRecord
    viewer_url: str
    download_url: str
    input_image_count: int
    loaded_object_ids: list[str]
