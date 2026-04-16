# Deco Room GSplat Studio

Browser-based tooling for turning room photos or existing `gsplat` captures into editable scenes, placing 3D assets, generating new object meshes, authoring camera shots, and rendering MP4 output through a FastAPI-backed workspace.

## Current Scope

- FastAPI backend for projects, assets, scene objects, trajectories, renders, and viewer launch
- Temporary browser editor served at `/editor`
- Room creation from input images through the optional Depth Anything 3 integration
- Existing room `.ply` upload and live `viser` viewer launch
- Object upload for `.glb` and self-contained `.gltf`
- Hunyuan3D object generation from image or text prompt
- Local trajectory capture and MP4 rendering
- Optional Runway Aleph post-processing for rendered videos

## What Is Stale In Older Docs

These older assumptions are no longer accurate:

- trajectory capture and render flow now exists in the `/editor` UI
- Hunyuan3D object generation is wired into the API and editor
- Runway enhancement is a separate render enhancement step, not part of the initial render request
- the main browser UI is currently served by the API app at `/editor`; `apps/web` is not the active frontend
- API tests live under `apps/api/tests`

## Installation

### Requirements

- Python 3.10+ recommended
- CUDA-capable GPU if you want practical Hunyuan3D or DA3 generation

### Common Install Script

From the repository root:

```bash
chmod +x scripts/install.sh
./scripts/install.sh --venv .venv --with-hunyuan
```

That creates the virtualenv if needed, upgrades `pip`, and installs:

- base API/runtime requirements
- optional Hunyuan3D dependencies
- editable install of `external/Hunyuan3D-2`

Optional flags:

- `--with-da3` installs the Depth Anything 3 stack from `requirements-da3.txt`
- `--skip-venv` installs into the currently active interpreter
- `--python python3.10` chooses a specific Python binary

If `external/Hunyuan3D-2` is missing, the script clones it automatically from GitHub before installing it.

### Manual Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
git clone https://github.com/Tencent/Hunyuan3D-2.git external/Hunyuan3D-2
python -m pip install -r requirements-hunyuan.txt
python -m pip install -e external/Hunyuan3D-2
```

Optional DA3 install:

```bash
python -m pip install -r requirements-da3.txt
```

## Run The App

Start the API server from the repository root:

```bash
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

Then open:

- `http://localhost:8000/docs`
- `http://localhost:8000/editor`

The `viser` viewer runs on port `8080` by default.

## Editor Flow

`/editor` supports two room entry paths:

1. Generate a room splat from overlapping images through `POST /generation/create-gsplat`
2. Upload an existing room `.ply` through `POST /projects/{project_id}/assets/upload-room`

Once a room is loaded, the editor lets you:

- upload `.glb` or self-contained `.gltf` objects
- generate new GLB objects from image or text with Hunyuan3D
- place and transform objects in the live viewer
- create trajectories, capture keyframes, and render MP4s
- optionally submit the latest render to Runway via `POST /projects/{project_id}/renders/{filename}/enhance`

`.gltf` uploads must currently be self-contained. External `.bin` buffers or texture sidecars are not copied into the project.

## Hunyuan3D Notes

Relevant environment variables:

- `DECO_HUNYUAN_REPO_PATH` default `external/Hunyuan3D-2`
- `DECO_HUNYUAN_SHAPE_MODEL` default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_SHAPE_SUBFOLDER` default `hunyuan3d-dit-v2-0`
- `DECO_HUNYUAN_TEXTURE_MODEL` default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_TEXT2IMAGE_MODEL` default `Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled`
- `DECO_HUNYUAN_DEVICE` default `auto`

Object generation endpoints:

- `POST /projects/{project_id}/assets/generate-from-image`
- `POST /projects/{project_id}/assets/generate-from-text`

The current implementation returns `503` when CUDA is unavailable. Texture generation can also fail if Hunyuan3D native rasterizer extensions are not built; in that case retry with `include_texture=false`.

## Depth Anything 3 Notes

Relevant environment variables:

- `DECO_DA3_MODEL`
- `DECO_DA3_DEVICE` default `auto`
- `DECO_DA3_PROCESS_RES` default `504`

If `DECO_DA3_MODEL` is unset, deco first looks for a local checkpoint under repo `models/` or `model/`, then falls back to `depth-anything/DA3NESTED-GIANT-LARGE-1.1`.

The current DA3 integration saves a generated `.ply` and renders it through this repo's own `viser` flow. It does not require the upstream `gsplat` rasterizer package for the current room-generation path.

## Runway Enhancement

Configuration is read from environment variables or the repo-root `.env` file:

- `DECO_RUNWAY_API_KEY`
- `DECO_RUNWAY_API_VERSION` default `2024-11-06`
- `DECO_RUNWAY_VIDEO_MODEL` default `gen4_aleph`
- `DECO_RUNWAY_VIDEO_PROMPT`
- `DECO_RUNWAY_POLL_INTERVAL_SECONDS` default `5`

The app also accepts `RUNWAYML_API_SECRET` as a fallback API key source.

## Environment Variables

General runtime configuration:

- `DECO_PROJECTS_ROOT` default `projects`
- `DECO_VIEWER_HOST` default `0.0.0.0`
- `DECO_VIEWER_PORT` default `8080`
- `DECO_VIEWER_PUBLIC_HOST` default `localhost`

Example:

```bash
DECO_PROJECTS_ROOT=./projects \
DECO_VIEWER_HOST=0.0.0.0 \
DECO_VIEWER_PORT=8080 \
DECO_VIEWER_PUBLIC_HOST=localhost \
DECO_HUNYUAN_REPO_PATH=./external/Hunyuan3D-2 \
DECO_DA3_MODEL=./model/DA3-GIANT-1.1 \
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

## Tests

This environment has a broken globally installed Hydra pytest plugin, so run tests with plugin autoload disabled:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/api/tests -q
```

## Repository Layout

- `apps/api` FastAPI application and tests
- `apps/web` placeholder for a separate frontend app
- `services` domain packages for generation, storage, rendering, viewer, and scene state
- `external/Hunyuan3D-2` optional upstream checkout used for object generation
- `projects` local project and artifact storage
- `configs` example config templates
- `scripts` developer scripts
- `docs` API and architecture notes
