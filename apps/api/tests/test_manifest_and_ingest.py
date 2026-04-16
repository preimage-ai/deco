"""Tests for manifest persistence and asset ingest services."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from services.assets.gltf_ingest import InvalidGltfError
from services.assets.file_ingest import AssetIngestService
from services.scene_core.project_manifest import ObjectInstance, ProjectManifest, TrajectoryRecord
from services.storage.local_fs import EntityNotFoundError


def test_project_manifest_round_trip(repo) -> None:
    project = repo.create_project(
        ProjectManifest(name="Living Room", description="backend test")
    )

    loaded = repo.get_project(project.id)
    assert loaded.id == project.id
    assert loaded.name == "Living Room"
    assert loaded.description == "backend test"
    assert loaded.assets == []
    assert loaded.scene.objects == []
    assert loaded.trajectories == []


def test_ingest_room_and_object_assets(repo, tmp_path: Path) -> None:
    project = repo.create_project(ProjectManifest(name="Ingest Demo"))
    ingest = AssetIngestService(repo)

    ply_path = tmp_path / "room.ply"
    ply_path.write_text(
        "\n".join(
            [
                "ply",
                "format binary_little_endian 1.0",
                "element vertex 2",
                "property float x",
                "property float y",
                "property float z",
                "end_header",
                "",
            ]
        )
    )

    glb_path = tmp_path / "chair.glb"
    body = b"JSON"
    glb_path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)

    room = ingest.ingest_room_gsplat(project.id, "Room", ply_path)
    chair = ingest.ingest_object_glb(project.id, "Chair", glb_path)
    loaded = repo.get_project(project.id)

    assert room.kind == "gsplat_ply"
    assert room.role == "room"
    assert room.metadata["vertex_count"] == 2
    assert loaded.scene.room_asset_id == room.id

    assert chair.kind == "glb"
    assert chair.role == "object"
    assert chair.metadata["version"] == 2
    assert len(loaded.assets) == 2


def test_ingest_self_contained_gltf_object_asset(repo, tmp_path: Path) -> None:
    project = repo.create_project(ProjectManifest(name="GLTF Demo"))
    ingest = AssetIngestService(repo)

    gltf_path = tmp_path / "lamp.gltf"
    gltf_path.write_text(
        json.dumps(
            {
                "asset": {"version": "2.0"},
                "buffers": [
                    {
                        "byteLength": 4,
                        "uri": "data:application/octet-stream;base64,AAAAAA==",
                    }
                ],
                "meshes": [{}],
                "nodes": [{}],
            }
        )
    )

    lamp = ingest.ingest_object_mesh(project.id, "Lamp", gltf_path)

    assert lamp.kind == "gltf"
    assert lamp.role == "object"
    assert lamp.metadata["version"] == "2.0"
    assert lamp.metadata["mesh_count"] == 1


def test_ingest_gltf_rejects_external_resources(repo, tmp_path: Path) -> None:
    project = repo.create_project(ProjectManifest(name="GLTF Validation"))
    ingest = AssetIngestService(repo)

    gltf_path = tmp_path / "table.gltf"
    gltf_path.write_text(
        json.dumps(
            {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": 4, "uri": "table.bin"}],
            }
        )
    )

    try:
        ingest.ingest_object_mesh(project.id, "Table", gltf_path)
    except InvalidGltfError as exc:
        assert "self-contained" in str(exc)
    else:
        raise AssertionError("Expected ingest_object_mesh to reject external GLTF resources")


def test_object_requires_existing_asset(repo) -> None:
    project = repo.create_project(ProjectManifest(name="Scene Demo"))

    try:
        repo.add_object(project.id, ObjectInstance(name="TV", asset_id="asset_missing"))
    except EntityNotFoundError as exc:
        assert "Asset not found" in str(exc)
    else:
        raise AssertionError("Expected add_object to reject missing asset")


def test_trajectory_persists_in_manifest(repo) -> None:
    project = repo.create_project(ProjectManifest(name="Trajectory Demo"))
    repo.add_trajectory(project.id, TrajectoryRecord(name="Orbit"))

    loaded = repo.get_project(project.id)
    assert len(loaded.trajectories) == 1
    assert loaded.trajectories[0].name == "Orbit"
