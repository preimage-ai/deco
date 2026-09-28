"""Test Astra's API contract, bounded recipes, and real GLB export without paid calls."""
import json
from types import SimpleNamespace

import httpx
import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from apps.api.app.deps import get_astra_generation_service, get_repo
from apps.api.app.main import create_app
from services.assets.file_ingest import AssetIngestService
from services.generation.astra3d import Astra3DService, AstraGenerationError, ObjectRecipe, recipe_to_scene
from services.generation.hunyuan3d import GenerationUnavailableError
from services.scene_core.project_manifest import ProjectManifest


def recipe():
    return {"description": "Procedural table approximation", "parts": [
        {"kind": "box", "size": [1.2, .7, .08], "position": [0, 0, .7], "rotation_euler": [0, 0, 0], "color": [130, 90, 60]},
        {"kind": "cylinder", "size": [.4, .4, .66], "position": [0, 0, .33], "rotation_euler": [0, 0, 0], "color": [90, 70, 50]},
    ]}


def service(repo):
    return Astra3DService(AssetIngestService(repo), api_key="test-key")


def test_astra_export_is_real_glb_with_persistent_recipe(repo, monkeypatch):
    project = repo.create_project(ProjectManifest(name="Astra"))
    generator = service(repo)
    monkeypatch.setattr(generator, "_request_recipe", lambda content: ObjectRecipe.model_validate(recipe()))
    asset = generator.generate(project_id=project.id, name="Oak table", prompt="a small oak table")
    mesh = trimesh.load(repo.root / asset.source_uri, force="scene")
    assert len(mesh.geometry) == 2
    assert np.isclose(mesh.bounds[0, 2], 0)
    assert np.allclose(mesh.extents[:2], [1.2, .7])
    assert asset.metadata["textured"] is False
    assert asset.metadata["generator"] == "gpt-6-astra"
    saved = json.loads((repo.root / asset.metadata["recipe_uri"]).read_text())
    assert len(saved["parts"]) == 2


def test_astra_missing_key_makes_no_provider_call(repo, monkeypatch):
    project = repo.create_project(ProjectManifest(name="Astra"))
    generator = Astra3DService(AssetIngestService(repo), api_key=None)
    monkeypatch.setattr(generator, "_request_recipe", lambda _: pytest.fail("Must not call provider"))
    with pytest.raises(GenerationUnavailableError):
        generator.generate(project_id=project.id, name="Table", prompt="table")


@pytest.mark.parametrize("alter", [lambda r:r["parts"][0].update(kind="python"),
                                    lambda r:r["parts"][0].update(size=[-1, 1, 1]),
                                    lambda r:r["parts"][0].update(position=[float('nan'),0,0]),
                                    lambda r:r.update(parts=r["parts"]*40)])
def test_untrusted_recipe_is_bounded(alter):
    data = recipe(); alter(data)
    with pytest.raises(ValidationError):
        ObjectRecipe.model_validate(data)


def test_responses_request_and_parse(repo, monkeypatch):
    seen = {}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            seen.update(kwargs["json"])
            assert url == "https://api.openai.com/v1/responses"
            return httpx.Response(200, request=httpx.Request("POST", url), json={
                "status": "completed", "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": json.dumps(recipe())}]}]})
    monkeypatch.setattr("services.generation.astra3d.httpx.Client", Client)
    result = service(repo)._request_recipe([{"type": "input_text", "text": "table"}])
    assert len(result.parts) == 2
    assert seen["model"] == "gpt-6-astra"
    assert seen["store"] is False
    assert seen["text"]["format"]["strict"] is True
    assert "tools" not in seen


def test_reference_image_is_bounded_and_encoded(tmp_path):
    image = tmp_path / "photo.png"
    Image.new("RGB", (1800, 900)).save(image)
    assert Astra3DService._image_data(image).startswith("data:image/jpeg;base64,")
    image.write_text("not an image")
    with pytest.raises(ValueError): Astra3DService._image_data(image)


def test_astra_routes_use_selected_provider(repo, monkeypatch, tmp_path):
    project = repo.create_project(ProjectManifest(name="Astra"))
    generator = service(repo)
    seen = []
    def plan(content):
        seen.extend(content)
        return ObjectRecipe.model_validate(recipe())
    monkeypatch.setattr(generator, "_request_recipe", plan)
    app = create_app()
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_astra_generation_service] = lambda: generator
    client = TestClient(app)
    base = f"/projects/{project.id}/assets/astra"
    assert client.post(base+"/from-text", json={"prompt":"oak table"}).status_code == 201
    image = tmp_path/"photo.png"
    Image.new("RGB", (100,100)).save(image)
    assert client.post(base+"/from-image", files={"file":("photo.png",image.read_bytes(),"image/png")}).status_code == 201
    assert any(p["type"] == "input_image" for p in seen)
    assert client.post(base+"/from-image", files={"file":("photo.png",b"bad","image/png")}).status_code == 400
    assert client.post(base+"/from-text", json={"prompt":""}).status_code == 422


@pytest.mark.parametrize("data", [
    {"status": "incomplete", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "Declined"}]}]},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "invalid"}]}]},
])
def test_unusable_model_responses_are_reported(repo, monkeypatch, data):
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            return httpx.Response(200, request=httpx.Request("POST",url), json=data)
    monkeypatch.setattr("services.generation.astra3d.httpx.Client", Client)
    with pytest.raises(AstraGenerationError):
        service(repo)._request_recipe([])
