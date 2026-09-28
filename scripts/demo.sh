#!/usr/bin/env bash
# Launch the local presentation demo without downloading any AI model weights.
set -euo pipefail
DECO_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DECO_REPO_DIR"
DECO_PYTHON="${DECO_PYTHON:-$DECO_REPO_DIR/.venv/bin/python}"
if [[ ! -x "$DECO_PYTHON" ]]; then
  echo "Create the demo environment first:"
  echo "  ./scripts/install.sh --python python3.11 --venv .venv"
  exit 1
fi
"$DECO_PYTHON" -c 'import fastapi, viser, trimesh, plyfile, imageio, imageio_ffmpeg' || {
  echo "Install missing dependencies: $DECO_PYTHON -m pip install -r requirements.txt"
  exit 1
}
export DECO_PROJECTS_ROOT="${DECO_PROJECTS_ROOT:-$DECO_REPO_DIR/projects}"
export DECO_VIEWER_HOST="${DECO_VIEWER_HOST:-127.0.0.1}"
export DECO_VIEWER_PORT="${DECO_VIEWER_PORT:-8080}"
echo "Deco Studio → http://localhost:${DECO_PORT:-8000}/editor"
echo "Choose ‘Explore the demo studio’ to begin. Ctrl+C stops the server."
exec "$DECO_PYTHON" -m uvicorn apps.api.app.main:app --host "${DECO_HOST:-127.0.0.1}" --port "${DECO_PORT:-8000}"
