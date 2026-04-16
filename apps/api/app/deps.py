"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from apps.api.app.config import Settings, get_settings
from services.assets.file_ingest import AssetIngestService
from services.generation.depth_anything_generation import DepthAnythingGenerationService
from apps.api.app.orchestration.viewer_service import ViewerService
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
