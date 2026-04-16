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
    viewer_host: str
    viewer_port: int
    viewer_public_host: str


def get_settings() -> Settings:
    """Return application settings from environment variables."""
    projects_root = Path(os.getenv("DECO_PROJECTS_ROOT", "projects")).resolve()
    viewer_host = os.getenv("DECO_VIEWER_HOST", "0.0.0.0")
    viewer_port = int(os.getenv("DECO_VIEWER_PORT", "8080"))
    viewer_public_host = os.getenv("DECO_VIEWER_PUBLIC_HOST", "localhost")
    return Settings(
        app_name="deco API",
        projects_root=projects_root,
        viewer_host=viewer_host,
        viewer_port=viewer_port,
        viewer_public_host=viewer_public_host,
    )
