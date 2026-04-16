"""Minimal GLB inspection helpers."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


class InvalidGlbError(ValueError):
    """Raised when a file is not a valid GLB container."""


@dataclass
class GlbMetadata:
    """Basic metadata extracted from a GLB header."""

    version: int
    declared_length: int
    file_size: int


def inspect_glb(path: Path) -> GlbMetadata:
    """Validate GLB magic bytes and return file-level metadata."""
    file_size = path.stat().st_size
    if file_size < 12:
        raise InvalidGlbError("GLB file is too small to contain a valid header")

    with path.open("rb") as handle:
        header = handle.read(12)

    magic, version, declared_length = struct.unpack("<4sII", header)
    if magic != b"glTF":
        raise InvalidGlbError("Expected GLB magic 'glTF'")
    if declared_length != file_size:
        raise InvalidGlbError(
            f"GLB declared length {declared_length} does not match file size {file_size}"
        )

    return GlbMetadata(
        version=version,
        declared_length=declared_length,
        file_size=file_size,
    )

