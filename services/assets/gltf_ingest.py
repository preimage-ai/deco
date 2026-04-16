"""Minimal GLTF inspection helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class InvalidGltfError(ValueError):
    """Raised when a file is not a valid or supported GLTF asset."""


@dataclass
class GltfMetadata:
    """Basic metadata extracted from a GLTF manifest."""

    version: str
    mesh_count: int
    node_count: int
    buffer_count: int
    image_count: int
    embedded_resource_count: int


def inspect_gltf(path: Path) -> GltfMetadata:
    """Validate a GLTF manifest and ensure it is self-contained."""
    try:
        payload = json.loads(path.read_text())
    except UnicodeDecodeError as exc:
        raise InvalidGltfError("GLTF file must be valid UTF-8 JSON") from exc
    except json.JSONDecodeError as exc:
        raise InvalidGltfError("GLTF file is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise InvalidGltfError("GLTF root payload must be a JSON object")

    asset = payload.get("asset")
    if not isinstance(asset, dict):
        raise InvalidGltfError("GLTF file is missing the required asset block")

    version = asset.get("version")
    if not isinstance(version, str) or not version:
        raise InvalidGltfError("GLTF asset block is missing a valid version")

    embedded_resource_count = 0
    external_resources: list[str] = []
    for key in ("buffers", "images"):
        entries = payload.get(key, [])
        if not isinstance(entries, list):
            raise InvalidGltfError(f"GLTF field '{key}' must be a list when present")
        for entry in entries:
            if not isinstance(entry, dict):
                raise InvalidGltfError(f"GLTF field '{key}' must contain objects")
            uri = entry.get("uri")
            if not uri:
                continue
            if not isinstance(uri, str):
                raise InvalidGltfError(f"GLTF field '{key}.uri' must be a string")
            if uri.startswith("data:"):
                embedded_resource_count += 1
                continue
            external_resources.append(uri)

    if external_resources:
        joined = ", ".join(external_resources[:5])
        raise InvalidGltfError(
            "GLTF upload must be self-contained; external buffers or textures are not "
            f"supported ({joined})"
        )

    return GltfMetadata(
        version=version,
        mesh_count=_count_list(payload, "meshes"),
        node_count=_count_list(payload, "nodes"),
        buffer_count=_count_list(payload, "buffers"),
        image_count=_count_list(payload, "images"),
        embedded_resource_count=embedded_resource_count,
    )


def _count_list(payload: dict, key: str) -> int:
    value = payload.get(key, [])
    if value is None:
        return 0
    if not isinstance(value, list):
        raise InvalidGltfError(f"GLTF field '{key}' must be a list when present")
    return len(value)
