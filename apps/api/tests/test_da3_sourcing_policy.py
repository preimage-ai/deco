"""Tests for DA3 model sourcing policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_config_module():
    config_path = Path(__file__).resolve().parents[1] / "app" / "config.py"
    spec = importlib.util.spec_from_file_location("test_app_config_module", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load config module from {config_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


config_module = _load_config_module()


def test_da3_defaults_to_hf_model_even_when_local_checkpoint_is_discoverable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_model_dir = tmp_path / "models" / "DA3-GIANT-1.1"
    local_model_dir.mkdir(parents=True)
    (local_model_dir / "config.json").write_text("{}")
    (local_model_dir / "model.safetensors").write_bytes(b"weights")

    monkeypatch.delenv("DECO_DA3_MODEL", raising=False)
    monkeypatch.setenv("DECO_PROJECTS_ROOT", str(tmp_path / "projects"))
    monkeypatch.chdir(tmp_path)

    settings = config_module.get_settings()

    assert settings.da3_model_name == "depth-anything/DA3NESTED-GIANT-LARGE-1.1"


def test_da3_explicit_local_override_resolves_to_local_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_model_dir = tmp_path / "models" / "DA3-GIANT-1.1"
    local_model_dir.mkdir(parents=True)
    (local_model_dir / "config.json").write_text("{}")
    (local_model_dir / "model.safetensors").write_bytes(b"weights")

    monkeypatch.setenv("DECO_DA3_MODEL", str(local_model_dir))
    monkeypatch.setenv("DECO_PROJECTS_ROOT", str(tmp_path / "projects"))
    settings = config_module.get_settings()

    assert settings.da3_model_name == str(local_model_dir.resolve())
