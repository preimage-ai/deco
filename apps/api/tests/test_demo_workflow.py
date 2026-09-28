"""Exercise the sample as real splat/GLB assets and verify demo persistence."""
from pathlib import Path

import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.main import create_app
from apps.api.app.schemas.trajectory import RenderTrajectoryRequest
from services.demo.studio import create_demo
from services.preview.viser_scene import load_gaussian_splat_ply
from services.scene_core.project_manifest import Transform
from services.storage.local_fs import ProjectNotFoundError
from services.trajectory.interpolation import sample_trajectory


def test_demo_is_real_editable_content_and_new_copy_preserves_edits(repo):
    first = create_demo(repo)
    assert len(first.scene.objects) == 6
    room = next(a for a in first.assets if a.role == "room")
    splats = load_gaussian_splat_ply(repo.root / room.source_uri, center=False)
    assert len(splats.centers) > 10000
    assert np.isfinite(splats.covariances).all()
    assert splats.centers[:, 2].min() == 0
    for asset in first.assets:
        if asset.role == "object":
            scene = trimesh.load(repo.root / asset.source_uri, force="scene")
            assert len(scene.geometry) > 0
    assert len(sample_trajectory(first.trajectories[0], fps=24)) == 96
    obj = first.scene.objects[0]
    repo.update_object(first.id, obj.id, {"name": "My sofa"})
    second = create_demo(repo)
    assert first.id != second.id
    assert repo.get_project(first.id).scene.objects[0].name == "My sofa"


def test_demo_routes_and_export_library(repo):
    app = create_app()
    app.dependency_overrides[get_repo] = lambda: repo
    client = TestClient(app)
    response = client.post("/demo/projects")
    assert response.status_code == 201
    project = response.json()
    project_id = project["id"]
    assert client.get("/").status_code == 200
    assert client.get("/static/studio.js").status_code == 200
    assert client.get(f"/projects/{project_id}/renders").json() == []
    renders = repo.project_dir(project_id) / "renders"
    (renders / "film.mp4").write_bytes(b"demo-video")
    (renders / "working.partial.mp4").write_bytes(b"unfinished")
    listing = client.get(f"/projects/{project_id}/renders").json()
    assert len(listing) == 1
    assert listing[0]["filename"] == "film.mp4"
    assert client.get(listing[0]["artifact_url"]).content == b"demo-video"
    assert client.get("/projects/nonexistent/renders").status_code == 404
    assert client.get("/capabilities").json()["demo"] is True


@pytest.mark.parametrize("value", [[1, 2], [1, 2, 3, 4], [float('inf'), 0, 0]])
def test_transform_rejects_invalid_vectors(value):
    with pytest.raises(ValidationError):
        Transform(position=value)


@pytest.mark.parametrize("payload", [{"fps": 0}, {"width": -1}, {"height": 721}, {"width": 10000}])
def test_render_rejects_invalid_dimensions(payload):
    with pytest.raises(ValidationError):
        RenderTrajectoryRequest(**payload)


def test_project_path_cannot_escape_store(repo):
    with pytest.raises(ProjectNotFoundError):
        repo.project_dir("../outside")
