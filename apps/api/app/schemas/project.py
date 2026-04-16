"""API schemas for projects."""

from __future__ import annotations

from pydantic import BaseModel

from services.scene_core.project_manifest import ProjectManifest


class ProjectCreateRequest(BaseModel):
    """Payload for creating a project."""

    name: str
    description: str | None = None


class ProjectUpdateRequest(BaseModel):
    """Payload for updating basic project metadata."""

    name: str | None = None
    description: str | None = None


class ProjectSummary(BaseModel):
    """Small project summary for list endpoints."""

    id: str
    name: str
    description: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_manifest(cls, manifest: ProjectManifest) -> "ProjectSummary":
        return cls(
            id=manifest.id,
            name=manifest.name,
            description=manifest.description,
            created_at=manifest.created_at.isoformat(),
            updated_at=manifest.updated_at.isoformat(),
        )

