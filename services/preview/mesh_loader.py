"""Helpers for preparing object mesh assets for the viewer."""

from __future__ import annotations

from pathlib import Path


class InvalidMeshAssetError(ValueError):
    """Raised when a mesh asset cannot be loaded into the viewer."""


class MissingMeshDependencyError(ImportError):
    """Raised when optional mesh-viewer dependencies are unavailable."""


def load_mesh_glb_bytes(path: Path, *, kind: str) -> bytes:
    """Return GLB bytes for a mesh asset, converting GLTF when needed."""
    normalized_kind = kind.lower()
    suffix = path.suffix.lower()

    if normalized_kind in {"glb", "generated_glb"} or suffix == ".glb":
        return path.read_bytes()

    if normalized_kind != "gltf" and suffix != ".gltf":
        raise InvalidMeshAssetError(f"Unsupported mesh asset kind for viewer: {kind}")

    trimesh = _import_trimesh()
    try:
        scene = trimesh.load(path, force="scene")
        glb_data = scene.export(file_type="glb")
    except Exception as exc:  # pragma: no cover - guarded by tests via monkeypatch
        raise InvalidMeshAssetError(f"Unable to convert GLTF mesh for viewer: {path.name}") from exc

    if not isinstance(glb_data, (bytes, bytearray)):
        raise InvalidMeshAssetError("GLTF conversion did not produce GLB bytes")
    return bytes(glb_data)


def _import_trimesh():
    try:
        import trimesh
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise MissingMeshDependencyError(
            "Mesh viewing requires the optional 'trimesh' package. Install `trimesh` "
            "to place GLB or GLTF objects into the viewer."
        ) from exc
    return trimesh
