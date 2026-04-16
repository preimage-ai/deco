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

## Requirements

- Python 3.9+
- `fastapi`
- `uvicorn`
- `pydantic`
- `viser`
- `plyfile`
- `numpy`
- `python-multipart`
- `pytest` for tests

Optional for `.gltf` object support:

- `trimesh`

If you are using the same environment as development here, launch `uvicorn` through `python -m uvicorn` so it uses the correct interpreter and installed dependencies.

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
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest apps/api/tests -q
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
