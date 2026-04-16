"""API schemas for viewer endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class ViewerLaunchRequest(BaseModel):
    """Optional request payload for launching the room viewer."""

    asset_id: str | None = None


class ViewerLaunchResponse(BaseModel):
    """Response payload returned after loading a room into viser."""

    viewer_url: str
    project_id: str
    asset_id: str
    source_uri: str
    loaded_object_ids: list[str]
