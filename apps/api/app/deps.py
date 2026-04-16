"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from apps.api.app.config import Settings, get_settings
from services.assets.file_ingest import AssetIngestService
from apps.api.app.orchestration.viewer_service import ViewerService
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
