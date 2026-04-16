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


class ViewerObjectSelectionRequest(BaseModel):
    """Request payload for showing or hiding an object's transform gizmo."""

    object_id: str | None = None


class ViewerObjectSelectionResponse(BaseModel):
    """Response payload after updating viewer object selection."""

    selected_object_id: str | None = None
    loaded_object_ids: list[str]
