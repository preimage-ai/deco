"""Asset CRUD routes."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from apps.api.app.deps import (
    get_asset_ingest_service,
    get_generation_service,
    get_repo,
    get_viewer_service,
)
from apps.api.app.schemas.asset import AssetCreateRequest, AssetUpdateRequest
from apps.api.app.schemas.generation import TextTo3DRequest
from apps.api.app.schemas.upload import AssetUploadResponse
from services.assets.glb_ingest import InvalidGlbError
from services.assets.gltf_ingest import InvalidGltfError
from services.assets.file_ingest import AssetIngestService
from services.generation import GenerationUnavailableError, Hunyuan3DService
from services.gsplat.ply_parser import InvalidPlyError
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


@router.post("/upload-room", response_model=AssetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_room_asset(
    project_id: str,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    ingest: AssetIngestService = Depends(get_asset_ingest_service),
) -> AssetUploadResponse:
    """Upload a gsplat PLY and register it as the room asset."""
    asset_name = name or Path(file.filename or "room.ply").stem
    try:
        asset = await _store_upload_and_ingest(
            file=file,
            allowed_suffixes={".ply"},
            default_suffix=".ply",
            ingest_fn=lambda temp_path: ingest.ingest_room_gsplat(
                project_id=project_id,
                name=asset_name,
                source_path=temp_path,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidPlyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AssetUploadResponse(asset=asset)


@router.post(
    "/upload-object",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_object_asset(
    project_id: str,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    ingest: AssetIngestService = Depends(get_asset_ingest_service),
) -> AssetUploadResponse:
    """Upload a GLB or self-contained GLTF and register it as an object asset."""
    asset_name = name or Path(file.filename or "object.glb").stem
    try:
        asset = await _store_upload_and_ingest(
            file=file,
            allowed_suffixes={".glb", ".gltf"},
            default_suffix=".glb",
            ingest_fn=lambda temp_path: ingest.ingest_object_mesh(
                project_id=project_id,
                name=asset_name,
                source_path=temp_path,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidGlbError, InvalidGltfError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AssetUploadResponse(asset=asset)


@router.post(
    "/generate-from-image",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_object_from_image(
    project_id: str,
    file: UploadFile = File(...),
    name: str | None = Form(None),
    include_texture: bool = Form(True),
    remove_background: bool = Form(True),
    seed: int = Form(0),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    octree_resolution: int = Form(256),
    num_chunks: int = Form(20000),
    generation: Hunyuan3DService = Depends(get_generation_service),
) -> AssetUploadResponse:
    """Generate a GLB object from an input image with Hunyuan3D."""
    asset_name = name or Path(file.filename or "generated-object.png").stem
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or ".png").suffix or ".png") as tmp:
            temp_path = Path(tmp.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        asset = generation.generate_from_image(
            project_id=project_id,
            name=asset_name,
            image_path=temp_path,
            include_texture=include_texture,
            remove_background=remove_background,
            seed=seed,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            octree_resolution=octree_resolution,
            num_chunks=num_chunks,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GenerationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    return AssetUploadResponse(asset=asset)


@router.post(
    "/generate-from-text",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_object_from_text(
    project_id: str,
    payload: TextTo3DRequest,
    generation: Hunyuan3DService = Depends(get_generation_service),
) -> AssetUploadResponse:
    """Generate a GLB object from a text prompt with Hunyuan3D."""
    asset_name = payload.name or payload.prompt[:48].strip() or "generated-object"
    try:
        asset = generation.generate_from_text(
            project_id=project_id,
            name=asset_name,
            prompt=payload.prompt,
            include_texture=payload.include_texture,
            remove_background=payload.remove_background,
            seed=payload.seed,
            num_inference_steps=payload.num_inference_steps,
            guidance_scale=payload.guidance_scale,
            octree_resolution=payload.octree_resolution,
            num_chunks=payload.num_chunks,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GenerationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AssetUploadResponse(asset=asset)


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
    viewer_service=Depends(get_viewer_service),
) -> Response:
    """Delete an asset and any scene objects using it."""
    try:
        repo.delete_asset(project_id, asset_id)
        viewer_service.refresh_scene_objects(project_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _store_upload_and_ingest(
    file: UploadFile,
    allowed_suffixes: set[str],
    default_suffix: str,
    ingest_fn,
) -> AssetRecord:
    """Persist an uploaded file to a temp path before ingest."""
    temp_path: Path | None = None
    upload_suffix = Path(file.filename or "").suffix.lower()
    temp_suffix = upload_suffix or default_suffix
    if upload_suffix and upload_suffix not in allowed_suffixes:
        expected = ", ".join(sorted(allowed_suffixes))
        raise HTTPException(status_code=400, detail=f"Expected file extension in {{{expected}}}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=temp_suffix) as tmp:
            temp_path = Path(tmp.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        return ingest_fn(temp_path)
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
