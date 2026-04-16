"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API app."""

    app_name: str
    projects_root: Path
    viewer_host: str
    viewer_port: int
    viewer_public_host: str
    da3_model_name: str
    da3_device: str
    da3_process_res: int


def _repo_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[3]


def _candidate_model_roots() -> list[Path]:
    """Return likely directories for repo-local DA3 checkpoints."""
    repo_root = _repo_root()
    roots = [repo_root / "models", repo_root / "model"]
    cwd = Path.cwd().resolve()
    if cwd != repo_root:
        roots.extend([cwd / "models", cwd / "model"])
    return roots


def _discover_local_da3_model_dir() -> Path | None:
    """Find a DA3 checkpoint directory that contains config and weights."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    for root in _candidate_model_roots():
        if not root.exists():
            continue
        for config_path in sorted(root.rglob("config.json")):
            model_dir = config_path.parent.resolve()
            if model_dir in seen:
                continue
            if (model_dir / "model.safetensors").exists():
                candidates.append(model_dir)
                seen.add(model_dir)

    if not candidates:
        return None

    preferred_names = [
        "DA3NESTED-GIANT-LARGE-1.1",
        "DA3-GIANT-1.1",
        "DA3NESTED-GIANT-LARGE",
        "DA3-GIANT",
    ]
    for preferred_name in preferred_names:
        for candidate in candidates:
            if candidate.name.upper() == preferred_name.upper():
                return candidate

    return candidates[0]


def _resolve_da3_model_source(raw_value: str | None) -> str:
    """Resolve DA3 source from env, repo-local checkpoint, or remote default."""
    if raw_value:
        configured = Path(raw_value).expanduser()
        path_candidates = [configured]
        if not configured.is_absolute():
            path_candidates.append((_repo_root() / configured).resolve())
        for path_candidate in path_candidates:
            if path_candidate.exists():
                return str(path_candidate.resolve())
        return raw_value

    local_model_dir = _discover_local_da3_model_dir()
    if local_model_dir is not None:
        return str(local_model_dir)

    return "depth-anything/DA3NESTED-GIANT-LARGE-1.1"


def get_settings() -> Settings:
    """Return application settings from environment variables."""
    projects_root = Path(os.getenv("DECO_PROJECTS_ROOT", "projects")).resolve()
    viewer_host = os.getenv("DECO_VIEWER_HOST", "0.0.0.0")
    viewer_port = int(os.getenv("DECO_VIEWER_PORT", "8080"))
    viewer_public_host = os.getenv("DECO_VIEWER_PUBLIC_HOST", "localhost")
    da3_model_name = _resolve_da3_model_source(os.getenv("DECO_DA3_MODEL"))
    da3_device = os.getenv("DECO_DA3_DEVICE", "auto")
    da3_process_res = int(os.getenv("DECO_DA3_PROCESS_RES", "504"))
    return Settings(
        app_name="deco API",
        projects_root=projects_root,
        viewer_host=viewer_host,
        viewer_port=viewer_port,
        viewer_public_host=viewer_public_host,
        da3_model_name=da3_model_name,
        da3_device=da3_device,
        da3_process_res=da3_process_res,
    )
