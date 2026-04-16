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
