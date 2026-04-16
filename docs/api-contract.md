# API Contract

Current backend scope:

- `GET /healthz`
- `GET|POST /projects`
- `GET|PATCH|DELETE /projects/{project_id}`
- `GET|POST /projects/{project_id}/assets`
- `POST /projects/{project_id}/assets/upload-room`
- `POST /projects/{project_id}/assets/upload-object`
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

Object uploads support `.glb` and self-contained `.gltf`.
