# API Contract

Current backend scope:

- `GET /healthz`
- `POST /generation/create-gsplat`
- `GET|POST /projects`
- `GET|PATCH|DELETE /projects/{project_id}`
- `GET|POST /projects/{project_id}/assets`
- `POST /projects/{project_id}/assets/upload-room`
- `POST /projects/{project_id}/assets/upload-object`
- `GET /projects/{project_id}/assets/{asset_id}/download`
- `GET|PATCH|DELETE /projects/{project_id}/assets/{asset_id}`
- `POST /projects/{project_id}/viewer/load-room`
- `GET /projects/{project_id}/scene`
- `GET|POST /projects/{project_id}/objects`
- `GET|PATCH|DELETE /projects/{project_id}/objects/{object_id}`
- `GET|POST /projects/{project_id}/trajectories`
- `GET|PATCH|DELETE /projects/{project_id}/trajectories/{trajectory_id}`
- `GET /editor`

Project data is persisted as `projects/<project_id>/manifest.json`.

Uploaded files are stored under:

- `projects/<project_id>/assets/rooms/`
- `projects/<project_id>/assets/objects/`
- `projects/<project_id>/inputs/da3/` for source images used in DA3 generation
- `projects/<project_id>/generation/da3/` for intermediate DA3 exports

Object uploads support `.glb` and self-contained `.gltf`.

Image-to-gsplat generation accepts common image formats such as `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, and `.tiff`.


## Demo and saved exports

- `POST /demo/projects` creates a fresh procedural sample with a room splat, six mesh assets/instances, and a prepared camera trajectory. It returns the project manifest and does not overwrite existing samples.
- `GET /capabilities` reports optional runtime package/API-key availability without loading model weights or exposing credentials.
- `GET /projects/{project_id}/renders` lists completed MP4 files with artifact URLs and byte sizes, newest first. In-progress `.partial.mp4` files are excluded.
- `GET /` redirects to `/editor`; `/static` serves the studio frontend assets.

Capturing a keyframe at an existing timestamp replaces that view. Render dimensions must be even, width 64–3840, height 64–2160, and FPS 1–60. Trajectory durations and keyframe times are bounded to 300 seconds. Local video exports require a connected browser viewer.


## Optional Astra procedural objects

- `POST /projects/{project_id}/assets/astra/from-text`: JSON `prompt` (1–4000 characters), optional `name` (1–120). Requires a server-side OpenAI key.
- `POST /projects/{project_id}/assets/astra/from-image`: multipart `file` (up to 20 MB), optional `name` and `prompt`. Sends a resized reference image to OpenAI.
- Both return `AssetUploadResponse`, create a real generated GLB and persist a bounded primitive recipe. They register an asset; the editor separately places it as an object.
- `/capabilities` includes `astra`, indicating key configuration only, not verified account access.
- Runway model `aleph2` omits the legacy `ratio` request parameter. See [the integration guide](ai-integrations.md) for setup and limitations.
