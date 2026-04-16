"""Tests for Depth Anything 3 configuration defaults."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_config_module():
    config_path = Path(__file__).resolve().parents[1] / "app" / "config.py"
    spec = importlib.util.spec_from_file_location("da3_config_under_test", config_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_da3_model_defaults_to_huggingface_id(tmp_path: Path, monkeypatch) -> None:
    config = _load_config_module()
    monkeypatch.chdir(tmp_path)
    model_dir = tmp_path / "models" / "DA3NESTED-GIANT-LARGE-1.1"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}")
    (model_dir / "model.safetensors").write_text("weights")

    assert config._resolve_da3_model_source(None) == "depth-anything/DA3NESTED-GIANT-LARGE-1.1"


def test_da3_model_keeps_explicit_local_path(tmp_path: Path) -> None:
    config = _load_config_module()
    model_dir = tmp_path / "da3-local"
    model_dir.mkdir()

    assert config._resolve_da3_model_source(str(model_dir)) == str(model_dir.resolve())
