"""API schemas for gsplat generation workflows."""

from __future__ import annotations

from pydantic import BaseModel

from services.scene_core.project_manifest import AssetRecord


class GeneratedGsplatResponse(BaseModel):
    """Response payload for image-to-gsplat generation."""

    project_id: str
    project_name: str
    asset: AssetRecord
    viewer_url: str
    download_url: str
    input_image_count: int
    loaded_object_ids: list[str]
