"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API app."""

    app_name: str
    projects_root: Path


def get_settings() -> Settings:
    """Return application settings from environment variables."""
    projects_root = Path(os.getenv("DECO_PROJECTS_ROOT", "projects")).resolve()
    return Settings(app_name="deco API", projects_root=projects_root)

