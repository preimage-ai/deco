"""Trajectory CRUD routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse

from apps.api.app.deps import get_enhancement_service, get_render_service, get_repo, get_viewer_service
from apps.api.app.schemas.trajectory import (
    CaptureKeyframeRequest,
    EnhanceRenderRequest,
    EnhancedVideoResponse,
    RenderTrajectoryRequest,
    RenderTrajectoryResponse,
    TrajectoryCreateRequest,
    TrajectoryUpdateRequest,
)
from services.enhancement import EnhancementFailedError, EnhancementUnavailableError
from services.scene_core.project_manifest import TrajectoryRecord
from services.trajectory.interpolation import keyframe_from_camera_state
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


@router.post("/{trajectory_id}/capture-keyframe", response_model=TrajectoryRecord)
def capture_keyframe(
    project_id: str,
    trajectory_id: str,
    payload: CaptureKeyframeRequest,
    repo: ProjectRepository = Depends(get_repo),
    viewer_service=Depends(get_viewer_service),
) -> TrajectoryRecord:
    """Capture the active viewer camera as a new keyframe."""
    try:
        manifest = repo.get_project(project_id)
        trajectory = next(item for item in manifest.trajectories if item.id == trajectory_id)
        client = viewer_service.get_active_client()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Trajectory not found: {trajectory_id}") from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    time_seconds = payload.time_seconds
    if time_seconds is None:
        if not trajectory.keyframes:
            time_seconds = 0.0
        else:
            time_seconds = max(item.time_seconds for item in trajectory.keyframes)
            time_seconds += max(trajectory.duration_seconds / max(len(trajectory.keyframes), 1), 1.0)

    keyframe = keyframe_from_camera_state(
        time_seconds=time_seconds,
        position=client.camera.position,
        target=client.camera.look_at,
        up_direction=client.camera.up_direction,
        fov_radians=client.camera.fov,
    )

    updated_keyframes = sorted(
        [*trajectory.keyframes, keyframe],
        key=lambda item: item.time_seconds,
    )
    manifest = repo.update_trajectory(
        project_id,
        trajectory_id,
        {"keyframes": updated_keyframes},
    )
    return next(item for item in manifest.trajectories if item.id == trajectory_id)


@router.post("/{trajectory_id}/render", response_model=RenderTrajectoryResponse)
def render_trajectory_video(
    project_id: str,
    trajectory_id: str,
    payload: RenderTrajectoryRequest,
    repo: ProjectRepository = Depends(get_repo),
    viewer_service=Depends(get_viewer_service),
    render_service=Depends(get_render_service),
) -> RenderTrajectoryResponse:
    """Render a trajectory to an MP4 using the connected viewer client."""
    try:
        manifest = repo.get_project(project_id)
        trajectory = next(item for item in manifest.trajectories if item.id == trajectory_id)
        viewer_service.set_selected_object(project_id, None)
        client = viewer_service.get_active_client()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Trajectory not found: {trajectory_id}") from exc
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(trajectory.keyframes) < 2:
        raise HTTPException(status_code=400, detail="At least two keyframes are required")

    try:
        rendered = render_service.render_trajectory(
            project_id=project_id,
            trajectory=trajectory,
            client=client,
            width=payload.width,
            height=payload.height,
            fps=payload.fps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RenderTrajectoryResponse(
        filename=rendered.filename,
        relative_path=rendered.relative_path,
        artifact_url=f"/projects/{project_id}/renders/{rendered.filename}",
        frame_count=rendered.frame_count,
        fps=rendered.fps,
    )

render_router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


@render_router.post("/{filename}/enhance", response_model=EnhancedVideoResponse)
def enhance_rendered_video(
    project_id: str,
    filename: str,
    payload: EnhanceRenderRequest,
    repo: ProjectRepository = Depends(get_repo),
    enhancement_service=Depends(get_enhancement_service),
) -> EnhancedVideoResponse:
    """Send an existing rendered MP4 through Runway Aleph enhancement."""
    render_path = repo.project_dir(project_id) / "renders" / Path(filename).name
    if not render_path.exists():
        raise HTTPException(status_code=404, detail=f"Render not found: {filename}")

    try:
        enhanced = enhancement_service.enhance_video(
            project_id=project_id,
            source_relative_path=str(render_path.relative_to(repo.root)),
            output_stem=render_path.stem,
            width=payload.width,
            height=payload.height,
            wait_timeout_seconds=payload.ai_wait_timeout_seconds,
            prompt=payload.prompt,
        )
    except EnhancementUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EnhancementFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EnhancedVideoResponse(
        provider=enhanced.provider,
        model=enhanced.model,
        prompt=enhanced.prompt,
        task_id=enhanced.task_id,
        status=enhanced.status,
        filename=enhanced.filename,
        relative_path=enhanced.relative_path,
        artifact_url=(
            f"/projects/{project_id}/renders/{enhanced.filename}"
            if enhanced.filename
            else None
        ),
    )


@render_router.get("/{filename}")
def get_rendered_video(
    project_id: str,
    filename: str,
    repo: ProjectRepository = Depends(get_repo),
) -> FileResponse:
    """Serve a rendered MP4 artifact for a project."""
    render_path = repo.project_dir(project_id) / "renders" / Path(filename).name
    if not render_path.exists():
        raise HTTPException(status_code=404, detail=f"Render not found: {filename}")
    return FileResponse(render_path, media_type="video/mp4", filename=render_path.name)
