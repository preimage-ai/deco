"""Local sample scene and non-invasive runtime availability checks."""
from importlib.util import find_spec

from fastapi import APIRouter, Depends

from apps.api.app.config import get_settings
from apps.api.app.deps import get_repo
from services.demo.studio import create_demo
from services.scene_core.project_manifest import ProjectManifest
from services.storage.local_fs import ProjectRepository

router = APIRouter(tags=["demo"])


@router.post("/demo/projects", response_model=ProjectManifest, status_code=201)
def create_demo_project(repo: ProjectRepository = Depends(get_repo)):
    return create_demo(repo)


@router.get("/capabilities")
def capabilities():
    settings = get_settings()
    return {
        "demo": True,
        "astra": bool(settings.openai_api_key),
        "da3": find_spec("depth_anything_3") is not None,
        "hunyuan": find_spec("hy3dgen") is not None or settings.hunyuan_repo_path is not None,
        "runway": bool(settings.runway_api_key) and find_spec("runwayml") is not None,
        "note": "Package availability only; AI generation also requires model weights and suitable hardware.",
    }
