"""Image-to-gsplat generation routes."""

from __future__ import annotations

from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from apps.api.app.deps import get_generation_service, get_viewer_service
from apps.api.app.orchestration.viewer_service import (
    MissingViewerDependencyError,
    ViewerService,
)
from apps.api.app.schemas.generation import GeneratedGsplatResponse
from services.generation.depth_anything_generation import (
    DepthAnythingGenerationError,
    DepthAnythingGenerationService,
    MissingDepthAnythingDependencyError,
)
from services.preview.mesh_loader import InvalidMeshAssetError, MissingMeshDependencyError
from services.preview.viser_scene import InvalidGaussianSplatError
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("/create-gsplat", response_model=GeneratedGsplatResponse, status_code=status.HTTP_201_CREATED)
async def create_gsplat_from_images(
    files: list[UploadFile] = File(...),
    generation_service: DepthAnythingGenerationService = Depends(get_generation_service),
    viewer_service: ViewerService = Depends(get_viewer_service),
) -> GeneratedGsplatResponse:
    """Generate a room gsplat from uploaded images and launch it in the viewer."""
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one input image.")

    try:
        with tempfile.TemporaryDirectory(prefix="deco-da3-") as tmp_dir:
            image_paths = await _store_uploaded_images(files, Path(tmp_dir))
            result = generation_service.create_project_from_images(image_paths)

        try:
            session = viewer_service.load_room(project_id=result.project_id, asset_id=result.asset.id)
        except (ProjectNotFoundError, EntityNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (InvalidGaussianSplatError, InvalidMeshAssetError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (MissingViewerDependencyError, MissingMeshDependencyError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    except MissingDepthAnythingDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DepthAnythingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GeneratedGsplatResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        asset=result.asset,
        viewer_url=session.viewer_url,
        download_url=f"/projects/{result.project_id}/assets/{result.asset.id}/download",
        input_image_count=result.input_image_count,
        loaded_object_ids=session.loaded_object_ids,
    )


async def _store_uploaded_images(files: list[UploadFile], target_dir: Path) -> list[Path]:
    """Persist uploaded image files to a temporary directory in request order."""
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_paths: list[Path] = []

    try:
        for index, file in enumerate(files):
            suffix = Path(file.filename or "").suffix.lower() or ".png"
            destination = target_dir / f"{index:04d}{suffix}"
            with destination.open("wb") as handle:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            stored_paths.append(destination)
    finally:
        for file in files:
            await file.close()

    return stored_paths
