"""Optional GPT-6 Astra procedural object endpoints."""
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from apps.api.app.deps import get_astra_generation_service
from apps.api.app.schemas.upload import AssetUploadResponse
from services.generation.astra3d import Astra3DService, AstraGenerationError
from services.generation.hunyuan3d import GenerationUnavailableError
from services.storage.local_fs import ProjectNotFoundError

router = APIRouter(prefix="/projects/{project_id}/assets/astra", tags=["generation"])


class AstraTextRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    name: str = Field(default="Astra furniture", min_length=1, max_length=120)


def _generate(service, **kwargs):
    try:
        return AssetUploadResponse(asset=service.generate(**kwargs))
    except ProjectNotFoundError as exc:
        raise HTTPException(404, "Project not found") from exc
    except GenerationUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except AstraGenerationError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/from-text", response_model=AssetUploadResponse, status_code=201)
def from_text(project_id: str, payload: AstraTextRequest,
              service: Astra3DService = Depends(get_astra_generation_service)):
    return _generate(service, project_id=project_id, name=payload.name, prompt=payload.prompt)


@router.post("/from-image", response_model=AssetUploadResponse, status_code=201)
async def from_image(project_id: str, file: UploadFile = File(...),
                     name: str = Form("Astra reference object", min_length=1, max_length=120),
                     prompt: str = Form("Approximate the main furniture object in this image.", max_length=4000),
                     service: Astra3DService = Depends(get_astra_generation_service)):
    try:
        with tempfile.TemporaryDirectory(prefix="deco-reference-") as directory:
            path = Path(directory) / "reference.image"
            total = 0
            with path.open("wb") as target:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 20 * 1024 * 1024:
                        raise HTTPException(413, "Reference image must be at most 20 MB.")
                    target.write(chunk)
            return await run_in_threadpool(_generate, service, project_id=project_id,
                                           name=name, prompt=prompt, image_path=path)
    finally:
        await file.close()
