"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from apps.api.app.config import Settings, get_settings
from services.assets.file_ingest import AssetIngestService
from services.generation.depth_anything_generation import DepthAnythingGenerationService
from apps.api.app.orchestration.viewer_service import ViewerService
from services.enhancement.runway_aleph import RunwayAlephEnhancementConfig, RunwayAlephEnhancementService
from services.generation import Hunyuan3DConfig, Hunyuan3DService
from services.rendering.trajectory_render import TrajectoryRenderService
from services.storage.local_fs import ProjectRepository


@lru_cache(maxsize=1)
def get_repo() -> ProjectRepository:
    """Return the singleton local project repository."""
    settings: Settings = get_settings()
    return ProjectRepository(settings.projects_root)


def get_asset_ingest_service() -> AssetIngestService:
    """Return the asset ingest service bound to the project repository."""
    return AssetIngestService(get_repo())


def get_generation_service() -> Hunyuan3DService:
    """Return the Hunyuan3D generation service."""
    settings: Settings = get_settings()
    return Hunyuan3DService(
        ingest=get_asset_ingest_service(),
        config=Hunyuan3DConfig(
            repo_path=settings.hunyuan_repo_path,
            shape_model=settings.hunyuan_shape_model,
            shape_subfolder=settings.hunyuan_shape_subfolder,
            texture_model=settings.hunyuan_texture_model,
            text2image_model=settings.hunyuan_text2image_model,
            device=settings.hunyuan_device,
        ),
    )


def get_enhancement_service() -> RunwayAlephEnhancementService:
    """Return the Runway Aleph enhancement service."""
    settings: Settings = get_settings()
    return RunwayAlephEnhancementService(
        repo=get_repo(),
        config=RunwayAlephEnhancementConfig(
            api_key=settings.runway_api_key,
            api_version=settings.runway_api_version,
            model=settings.runway_video_model,
            prompt_text=settings.runway_video_prompt,
            poll_interval_seconds=settings.runway_poll_interval_seconds,
        ),
    )


@lru_cache(maxsize=1)
def get_viewer_service() -> ViewerService:
    """Return the singleton viser viewer service."""
    settings: Settings = get_settings()
    return ViewerService(
        repo=get_repo(),
        host=settings.viewer_host,
        port=settings.viewer_port,
        public_host=settings.viewer_public_host,
    )


@lru_cache(maxsize=1)
def get_generation_service() -> DepthAnythingGenerationService:
    """Return the singleton Depth Anything 3 generation service."""
    settings: Settings = get_settings()
    return DepthAnythingGenerationService(
        repo=get_repo(),
        model_name=settings.da3_model_name,
        device=settings.da3_device,
        process_res=settings.da3_process_res,
    )


def get_render_service() -> TrajectoryRenderService:
    """Return the trajectory render service."""
    return TrajectoryRenderService(get_repo())
