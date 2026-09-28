"""Viewer routes and minimal editor page."""

from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from apps.api.app.config import get_settings
from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.orchestration.viewer_service import MissingViewerDependencyError
from apps.api.app.schemas.viewer import (
    ViewerLaunchRequest,
    ViewerLaunchResponse,
    ViewerObjectSelectionRequest,
    ViewerObjectSelectionResponse,
)
from services.preview.mesh_loader import InvalidMeshAssetError, MissingMeshDependencyError
from services.preview.viser_scene import InvalidGaussianSplatError
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(tags=["viewer"])


@router.get("/editor", response_class=HTMLResponse)
def editor_page(_repo: ProjectRepository = Depends(get_repo)) -> str:
    """Serve the editor, keeping frontend assets separate from API routes."""
    template = Path(__file__).resolve().parents[3] / "web" / "editor.html"
    return template.read_text().replace("__RUNWAY_PROMPT__", escape(get_settings().runway_video_prompt))


@router.post("/projects/{project_id}/viewer/load-room", response_model=ViewerLaunchResponse)
def load_room_viewer(
    project_id: str,
    payload: ViewerLaunchRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerLaunchResponse:
    """Load the active room asset into the viser viewer."""
    try:
        session = viewer_service.load_room(project_id=project_id, asset_id=payload.asset_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidGaussianSplatError, InvalidMeshAssetError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (MissingViewerDependencyError, MissingMeshDependencyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ViewerLaunchResponse(
        viewer_url=session.viewer_url,
        project_id=session.project_id,
        asset_id=session.asset_id,
        source_uri=session.source_uri,
        loaded_object_ids=session.loaded_object_ids,
    )


@router.post(
    "/projects/{project_id}/viewer/select-object",
    response_model=ViewerObjectSelectionResponse,
)
def select_viewer_object(
    project_id: str,
    payload: ViewerObjectSelectionRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerObjectSelectionResponse:
    """Show one object's gizmo or clear viewer selection."""
    try:
        loaded_object_ids = viewer_service.set_selected_object(project_id, payload.object_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ViewerObjectSelectionResponse(
        selected_object_id=payload.object_id,
        loaded_object_ids=loaded_object_ids,
    )


@router.post(
    "/projects/{project_id}/viewer/save-object",
    response_model=ViewerObjectSelectionResponse,
)
def save_viewer_object(
    project_id: str,
    payload: ViewerObjectSelectionRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerObjectSelectionResponse:
    """Persist the current object transform from the viewer and hide its gizmo."""
    if not payload.object_id:
        raise HTTPException(status_code=400, detail="object_id is required")

    try:
        viewer_service.persist_object_state(
            project_id,
            payload.object_id,
            name=payload.name,
            scale=payload.scale,
        )
        loaded_object_ids = viewer_service.set_selected_object(project_id, None)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ViewerObjectSelectionResponse(
        selected_object_id=None,
        loaded_object_ids=loaded_object_ids,
    )
