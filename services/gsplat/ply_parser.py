"""Minimal PLY inspection helpers for gsplat assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class InvalidPlyError(ValueError):
    """Raised when a file is not a valid PLY container."""


@dataclass
class PlyMetadata:
    """Basic metadata extracted from a PLY header."""

    format: str
    vertex_count: int | None
    properties: list[str]
    header_lines: int


def inspect_ply(path: Path) -> PlyMetadata:
    """Parse a PLY header and return basic metadata for registration."""
    with path.open("rb") as handle:
        first = handle.readline().decode("utf-8", errors="ignore").strip()
        if first != "ply":
            raise InvalidPlyError("Expected a PLY file with 'ply' header")

        fmt = ""
        vertex_count: int | None = None
        properties: list[str] = []
        header_lines = 1
        in_vertex_element = False

        for raw_line in handle:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            header_lines += 1

            if line.startswith("format "):
                fmt = line.split(maxsplit=1)[1]
            elif line.startswith("element "):
                parts = line.split()
                in_vertex_element = len(parts) >= 3 and parts[1] == "vertex"
                if in_vertex_element:
                    try:
                        vertex_count = int(parts[2])
                    except ValueError as exc:
                        raise InvalidPlyError("Invalid vertex count in PLY header") from exc
            elif line.startswith("property ") and in_vertex_element:
                parts = line.split()
                if parts:
                    properties.append(parts[-1])
            elif line == "end_header":
                break
        else:
            raise InvalidPlyError("PLY header terminated without end_header")

    if not fmt:
        raise InvalidPlyError("PLY header is missing format declaration")

    return PlyMetadata(
        format=fmt,
        vertex_count=vertex_count,
        properties=properties,
        header_lines=header_lines,
    )

