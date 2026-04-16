# Deco Room GSplat Studio

Deco is a FastAPI-based workspace for turning room photos or existing `gsplat` captures into editable scenes, placing 3D assets, authoring camera shots, and rendering video output from the browser.

It combines a local project store, a server-rendered editor at `/editor`, a live `viser` viewer session, and optional AI-assisted generation paths for room splats, object meshes, and post-processed renders.

## Features

- Project, asset, scene, trajectory, and render management through a FastAPI backend
- Browser-based editor served at `/editor`
- Room creation from image sets through optional Depth Anything 3 integration
- Existing room `.ply` upload and live `viser` viewer launch
- Object upload for `.glb` and self-contained `.gltf`
- Hunyuan3D object generation from image or text prompt
- Trajectory capture, keyframe authoring, and local MP4 rendering
- Optional Runway Aleph enhancement for rendered videos

## Architecture

The current runtime stack includes:

- `apps/api`: FastAPI application, API routes, orchestration, and tests
- `services`: generation, rendering, storage, viewer, and scene-state packages
- `projects`: local artifact and manifest store
- `scripts`: installation and development helper scripts
- `docs`: API contract and architecture notes

The browser UI is currently served from the API app at `/editor`. The `apps/web` directory remains reserved for a future standalone frontend.

## Quick Start

### Requirements

- Python 3.10+
- CUDA-capable GPU for practical Hunyuan3D or DA3 generation workloads

### Install

Use the shared install script from the repository root:

```bash
chmod +x scripts/install.sh
./scripts/install.sh --venv .venv --with-hunyuan --with-da3
source .venv/bin/activate
```

This installs:

- base runtime requirements from `requirements.txt`
- optional Depth Anything 3 runtime from `requirements-da3.txt`
- optional Hunyuan3D runtime from `requirements-hunyuan.txt`

Common options:

- `--with-da3` installs DA3 support
- `--with-hunyuan` installs Hunyuan3D support
- `--hunyuan-repo /path/to/Hunyuan3D-2` uses an explicit local Hunyuan checkout override
- `--skip-venv` installs into the active interpreter
- `--python python3.10` selects a specific Python executable

### Run

Start the API server from the repository root:

```bash
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

Then open:

- `http://localhost:8000/docs`
- `http://localhost:8000/editor`

The embedded `viser` viewer runs on port `8080` by default.

## Editor Workflow

The `/editor` flow supports two room entry paths:

1. Generate a room splat from overlapping input images through `POST /generation/create-gsplat`
2. Upload an existing room `.ply` through `POST /projects/{project_id}/assets/upload-room`

Once a room is loaded, the editor supports:

- object upload with `.glb` and self-contained `.gltf`
- object generation through Hunyuan3D image-to-3D and text-to-3D routes
- live object placement and transforms inside the viewer
- trajectory creation and keyframe capture
- local MP4 rendering
- optional Runway enhancement via `POST /projects/{project_id}/renders/{filename}/enhance`

`.gltf` uploads must currently be self-contained. External `.bin` buffers and sidecar textures are not copied into the project store.

## Model and Runtime Sourcing

Deco is configured to be pip- and Hugging Face-first by default.

### Depth Anything 3

- Python package source: `requirements-da3.txt`
- Default model: `depth-anything/DA3NESTED-GIANT-LARGE-1.1`
- Override variable: `DECO_DA3_MODEL`

If `DECO_DA3_MODEL` is unset, Deco loads the default DA3 model from Hugging Face. To use a local checkpoint, set `DECO_DA3_MODEL` explicitly to a local directory path.

### Hunyuan3D

- Python package source: `requirements-hunyuan.txt`
- Default shape model: `tencent/Hunyuan3D-2`
- Default text-to-image model: `Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled`
- Optional local code override: `DECO_HUNYUAN_REPO_PATH`

By default, Deco uses the pip-installed `hy3dgen` runtime and Hugging Face model ids. Use `DECO_HUNYUAN_REPO_PATH` only if you explicitly want to override the installed runtime with a local checkout.

Texture generation may still require native Hunyuan rasterizer extensions. If those extensions are unavailable, retry with `include_texture=false`.

## Configuration

General runtime settings:

- `DECO_PROJECTS_ROOT` default `projects`
- `DECO_VIEWER_HOST` default `0.0.0.0`
- `DECO_VIEWER_PORT` default `8080`
- `DECO_VIEWER_PUBLIC_HOST` default `localhost`

DA3 settings:

- `DECO_DA3_MODEL` default `depth-anything/DA3NESTED-GIANT-LARGE-1.1`
- `DECO_DA3_DEVICE` default `auto`
- `DECO_DA3_PROCESS_RES` default `504`

Hunyuan settings:

- `DECO_HUNYUAN_REPO_PATH` optional explicit local checkout override
- `DECO_HUNYUAN_SHAPE_MODEL` default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_SHAPE_SUBFOLDER` default `hunyuan3d-dit-v2-0`
- `DECO_HUNYUAN_TEXTURE_MODEL` default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_TEXT2IMAGE_MODEL` default `Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled`
- `DECO_HUNYUAN_DEVICE` default `auto`

Runway settings:

- `DECO_RUNWAY_API_KEY`
- `DECO_RUNWAY_API_VERSION` default `2024-11-06`
- `DECO_RUNWAY_VIDEO_MODEL` default `gen4_aleph`
- `DECO_RUNWAY_VIDEO_PROMPT`
- `DECO_RUNWAY_POLL_INTERVAL_SECONDS` default `5`

The app also accepts `RUNWAYML_API_SECRET` as a fallback API key source.

Example:

```bash
DECO_PROJECTS_ROOT=./projects \
DECO_VIEWER_HOST=0.0.0.0 \
DECO_VIEWER_PORT=8080 \
DECO_VIEWER_PUBLIC_HOST=localhost \
DECO_DA3_MODEL=depth-anything/DA3NESTED-GIANT-LARGE-1.1 \
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

## API Surface

Current backend scope includes:

- `GET /healthz`
- `GET /docs`
- `GET /editor`
- `POST /generation/create-gsplat`
- project CRUD under `/projects`
- asset upload, download, and generation routes under `/projects/{project_id}/assets`
- scene object CRUD under `/projects/{project_id}/objects`
- trajectory CRUD and render routes under `/projects/{project_id}/trajectories`
- render enhancement and artifact download under `/projects/{project_id}/renders`
- viewer launch routes under `/projects/{project_id}/viewer`

Additional details are documented in [docs/api-contract.md](/home/altair/preimage/deco/docs/api-contract.md).

## Development

Run tests with plugin autoload disabled in this environment:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/api/tests -q
```

For a narrower verification pass:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/api/tests/test_app_bootstrap.py -q
```

## Repository Layout

- `apps/api` FastAPI application, dependency wiring, API routes, and tests
- `apps/web` reserved for a future standalone frontend
- `services` domain packages for generation, rendering, storage, viewer, and scene state
- `projects` local project and artifact storage
- `configs` example configuration templates
- `scripts` install and helper scripts
- `docs` architecture and API documentation
