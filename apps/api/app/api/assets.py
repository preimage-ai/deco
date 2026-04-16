"""Asset CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.api.app.deps import get_repo
from apps.api.app.schemas.asset import AssetCreateRequest, AssetUpdateRequest
from services.scene_core.project_manifest import AssetRecord
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


@router.get("", response_model=list[AssetRecord])
def list_assets(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> list[AssetRecord]:
    """List project assets."""
    try:
        return repo.get_project(project_id).assets
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=AssetRecord, status_code=status.HTTP_201_CREATED)
def create_asset(
    project_id: str,
    payload: AssetCreateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> AssetRecord:
    """Register a new project asset."""
    asset = AssetRecord(**payload.model_dump())
    try:
        manifest = repo.add_asset(project_id, asset)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return next(item for item in manifest.assets if item.id == asset.id)


@router.get("/{asset_id}", response_model=AssetRecord)
def get_asset(
    project_id: str,
    asset_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> AssetRecord:
    """Fetch a single asset."""
    try:
        manifest = repo.get_project(project_id)
        return next(item for item in manifest.assets if item.id == asset_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}") from exc


@router.patch("/{asset_id}", response_model=AssetRecord)
def update_asset(
    project_id: str,
    asset_id: str,
    payload: AssetUpdateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> AssetRecord:
    """Update asset metadata."""
    try:
        manifest = repo.update_asset(
            project_id,
            asset_id,
            payload.model_dump(exclude_none=True),
        )
        return next(item for item in manifest.assets if item.id == asset_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    project_id: str,
    asset_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> Response:
    """Delete an asset and any scene objects using it."""
    try:
        repo.delete_asset(project_id, asset_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

