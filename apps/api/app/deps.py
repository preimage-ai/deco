"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from apps.api.app.config import Settings, get_settings
from services.storage.local_fs import ProjectRepository


@lru_cache(maxsize=1)
def get_repo() -> ProjectRepository:
    """Return the singleton local project repository."""
    settings: Settings = get_settings()
    return ProjectRepository(settings.projects_root)

