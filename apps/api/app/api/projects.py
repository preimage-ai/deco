"""Project CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.api.app.deps import get_repo
from apps.api.app.schemas.project import (
    ProjectCreateRequest,
    ProjectSummary,
    ProjectUpdateRequest,
)
from services.scene_core.project_manifest import ProjectManifest
from services.storage.local_fs import ProjectNotFoundError, ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
def list_projects(repo: ProjectRepository = Depends(get_repo)) -> list[ProjectSummary]:
    """List all projects."""
    return [ProjectSummary.from_manifest(project) for project in repo.list_projects()]


@router.post("", response_model=ProjectManifest, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> ProjectManifest:
    """Create a new empty project manifest."""
    manifest = ProjectManifest(name=payload.name, description=payload.description)
    return repo.create_project(manifest)


@router.get("/{project_id}", response_model=ProjectManifest)
def get_project(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> ProjectManifest:
    """Fetch a single project manifest."""
    try:
        return repo.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}", response_model=ProjectManifest)
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> ProjectManifest:
    """Update mutable project metadata."""
    try:
        manifest = repo.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    patch = payload.model_dump(exclude_none=True)
    updated = manifest.model_copy(update=patch)
    return repo.update_project(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> Response:
    """Delete a project and all local artifacts under it."""
    try:
        repo.delete_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

