"""Pytest fixtures for backend tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.storage.local_fs import ProjectRepository


@pytest.fixture
def repo(tmp_path: Path) -> ProjectRepository:
    """Create a repository backed by an isolated projects directory."""
    return ProjectRepository(tmp_path / "projects")
