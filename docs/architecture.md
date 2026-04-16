# Architecture

Current runnable stack:

- FastAPI API for manifest-backed project CRUD and asset ingest
- Minimal server-rendered editor shell at `/editor`
- Optional Depth Anything 3 image-to-gsplat generation path
- `viser` room viewer launched through the API and loaded from stored room gsplat assets plus placed mesh objects

The current editor now has two entry workflows:

- `Gsplat creation workflow`
- Upload input images
- Run Depth Anything 3 to generate a room gsplat PLY
- Register that generated PLY as the active room asset
- Launch the room in the embedded `viser` frame
- Allow the generated PLY to be downloaded from the workspace header

- `Normal gsplat editing and video rendering workflow`
- Drop a room `gsplat` PLY into the landing screen
- Auto-create a scene and launch the room viewer
- Drop mesh objects (`.glb` or self-contained `.gltf`) into the active workspace
- Inspect the splat and meshes in the embedded `viser` frame
- Click a mesh to edit its transform with interactive gizmos

While a viewer session is active, object create, update, and delete operations are reconciled into the open scene without reloading the room splat.

This is a temporary bridge until the dedicated web editor is implemented under `apps/web`.
