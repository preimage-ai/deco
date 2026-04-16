"""Scene and object CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.api.app.deps import get_repo
from apps.api.app.schemas.scene import ObjectCreateRequest, ObjectUpdateRequest
from services.scene_core.project_manifest import ObjectInstance, SceneState
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(prefix="/projects/{project_id}", tags=["scene"])


@router.get("/scene", response_model=SceneState)
def get_scene(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> SceneState:
    """Fetch the scene state for a project."""
    try:
        return repo.get_project(project_id).scene
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/objects", response_model=list[ObjectInstance])
def list_objects(
    project_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> list[ObjectInstance]:
    """List all placed objects in the project scene."""
    try:
        return repo.get_project(project_id).scene.objects
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/objects", response_model=ObjectInstance, status_code=status.HTTP_201_CREATED)
def create_object(
    project_id: str,
    payload: ObjectCreateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> ObjectInstance:
    """Create a placed object instance."""
    obj = ObjectInstance(**payload.model_dump())
    try:
        manifest = repo.add_object(project_id, obj)
        return next(item for item in manifest.scene.objects if item.id == obj.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/objects/{object_id}", response_model=ObjectInstance)
def get_object(
    project_id: str,
    object_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> ObjectInstance:
    """Fetch a placed object instance."""
    try:
        manifest = repo.get_project(project_id)
        return next(item for item in manifest.scene.objects if item.id == object_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Object not found: {object_id}") from exc


@router.patch("/objects/{object_id}", response_model=ObjectInstance)
def update_object(
    project_id: str,
    object_id: str,
    payload: ObjectUpdateRequest,
    repo: ProjectRepository = Depends(get_repo),
) -> ObjectInstance:
    """Update a placed object instance."""
    try:
        manifest = repo.update_object(
            project_id,
            object_id,
            payload.model_dump(exclude_none=True),
        )
        return next(item for item in manifest.scene.objects if item.id == object_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    project_id: str,
    object_id: str,
    repo: ProjectRepository = Depends(get_repo),
) -> Response:
    """Delete a placed object instance."""
    try:
        repo.delete_object(project_id, object_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

