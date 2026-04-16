"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def _setting(name: str, default: str | None = None) -> str | None:
    dotenv = _dotenv_values(_repo_root() / ".env")
    return os.getenv(name, dotenv.get(name, default))


def _apply_runtime_env_default(name: str) -> None:
    """Expose selected .env values to libraries that read process env directly."""
    value = _setting(name)
    if value:
        os.environ.setdefault(name, value)


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API app."""

    app_name: str
    projects_root: Path
    viewer_host: str
    viewer_port: int
    viewer_public_host: str
    hunyuan_repo_path: Path | None
    hunyuan_shape_model: str
    hunyuan_shape_subfolder: str
    hunyuan_texture_model: str
    hunyuan_text2image_model: str
    hunyuan_device: str
    runway_api_key: str | None
    runway_api_version: str
    runway_video_model: str
    runway_video_prompt: str
    runway_poll_interval_seconds: float
    da3_model_name: str
    da3_device: str
    da3_process_res: int


def _resolve_da3_model_source(raw_value: str | None) -> str:
    """Resolve DA3 source from env or the default Hugging Face model id."""
    if raw_value:
        configured = Path(raw_value).expanduser()
        path_candidates = [configured]
        if not configured.is_absolute():
            path_candidates.append((_repo_root() / configured).resolve())
        for path_candidate in path_candidates:
            if path_candidate.exists():
                return str(path_candidate.resolve())
        return raw_value

    return "depth-anything/DA3NESTED-GIANT-LARGE-1.1"


def get_settings() -> Settings:
    """Return application settings from environment variables."""
    # Libraries such as huggingface_hub read these directly from process env.
    for env_name in ("HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE"):
        _apply_runtime_env_default(env_name)

    projects_root = Path(_setting("DECO_PROJECTS_ROOT", "projects") or "projects").resolve()
    viewer_host = _setting("DECO_VIEWER_HOST", "0.0.0.0") or "0.0.0.0"
    viewer_port = int(_setting("DECO_VIEWER_PORT", "8080") or "8080")
    viewer_public_host = _setting("DECO_VIEWER_PUBLIC_HOST", "localhost") or "localhost"
    raw_hunyuan_repo_path = _setting("DECO_HUNYUAN_REPO_PATH")
    hunyuan_repo_path = (
        Path(raw_hunyuan_repo_path).expanduser().resolve()
        if raw_hunyuan_repo_path
        else None
    )
    hunyuan_shape_model = _setting("DECO_HUNYUAN_SHAPE_MODEL", "tencent/Hunyuan3D-2") or "tencent/Hunyuan3D-2"
    hunyuan_shape_subfolder = _setting(
        "DECO_HUNYUAN_SHAPE_SUBFOLDER",
        "hunyuan3d-dit-v2-0",
    ) or "hunyuan3d-dit-v2-0"
    hunyuan_texture_model = _setting("DECO_HUNYUAN_TEXTURE_MODEL", "tencent/Hunyuan3D-2") or "tencent/Hunyuan3D-2"
    hunyuan_text2image_model = _setting(
        "DECO_HUNYUAN_TEXT2IMAGE_MODEL",
        "Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled",
    ) or "Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled"
    hunyuan_device = _setting("DECO_HUNYUAN_DEVICE", "auto") or "auto"
    runway_api_key = _setting("DECO_RUNWAY_API_KEY") or _setting("RUNWAYML_API_SECRET")
    runway_api_version = _setting("DECO_RUNWAY_API_VERSION", "2024-11-06") or "2024-11-06"
    runway_video_model = _setting("DECO_RUNWAY_VIDEO_MODEL", "gen4_aleph") or "gen4_aleph"
    runway_video_prompt = _setting(
        "DECO_RUNWAY_VIDEO_PROMPT",
        "this video has a gaussian splat render with some 3d meshes added onto it. "
        "turn this video into a photorealistic video with reduced floaters, beautify it "
        "and make the meshes look real",
    ) or (
        "this video has a gaussian splat render with some 3d meshes added onto it. "
        "turn this video into a photorealistic video with reduced floaters, beautify it "
        "and make the meshes look real"
    )
    runway_poll_interval_seconds = float(
        _setting("DECO_RUNWAY_POLL_INTERVAL_SECONDS", "5") or "5"
    )
    da3_model_name = _resolve_da3_model_source(_setting("DECO_DA3_MODEL"))
    da3_device = _setting("DECO_DA3_DEVICE", "auto") or "auto"
    da3_process_res = int(_setting("DECO_DA3_PROCESS_RES", "504") or "504")
    return Settings(
        app_name="Deco Room GSplat Studio",
        projects_root=projects_root,
        viewer_host=viewer_host,
        viewer_port=viewer_port,
        viewer_public_host=viewer_public_host,
        hunyuan_repo_path=hunyuan_repo_path,
        hunyuan_shape_model=hunyuan_shape_model,
        hunyuan_shape_subfolder=hunyuan_shape_subfolder,
        hunyuan_texture_model=hunyuan_texture_model,
        hunyuan_text2image_model=hunyuan_text2image_model,
        hunyuan_device=hunyuan_device,
        runway_api_key=runway_api_key,
        runway_api_version=runway_api_version,
        runway_video_model=runway_video_model,
        runway_video_prompt=runway_video_prompt,
        runway_poll_interval_seconds=runway_poll_interval_seconds,
        da3_model_name=da3_model_name,
        da3_device=da3_device,
        da3_process_res=da3_process_res,
    )
