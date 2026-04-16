"""Trajectory CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.api.app.deps import get_repo
from apps.api.app.schemas.trajectory import (
    TrajectoryCreateRequest,
    TrajectoryUpdateRequest,
)
from services.scene_core.project_manifest import TrajectoryRecord
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(prefix="/projects/{project_id}/trajectories", tags=["trajectories"])


@router.get("", response_model=list[TrajectoryRecord])
def list_trajectories(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> list[TrajectoryRecord]:
    """List all stored trajectories."""
    try:
        return repo.get_project(project_id).trajectories
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=TrajectoryRecord, status_code=status.HTTP_201_CREATED)
def create_trajectory(
    project_id: str,
    payload: TrajectoryCreateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> TrajectoryRecord:
    """Create a new trajectory definition."""
    trajectory = TrajectoryRecord(**payload.model_dump())
    try:
        manifest = repo.add_trajectory(project_id, trajectory)
        return next(item for item in manifest.trajectories if item.id == trajectory.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{trajectory_id}", response_model=TrajectoryRecord)
def get_trajectory(
    project_id: str,
    trajectory_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> TrajectoryRecord:
    """Fetch a single trajectory."""
    try:
        manifest = repo.get_project(project_id)
        return next(item for item in manifest.trajectories if item.id == trajectory_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Trajectory not found: {trajectory_id}",
        ) from exc


@router.patch("/{trajectory_id}", response_model=TrajectoryRecord)
def update_trajectory(
    project_id: str,
    trajectory_id: str,
    payload: TrajectoryUpdateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> TrajectoryRecord:
    """Update a stored trajectory."""
    try:
        manifest = repo.update_trajectory(
            project_id,
            trajectory_id,
            payload.model_dump(exclude_none=True),
        )
        return next(item for item in manifest.trajectories if item.id == trajectory_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{trajectory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trajectory(
    project_id: str,
    trajectory_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> Response:
    """Delete a stored trajectory."""
    try:
        repo.delete_trajectory(project_id, trajectory_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

