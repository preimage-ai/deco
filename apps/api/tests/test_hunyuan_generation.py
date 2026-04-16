"""Tests for Hunyuan3D generation route wiring and asset persistence."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import MethodType

from fastapi import HTTPException

from apps.api.app.api.assets import generate_object_from_image, generate_object_from_text
from apps.api.app.deps import get_repo
from apps.api.app.main import create_app
from apps.api.app.schemas.generation import TextTo3DRequest
from services.generation import GenerationUnavailableError, Hunyuan3DConfig, Hunyuan3DService
from services.scene_core.project_manifest import AssetRecord, ProjectManifest


class _FakeGenerationService:
    def __init__(self, repo) -> None:
        self.repo = repo

    def generate_from_text(self, *, project_id: str, name: str, prompt: str, **kwargs) -> AssetRecord:
        asset = AssetRecord(
            name=name,
            kind="generated_glb",
            role="object",
            source_uri=f"{project_id}/assets/objects/{name}.glb",
            metadata={"generator": "fake", "prompt": prompt, **kwargs},
        )
        manifest = self.repo.add_asset(project_id, asset)
        return next(item for item in manifest.assets if item.id == asset.id)

    def generate_from_image(self, *, project_id: str, name: str, **kwargs) -> AssetRecord:
        asset = AssetRecord(
            name=name,
            kind="generated_glb",
            role="object",
            source_uri=f"{project_id}/assets/objects/{name}.glb",
            metadata={"generator": "fake", **kwargs},
        )
        manifest = self.repo.add_asset(project_id, asset)
        return next(item for item in manifest.assets if item.id == asset.id)


class _FakeUploadFile:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content
        self._cursor = 0

    async def read(self, size: int = -1) -> bytes:
        if self._cursor >= len(self._content):
            return b""
        if size < 0:
            chunk = self._content[self._cursor :]
            self._cursor = len(self._content)
            return chunk
        start = self._cursor
        end = min(len(self._content), start + size)
        self._cursor = end
        return self._content[start:end]

    async def close(self) -> None:
        return None


def test_app_registers_generation_routes(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()

    app = create_app()
    routes = {route.path for route in app.routes}

    assert "/projects/{project_id}/assets/generate-from-image" in routes
    assert "/projects/{project_id}/assets/generate-from-text" in routes


def test_generate_from_text_persists_generated_asset(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    repo = get_repo()
    project = repo.create_project(ProjectManifest(name="Generation Demo"))

    response = generate_object_from_text(
        project_id=project.id,
        payload=TextTo3DRequest(prompt="yellow chair", include_texture=False),
        generation=_FakeGenerationService(repo),
    )

    payload = response.model_dump()["asset"]
    assert payload["kind"] == "generated_glb"
    assert payload["metadata"]["prompt"] == "yellow chair"
    assert payload["metadata"]["include_texture"] is False

    loaded = repo.get_project(project.id)
    assert len(loaded.assets) == 1
    assert loaded.assets[0].kind == "generated_glb"


def test_generate_from_image_surfaces_runtime_unavailable(tmp_path: Path) -> None:
    os.environ["DECO_PROJECTS_ROOT"] = str(tmp_path / "projects")
    get_repo.cache_clear()
    repo = get_repo()
    project = repo.create_project(ProjectManifest(name="Generation Demo"))

    class _UnavailableService:
        def generate_from_image(self, **kwargs):
            raise GenerationUnavailableError("cuda missing")

    upload = _FakeUploadFile(filename="chair.png", content=b"fake-image")
    try:
        asyncio.run(
            generate_object_from_image(
                project_id=project.id,
                file=upload,
                generation=_UnavailableService(),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "cuda missing"
    else:
        raise AssertionError("Expected generate_object_from_image to raise HTTPException")


def test_texture_generator_wraps_missing_native_extension(tmp_path: Path) -> None:
    class _FakePaintPipeline:
        @classmethod
        def from_pretrained(cls, model_path: str):
            raise ModuleNotFoundError("No module named 'custom_rasterizer'", name="custom_rasterizer")

    service = Hunyuan3DService(
        ingest=None,
        config=Hunyuan3DConfig(
            repo_path=tmp_path,
            shape_model="shape",
            shape_subfolder="subfolder",
            texture_model="texture",
            text2image_model="text2image",
        ),
    )
    service._runtime = MethodType(  # type: ignore[method-assign]
        lambda self: {"Hunyuan3DPaintPipeline": _FakePaintPipeline},
        service,
    )

    try:
        service._texture_generator()
    except GenerationUnavailableError as exc:
        assert "include_texture=false" in str(exc)
        assert "native rasterizer extensions" in str(exc)
    else:
        raise AssertionError("Expected _texture_generator to raise GenerationUnavailableError")
