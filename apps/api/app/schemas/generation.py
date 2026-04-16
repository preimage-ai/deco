"""Schemas for Hunyuan3D generation requests."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
