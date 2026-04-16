# Architecture

Current runnable stack:

- FastAPI API for manifest-backed project CRUD and asset ingest
- Minimal server-rendered editor shell at `/editor`
- `viser` room viewer launched through the API and loaded from stored room gsplat assets plus placed mesh objects

The current viewer path is intentionally narrow:

1. Drop a room `gsplat` PLY into the landing screen
2. Auto-create a scene and launch the room viewer
3. Drop mesh objects (`.glb` or self-contained `.gltf`) into the active workspace
4. Inspect the splat and meshes in the embedded `viser` frame
5. Click a mesh to edit its transform with interactive gizmos

While a viewer session is active, object create, update, and delete operations are reconciled into the open scene without reloading the room splat.

This is a temporary bridge until the dedicated web editor is implemented under `apps/web`.
