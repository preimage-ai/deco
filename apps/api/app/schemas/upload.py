"""API response schemas for upload-backed asset ingest."""

from __future__ import annotations

from pydantic import BaseModel

from services.scene_core.project_manifest import AssetRecord


class AssetUploadResponse(BaseModel):
    """Response payload for uploaded and registered assets."""

    asset: AssetRecord
