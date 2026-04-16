# deco

Python-first application for furnishing a room `gsplat` with 3D assets, authoring camera trajectories, and rendering enhanced output videos through a web-based editor.

## Current Status

Current runnable scope:

- FastAPI backend for project manifests, assets, scene objects, and trajectories
- Drag-and-drop room `gsplat .ply` upload flow
- Dark-themed browser editor at `/editor`
- `viser`-based room viewer launched from the editor
- Mesh object upload and placement for `.glb` and self-contained `.gltf` assets

Not implemented yet:

- Separate frontend app under `apps/web`
- Trajectory editing UI
- Final rendering pipeline

## Installation

Requirements:

- Python 3.9+

From the repository root, create or activate a virtual environment, then install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Example with `venv`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you are using the same environment as development here, launch `uvicorn` through `python -m uvicorn` so it uses the correct interpreter and installed dependencies.

## Optional Hunyuan3D Integration

This repository now includes a Hunyuan3D-backed generation path for image-to-GLB and text-to-GLB asset creation.

Install the optional runtime like this:

```bash
python -m pip install -r requirements-hunyuan.txt
python -m pip install -e external/Hunyuan3D-2
```

Relevant environment variables:

- `DECO_HUNYUAN_REPO_PATH`
  local checkout path, default `external/Hunyuan3D-2`
- `DECO_HUNYUAN_SHAPE_MODEL`
  shape model id, default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_SHAPE_SUBFOLDER`
  shape model subfolder, default `hunyuan3d-dit-v2-0`
- `DECO_HUNYUAN_TEXTURE_MODEL`
  texture model id, default `tencent/Hunyuan3D-2`
- `DECO_HUNYUAN_TEXT2IMAGE_MODEL`
  text-to-image model id, default `Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled`
- `DECO_HUNYUAN_DEVICE`
  device override, default `auto`

Generation endpoints:

- `POST /projects/{project_id}/assets/generate-from-image`
  multipart form upload plus Hunyuan generation params
- `POST /projects/{project_id}/assets/generate-from-text`
  JSON prompt payload plus Hunyuan generation params

This implementation currently guards against CPU-only execution by returning `503` when CUDA is unavailable, because the upstream models are configured for GPU workloads and are not practical on this machine.

## Runway Enhancement

Rendered trajectory videos can now be post-processed with Runway Aleph video-to-video.

Configuration is read from environment variables or the repository-root `.env` file:

- `DECO_RUNWAY_API_KEY`
  Runway API key
- `DECO_RUNWAY_API_VERSION`
  default `2024-11-06`
- `DECO_RUNWAY_VIDEO_MODEL`
  default `gen4_aleph`
- `DECO_RUNWAY_VIDEO_PROMPT`
  prompt used for post-processing
- `DECO_RUNWAY_POLL_INTERVAL_SECONDS`
  task polling interval, default `5`

Render request fields:

- `enhance_with_ai`
  when `true`, the rendered MP4 is uploaded to Runway after local render
- `ai_wait_timeout_seconds`
  how long the API waits for the Runway task before returning a pending status

When enhancement succeeds, the response includes an `enhancement` object with task metadata and an artifact URL for the downloaded enhanced MP4 under the project `renders/` directory.

## Run The App

Start the API server from the repository root:

```bash
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

Then open:

- `http://localhost:8000/docs` for the FastAPI docs
- `http://localhost:8000/editor` for the temporary upload-and-view UI

## Editor Flow

The current `/editor` page is a temporary frontend served directly by FastAPI.

Use it like this:

1. Drop a room `gsplat` PLY file onto the landing screen
2. The editor creates a fresh scene and launches the viewer automatically
3. Drop mesh objects as `.glb` or self-contained `.gltf` files into the mesh dropzone
4. New meshes appear in the active viewer without reloading it
5. Click a mesh in the viewer to reveal move and rotate gizmos, then drag it interactively
6. Create shots, capture keyframes, and render trajectory MP4s from the side rail

Once the viewer is open, newly placed objects are synced into the active scene without relaunching it.

`.gltf` uploads currently need to be self-contained. External `.bin` buffers or texture files are not copied into the project yet.

The `viser` viewer runs on port `8080` by default.

## Environment Variables

Optional configuration:

- `DECO_PROJECTS_ROOT`
  path for stored projects and uploaded assets
- `DECO_VIEWER_HOST`
  bind host for the `viser` server, default `0.0.0.0`
- `DECO_VIEWER_PORT`
  port for the `viser` server, default `8080`
- `DECO_VIEWER_PUBLIC_HOST`
  host used in the browser iframe URL, default `localhost`

Example:

```bash
DECO_PROJECTS_ROOT=./projects \
DECO_VIEWER_HOST=0.0.0.0 \
DECO_VIEWER_PORT=8080 \
DECO_VIEWER_PUBLIC_HOST=localhost \
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
```

## Run Tests

This environment has a broken globally installed Hydra pytest plugin, so tests should be run with plugin autoload disabled:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest apps/api/tests -q
```

## Repository Layout

- `apps/api` FastAPI application and orchestration layer
- `apps/web` Web frontend for scene editing, trajectories, and job monitoring
- `services` Python domain packages for scene state, assets, rendering, jobs, and storage
- `projects` Local project and artifact storage
- `configs` Runtime and model configuration templates
- `scripts` Development and worker entrypoints
- `docs` Architecture and API notes
- `tests` Integration and end-to-end coverage
