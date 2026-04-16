# Architecture

Current runnable stack:

- FastAPI API for manifest-backed project CRUD and asset ingest
- Minimal server-rendered editor shell at `/editor`
- `viser` room viewer launched through the API and loaded from stored room gsplat assets plus placed mesh objects

The current viewer path is intentionally narrow:

1. Create a project
2. Upload a room `gsplat` PLY
3. Upload a mesh object (`.glb` or self-contained `.gltf`)
4. Place the object into the scene
5. Launch the room viewer
6. Inspect the splat and meshes in the embedded `viser` frame
7. Click a mesh to edit its transform with interactive gizmos

While a viewer session is active, object create, update, and delete operations are reconciled into the open scene without reloading the room splat.

This is a temporary bridge until the dedicated web editor is implemented under `apps/web`.
