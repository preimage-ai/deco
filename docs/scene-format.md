# Scene Format

The v0 manifest is a single JSON document persisted per project.

Top-level sections:

- `schema_version`
- `id`, `name`, `description`
- `assets`
- `scene`
- `trajectories`
- `created_at`, `updated_at`

The `scene` section currently stores:

- `room_asset_id`
- `objects`

Asset records now store:

- `kind`
- `role`
- `source_uri`
- `preview_uri`
- `metadata`

Each object stores:

- `id`
- `name`
- `asset_id`
- `transform`
- `visible`
- `metadata`

Each trajectory stores:

- `id`
- `name`
- `spline`
- `duration_seconds`
- `velocity`
- `keyframes`
