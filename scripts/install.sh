#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="python3"
VENV_PATH=""
USE_VENV=1
INSTALL_DA3=0
INSTALL_HUNYUAN=0
HUNYUAN_REPO_PATH=""

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [options]

Options:
  --venv PATH         Create/use a virtualenv at PATH
  --skip-venv         Install into the current interpreter
  --python BIN        Python executable to use (default: python3)
  --with-da3          Install optional Depth Anything 3 pip requirements
  --with-hunyuan      Install optional Hunyuan3D pip requirements
  --hunyuan-repo PATH Explicit local Hunyuan3D checkout to install editable
  --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv)
      VENV_PATH="$2"
      USE_VENV=1
      shift 2
      ;;
    --skip-venv)
      USE_VENV=0
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --with-da3)
      INSTALL_DA3=1
      shift
      ;;
    --with-hunyuan)
      INSTALL_HUNYUAN=1
      shift
      ;;
    --hunyuan-repo)
      HUNYUAN_REPO_PATH="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cd "$ROOT_DIR"

if [[ "$USE_VENV" -eq 1 ]]; then
  if [[ -z "$VENV_PATH" ]]; then
    VENV_PATH=".venv"
  fi
  if [[ ! -d "$VENV_PATH" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_PATH"
  fi
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements.txt

if [[ "$INSTALL_DA3" -eq 1 ]]; then
  "$PYTHON_BIN" -m pip install -r requirements-da3.txt
fi

if [[ "$INSTALL_HUNYUAN" -eq 1 ]]; then
  "$PYTHON_BIN" -m pip install -r requirements-hunyuan.txt
  if [[ -n "$HUNYUAN_REPO_PATH" ]]; then
    "$PYTHON_BIN" -m pip install -e "$HUNYUAN_REPO_PATH"
  fi
fi

cat <<EOF
Install complete.

Interpreter: $("$PYTHON_BIN" -c 'import sys; print(sys.executable)')
Base requirements: installed
Depth Anything 3: $([[ "$INSTALL_DA3" -eq 1 ]] && echo installed || echo skipped)
Hunyuan3D: $([[ "$INSTALL_HUNYUAN" -eq 1 ]] && echo installed || echo skipped)
EOF

if [[ "$INSTALL_DA3" -eq 1 ]]; then
  cat <<'EOF'
DA3 note: the app now defaults to the Hugging Face model `depth-anything/DA3NESTED-GIANT-LARGE-1.1`.
Set `DECO_DA3_MODEL` only if you want to override that with a different HF repo id or an explicit local checkpoint path.
EOF
fi

if [[ "$INSTALL_HUNYUAN" -eq 1 ]]; then
  cat <<'EOF'
Hunyuan note: the app now defaults to the pip-installed `hy3dgen` runtime plus Hugging Face model ids.
Set `DECO_HUNYUAN_REPO_PATH` or use `--hunyuan-repo` only if you explicitly want a local checkout override.
EOF
fi
