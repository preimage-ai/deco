# Presenting Deco Studio

Start with `./scripts/demo.sh`, then open <http://localhost:8000/editor> in a browser with WebGL enabled. The demo uses local procedural assets and needs no GPU model installation, account, API key, or network access after the Python dependencies are installed.

## A three-minute walkthrough

1. **Open a space.** Click **Explore the demo studio**. The daylight studio opens with a Gaussian-splat architectural shell, six separate GLB furniture/decor pieces, and a four-second camera shot. This is a procedural sample, not a claimed AI reconstruction.
2. **Style the room.** In **Stage**, expand Linen sofa. Click **Select** to show its gizmo in the viewer; drag an axis to move it. Gizmo changes save when the drag ends. Alternatively, enter a position, rotation (radians), and scale, then click **Save**. Try hiding the rug or duplicating a piece.
3. **Compose a shot.** Open **Shots & export**. The prepared **Studio reveal** has three camera keyframes. To create your own, choose a duration, click **Create Shot**, orbit the viewer, and capture at 0 seconds. Move the camera and capture at a later time. At least two distinct keyframe times are needed for a moving shot; capturing again at the same time replaces that view.
4. **Make the film.** Choose the shot and click **Render MP4**. Start with the default 640 × 360 / 24 fps. Keep the viewer connected, visible, and the browser tab active until completion. Playback and a **Download** link appear below the room. Export speed depends on browser graphics performance.
5. **Show continuity.** Reload to demonstrate that your room edits, camera shots, and completed films persist. Click **All spaces** to browse saved projects, or **Rename** to label the project.

## Presentation notes

- Each click on the sample button creates a fresh copy. Existing edits are preserved.
- Drag to orbit, right-drag to pan, and scroll to zoom. **Reset view** returns to the first saved shot's camera pose.
- Your data is saved under `projects/` by default. Preserve that directory to retain your demo work.
- The current runtime has one shared viewer scene. Use one active editing tab during the presentation. Switching projects changes that shared scene.
- The sample is illustrative geometry. Use the import flow for a real captured Gaussian-splat PLY. A generic point-cloud PLY does not have the required Gaussian fields.
- DA3, Hunyuan, and Runway remain optional integrations. The UI reports package/configuration availability; it does not certify GPU or model readiness. Those integrations need their documented models/hardware or API credentials. The local sample/edit/export flow works independently.
- This is a local demo, not an authenticated multi-user deployment. The launcher binds to localhost by default.

## Setup on another machine

```bash
./scripts/install.sh --python python3.11 --venv .venv
./scripts/demo.sh
```

If a port is occupied:

```bash
DECO_PORT=8765 DECO_VIEWER_PORT=8088 ./scripts/demo.sh
```

Backend checks:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest apps/api/tests -q
```

A repeatable browser check creates a sample, changes furniture, reloads, exports a real clip, verifies playback, and checks the mobile layout:

```bash
.venv/bin/python scripts/smoke_demo.py --url http://localhost:8000
```

It uses installed Google Chrome when available, or Playwright Chromium (`.venv/bin/python -m playwright install chromium`). Screenshots and the verified clip are written to `/tmp/deco-browser-check`. Software rendering may take a minute or more for the four-second clip.
