"""Viewer routes and minimal editor page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.orchestration.viewer_service import MissingViewerDependencyError
from apps.api.app.schemas.viewer import ViewerLaunchRequest, ViewerLaunchResponse
from services.preview.mesh_loader import InvalidMeshAssetError, MissingMeshDependencyError
from services.preview.viser_scene import InvalidGaussianSplatError
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(tags=["viewer"])


@router.get("/editor", response_class=HTMLResponse)
def editor_page(_repo: ProjectRepository = Depends(get_repo)) -> str:
    """Serve a drag-and-drop-first editor shell for room and mesh uploads."""
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>deco editor</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #07111f;
        --bg-glow: #11223d;
        --panel: rgba(12, 24, 42, 0.84);
        --panel-strong: rgba(15, 31, 52, 0.96);
        --ink: #f2f7ff;
        --muted: #9eafc7;
        --line: rgba(149, 179, 222, 0.16);
        --line-strong: rgba(149, 179, 222, 0.28);
        --accent: #6ee7c8;
        --accent-strong: #4dd2ff;
        --shadow: 0 32px 90px rgba(3, 8, 18, 0.45);
        --radius-xl: 28px;
        --radius-lg: 22px;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Sora", "Avenir Next", "Helvetica Neue", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(78, 152, 255, 0.18), transparent 30%),
          radial-gradient(circle at top right, rgba(110, 231, 200, 0.16), transparent 28%),
          linear-gradient(180deg, var(--bg-glow), var(--bg));
        color: var(--ink);
      }
      button, input, select, video {
        font: inherit;
      }
      button, input, select {
        border: 1px solid var(--line);
        outline: none;
      }
      button {
        cursor: pointer;
      }
      [hidden] {
        display: none !important;
      }
      .shell {
        min-height: 100vh;
        padding: 28px;
      }
      .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 12px;
        color: var(--accent);
      }
      .eyebrow::before {
        content: "";
        width: 28px;
        height: 1px;
        background: currentColor;
      }
      .landing {
        min-height: calc(100vh - 56px);
        display: grid;
        place-items: center;
      }
      .landing-card {
        width: min(820px, 100%);
        padding: 36px;
        border-radius: var(--radius-xl);
        background: linear-gradient(145deg, rgba(16, 31, 53, 0.92), rgba(10, 18, 31, 0.94));
        border: 1px solid var(--line-strong);
        box-shadow: var(--shadow);
      }
      .workflow-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
      }
      .workflow-card {
        width: 100%;
        padding: 24px;
        border-radius: calc(var(--radius-xl) - 6px);
        border: 1px solid var(--line);
        background: linear-gradient(180deg, rgba(13, 26, 46, 0.9), rgba(9, 16, 30, 0.92));
        color: var(--ink);
        display: grid;
        gap: 14px;
        text-align: left;
        box-shadow: var(--shadow);
        transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
      }
      .workflow-card:hover {
        transform: translateY(-2px);
        border-color: rgba(110, 231, 200, 0.42);
        background: linear-gradient(180deg, rgba(16, 31, 53, 0.96), rgba(9, 16, 30, 0.98));
      }
      .workflow-card h2 {
        margin: 0;
        font-size: 24px;
        letter-spacing: -0.04em;
      }
      .workflow-card p {
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }
      .landing-copy,
      .workspace-header-copy,
      .stack,
      .rail,
      .stage-column,
      .workspace {
        display: grid;
        gap: 18px;
      }
      .landing-copy h1,
      .workspace-title {
        margin: 0;
        font-size: clamp(38px, 7vw, 68px);
        line-height: 0.95;
        letter-spacing: -0.05em;
      }
      .landing-copy p,
      .viewer-note,
      .panel p,
      .status-card p,
      .meta-copy {
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }
      .dropzone {
        display: grid;
        gap: 16px;
        padding: 28px;
        border-radius: calc(var(--radius-xl) - 4px);
        border: 1px dashed rgba(110, 231, 200, 0.38);
        background: linear-gradient(180deg, rgba(110, 231, 200, 0.06), rgba(77, 210, 255, 0.03));
        transition: border-color 180ms ease, transform 180ms ease, background 180ms ease;
      }
      .dropzone.is-dragging,
      .dropzone:hover {
        border-color: rgba(110, 231, 200, 0.82);
        background: linear-gradient(180deg, rgba(110, 231, 200, 0.12), rgba(77, 210, 255, 0.08));
        transform: translateY(-2px);
      }
      .dropzone h2,
      .panel h2,
      .render-card h2 {
        margin: 0;
        font-size: 20px;
        letter-spacing: -0.03em;
      }
      .chip-row,
      .cta-row,
      .workspace-header,
      .workspace-header-actions,
      .panel-header,
      .stage-header,
      .render-header,
      .action-row,
      .inline-grid {
        display: flex;
        gap: 12px;
      }
      .chip-row,
      .cta-row,
      .workspace-header-actions,
      .action-row {
        flex-wrap: wrap;
      }
      .workspace-header,
      .panel-header,
      .stage-header,
      .render-header {
        justify-content: space-between;
        align-items: center;
      }
      .pill,
      .stat-pill,
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--line);
        color: var(--ink);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .button {
        border: none;
        border-radius: 999px;
        padding: 13px 18px;
        font-weight: 600;
        transition: transform 180ms ease, box-shadow 180ms ease;
      }
      a.button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
      }
      .button:hover {
        transform: translateY(-1px);
      }
      .button-primary {
        color: #031019;
        background: linear-gradient(135deg, var(--accent), var(--accent-strong));
        box-shadow: 0 16px 32px rgba(77, 210, 255, 0.22);
      }
      .button-secondary {
        color: var(--ink);
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--line-strong);
      }
      .workspace-grid {
        display: grid;
        grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
        gap: 20px;
        align-items: start;
      }
      .panel,
      .stage-panel,
      .render-card,
      .status-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow);
        backdrop-filter: blur(22px);
      }
      .panel,
      .status-card,
      .stage-panel,
      .render-card {
        padding: 20px;
      }
      label {
        display: grid;
        gap: 6px;
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }
      input,
      select {
        width: 100%;
        padding: 14px 16px;
        border-radius: 14px;
        background: rgba(4, 10, 20, 0.5);
        color: var(--ink);
      }
      .inline-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .stage-frame {
        position: relative;
        min-height: 720px;
        border-radius: calc(var(--radius-lg) - 4px);
        overflow: hidden;
        border: 1px solid rgba(149, 179, 222, 0.14);
        background: linear-gradient(180deg, rgba(6, 12, 23, 0.84), rgba(6, 12, 23, 0.92));
      }
      iframe,
      video {
        width: 100%;
        min-height: 100%;
        border: 0;
        border-radius: calc(var(--radius-lg) - 4px);
        background: rgba(4, 8, 16, 0.8);
      }
      .stage-hint {
        position: absolute;
        inset: 18px;
        display: grid;
        place-items: center;
        text-align: center;
        padding: 24px;
        border-radius: 22px;
        border: 1px dashed rgba(110, 231, 200, 0.24);
        background: rgba(6, 12, 24, 0.46);
        color: var(--muted);
        pointer-events: none;
      }
      .status-card {
        min-height: 108px;
        white-space: pre-wrap;
      }
      .status-card[data-tone="error"] {
        border-color: rgba(255, 143, 143, 0.28);
      }
      .status-card[data-tone="success"] {
        border-color: rgba(110, 231, 200, 0.26);
      }
      .status-label {
        margin-bottom: 12px;
        color: var(--muted);
        font-size: 12px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }
      .flash-banner {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10;
        width: min(420px, calc(100vw - 40px));
        padding: 14px 16px;
        border-radius: 18px;
        border: 1px solid var(--line);
        background: rgba(12, 24, 42, 0.92);
        box-shadow: var(--shadow);
        color: var(--ink);
        backdrop-filter: blur(20px);
      }
      .flash-banner[data-tone="error"] {
        border-color: rgba(255, 143, 143, 0.34);
      }
      .flash-banner[data-tone="success"] {
        border-color: rgba(110, 231, 200, 0.34);
      }
      .badge-live::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--accent);
      }
      .ghost-note {
        font-size: 13px;
        color: var(--muted);
      }
      .file-input {
        display: none;
      }
      @media (max-width: 900px) {
        .shell {
          padding: 18px;
        }
        .workflow-grid {
          grid-template-columns: 1fr;
        }
        .workspace-grid {
          grid-template-columns: 1fr;
        }
        .workspace-header {
          flex-direction: column;
          align-items: flex-start;
        }
        .stage-frame {
          min-height: 520px;
        }
        .inline-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <div id="flash-banner" class="flash-banner" data-tone="info" hidden>Choose a workflow to begin.</div>

      <section id="landing" class="landing">
        <div class="landing-card">
          <div class="landing-copy">
            <span class="eyebrow">deco studio</span>
            <h1>Choose your gsplat workflow.</h1>
            <p>Start from images with Depth Anything 3 or jump straight into editing an existing room splat. Both paths land in the same live viewer and render workspace.</p>
          </div>
          <div class="workflow-grid">
            <button id="workflow-create-button" class="workflow-card" type="button">
              <span class="pill">Depth Anything 3</span>
              <h2>Gsplat creation workflow</h2>
              <p>Drop a set of overlapping images, generate a fresh room splat, preview it immediately, and save the resulting `.ply` to disk.</p>
            </button>
            <button id="workflow-edit-button" class="workflow-card" type="button">
              <span class="pill">Editor + render</span>
              <h2>Normal gsplat editing and video rendering workflow</h2>
              <p>Open an existing room `.ply`, place `.glb` or `.gltf` meshes into the live viewer, and capture keyframes for video rendering.</p>
            </button>
          </div>
        </div>
      </section>

      <section id="editing-landing" class="landing" hidden>
        <div class="landing-card">
          <div class="landing-copy">
            <span class="eyebrow">existing gsplat</span>
            <h1>Drop a Gaussian Splat to begin.</h1>
            <p>Bring in a room `.ply` file and the editor will create a fresh scene, launch the viewer, and get you ready to place meshes immediately.</p>
          </div>
          <div id="room-dropzone" class="dropzone" tabindex="0">
            <div class="chip-row">
              <span class="pill">Input `.ply`</span>
              <span class="pill">Auto scene setup</span>
              <span class="pill">Viewer launches itself</span>
            </div>
            <h2>Drag and drop your gsplat room here</h2>
            <p class="meta-copy">No project setup, no naming, no extra clicks. If you prefer, click to browse for a file.</p>
            <div class="cta-row">
              <button id="room-browse-button" class="button button-primary" type="button">Choose `.ply`</button>
              <button id="editing-back-button" class="button button-secondary" type="button">Back</button>
              <span class="ghost-note">The first drop creates a new scene automatically.</span>
            </div>
          </div>
        </div>
      </section>

      <section id="creation-landing" class="landing" hidden>
        <div class="landing-card">
          <div class="landing-copy">
            <span class="eyebrow">image to gsplat</span>
            <h1>Drop images to generate a room splat.</h1>
            <p>Upload a small set of overlapping room photos and deco will run Depth Anything 3, open the resulting gsplat in the viewer, and give you a one-click download for the generated `.ply`.</p>
          </div>
          <div id="generation-dropzone" class="dropzone" tabindex="0">
            <div class="chip-row">
              <span class="pill">Multi-image input</span>
              <span class="pill">Auto gsplat generation</span>
              <span class="pill">Viewer launches itself</span>
            </div>
            <h2>Drag and drop your input images here</h2>
            <p class="meta-copy">Use `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, or `.tiff`. The first run may take longer because the DA3 model weights may need to download.</p>
            <div class="cta-row">
              <button id="generation-browse-button" class="button button-primary" type="button">Choose images</button>
              <button id="creation-back-button" class="button button-secondary" type="button">Back</button>
              <span class="ghost-note">Overlapping views usually produce a stronger splat.</span>
            </div>
          </div>
        </div>
      </section>

      <section id="workspace" class="workspace" hidden>
        <header class="workspace-header">
          <div class="workspace-header-copy">
            <span class="eyebrow">deco studio</span>
            <h1 class="workspace-title" id="scene-title">Fresh Scene</h1>
            <p class="viewer-note" id="scene-subtitle">Drop meshes, drag them into place in the viewer, and capture camera motion once the composition feels right.</p>
          </div>
          <div class="workspace-header-actions">
            <span class="stat-pill"><strong id="scene-object-count">0</strong> meshes</span>
            <span class="stat-pill"><strong id="scene-trajectory-count">0</strong> shots</span>
            <a id="download-room-link" class="button button-secondary" href="#" download hidden>Download GSplat</a>
            <button id="new-scene-button" class="button button-secondary" type="button">Start New Scene</button>
          </div>
        </header>

        <section class="workspace-grid">
          <aside class="rail">
            <div id="mesh-dropzone" class="panel dropzone" tabindex="0">
              <div class="chip-row">
                <span class="pill">Mesh `.glb` / `.gltf`</span>
                <span class="pill">Live placement</span>
              </div>
              <h2>Drop a mesh into the scene</h2>
              <p>Meshes are uploaded, instantiated, and inserted into the active viewer automatically. Then you can drag them into place with the gizmo.</p>
              <div class="cta-row">
                <button id="mesh-browse-button" class="button button-primary" type="button">Choose mesh</button>
                <span class="ghost-note">New objects appear without reloading the viewer.</span>
              </div>
            </div>

            <form id="trajectory-form" class="panel stack">
              <div class="panel-header">
                <div>
                  <h2>Shot Builder</h2>
                  <p>Create a trajectory once and keep capturing camera keyframes into it.</p>
                </div>
                <span class="badge">camera</span>
              </div>
              <label>
                Duration
                <input id="trajectory-duration" name="duration_seconds" type="number" min="1" step="0.1" value="5" />
              </label>
              <div class="action-row">
                <button class="button button-primary" type="submit">Create Shot</button>
                <span class="ghost-note" id="trajectory-draft-name">Next: Shot 1</span>
              </div>
            </form>

            <form id="keyframe-form" class="panel stack">
              <div class="panel-header">
                <div>
                  <h2>Keyframes</h2>
                  <p>Capture the current viewer camera into the selected shot.</p>
                </div>
                <span class="badge">record</span>
              </div>
              <label>
                Shot
                <select id="trajectory-select" name="trajectory_id">
                  <option value="">No shots yet</option>
                </select>
              </label>
              <label>
                Time (seconds)
                <input id="keyframe-time" name="time_seconds" type="number" min="0" step="0.1" value="0" />
              </label>
              <button id="capture-keyframe-button" class="button button-secondary" type="submit">Capture Keyframe</button>
            </form>

            <form id="render-form" class="panel stack">
              <div class="panel-header">
                <div>
                  <h2>Render</h2>
                  <p>Generate an MP4 from the selected shot while the viewer tab stays connected.</p>
                </div>
                <span class="badge">export</span>
              </div>
              <label>
                Shot
                <select id="render-trajectory-select" name="trajectory_id">
                  <option value="">No shots yet</option>
                </select>
              </label>
              <div class="inline-grid">
                <label>
                  FPS
                  <input id="render-fps" name="fps" type="number" min="1" step="1" value="24" />
                </label>
                <label>
                  Width
                  <input id="render-width" name="width" type="number" min="64" step="1" value="1280" />
                </label>
                <label>
                  Height
                  <input id="render-height" name="height" type="number" min="64" step="1" value="720" />
                </label>
              </div>
              <button id="render-button" class="button button-primary" type="submit">Render MP4</button>
            </form>

            <div id="status-card" class="status-card" data-tone="info">
              <div class="status-label">Status</div>
              <div id="status">Choose a workflow to begin.</div>
            </div>
          </aside>

          <div class="stage-column">
            <section class="stage-panel">
              <div class="stage-header">
                <div>
                  <h2>Viewer Stage</h2>
                  <p class="viewer-note">Click any mesh in the viewer to reveal move and rotate gizmos. Drop more meshes from the left rail whenever you need them.</p>
                </div>
                <span id="viewer-badge" class="badge">waiting</span>
              </div>
              <div class="stage-frame">
                <iframe id="viewer-frame" title="viser viewer"></iframe>
                <div id="stage-hint" class="stage-hint">
                  <div>
                    <strong>The viewer will appear here.</strong>
                    <div>Load or generate a room, then drop meshes into the scene.</div>
                  </div>
                </div>
              </div>
            </section>

            <section class="render-card">
              <div class="render-header">
                <div>
                  <h2>Playback</h2>
                  <p class="viewer-note">Rendered clips show up here as soon as the export finishes.</p>
                </div>
                <span class="badge badge-live">preview</span>
              </div>
              <video id="render-video" controls></video>
            </section>
          </div>
        </section>
      </section>
    </div>

    <input id="room-file-input" class="file-input" type="file" accept=".ply" />
    <input id="generation-file-input" class="file-input" type="file" accept=".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff" multiple />
    <input id="mesh-file-input" class="file-input" type="file" accept=".glb,.gltf" />

    <script>
      const PROJECT_STORAGE_KEY = "deco_active_project_id";
      const landing = document.getElementById("landing");
      const editingLanding = document.getElementById("editing-landing");
      const creationLanding = document.getElementById("creation-landing");
      const workspace = document.getElementById("workspace");
      const roomDropzone = document.getElementById("room-dropzone");
      const generationDropzone = document.getElementById("generation-dropzone");
      const meshDropzone = document.getElementById("mesh-dropzone");
      const roomFileInput = document.getElementById("room-file-input");
      const generationFileInput = document.getElementById("generation-file-input");
      const meshFileInput = document.getElementById("mesh-file-input");
      const workflowCreateButton = document.getElementById("workflow-create-button");
      const workflowEditButton = document.getElementById("workflow-edit-button");
      const roomBrowseButton = document.getElementById("room-browse-button");
      const generationBrowseButton = document.getElementById("generation-browse-button");
      const meshBrowseButton = document.getElementById("mesh-browse-button");
      const editingBackButton = document.getElementById("editing-back-button");
      const creationBackButton = document.getElementById("creation-back-button");
      const newSceneButton = document.getElementById("new-scene-button");
      const downloadRoomLink = document.getElementById("download-room-link");
      const sceneTitle = document.getElementById("scene-title");
      const sceneSubtitle = document.getElementById("scene-subtitle");
      const sceneObjectCount = document.getElementById("scene-object-count");
      const sceneTrajectoryCount = document.getElementById("scene-trajectory-count");
      const viewerBadge = document.getElementById("viewer-badge");
      const stageHint = document.getElementById("stage-hint");
      const trajectorySelect = document.getElementById("trajectory-select");
      const renderTrajectorySelect = document.getElementById("render-trajectory-select");
      const trajectoryDuration = document.getElementById("trajectory-duration");
      const trajectoryDraftName = document.getElementById("trajectory-draft-name");
      const keyframeTimeInput = document.getElementById("keyframe-time");
      const captureKeyframeButton = document.getElementById("capture-keyframe-button");
      const renderButton = document.getElementById("render-button");
      const renderFpsInput = document.getElementById("render-fps");
      const renderWidthInput = document.getElementById("render-width");
      const renderHeightInput = document.getElementById("render-height");
      const statusCard = document.getElementById("status-card");
      const statusEl = document.getElementById("status");
      const flashBanner = document.getElementById("flash-banner");
      const viewerFrame = document.getElementById("viewer-frame");
      const renderVideo = document.getElementById("render-video");
      const STAGE_DEFAULT_HINT = "<div><strong>The viewer will appear here.</strong><div>Load or generate a room, then drop meshes into the scene.</div></div>";

      const state = {
        projectId: null,
        projectName: null,
        roomAssetId: null,
        objectCount: 0,
        trajectories: [],
        workflowMode: null,
      };

      function setStatus(message, tone = "info") {
        statusCard.dataset.tone = tone;
        statusEl.textContent = message;
        flashBanner.dataset.tone = tone;
        flashBanner.textContent = message;
        flashBanner.hidden = !message;
      }

      function showWorkflowSelector() {
        landing.hidden = false;
        editingLanding.hidden = true;
        creationLanding.hidden = true;
        workspace.hidden = true;
      }

      function showEditingLanding() {
        landing.hidden = true;
        editingLanding.hidden = false;
        creationLanding.hidden = true;
        workspace.hidden = true;
      }

      function showCreationLanding() {
        landing.hidden = true;
        editingLanding.hidden = true;
        creationLanding.hidden = false;
        workspace.hidden = true;
      }

      function showWorkspace() {
        landing.hidden = true;
        editingLanding.hidden = true;
        creationLanding.hidden = true;
        workspace.hidden = false;
      }

      function updateDownloadLink() {
        if (!state.projectId || !state.roomAssetId) {
          downloadRoomLink.hidden = true;
          downloadRoomLink.removeAttribute("href");
          return;
        }
        downloadRoomLink.hidden = false;
        downloadRoomLink.href = `/projects/${state.projectId}/assets/${state.roomAssetId}/download`;
      }

      function formatSceneLabel() {
        return state.projectName || (state.projectId ? `Scene ${state.projectId.slice(-6)}` : "Fresh Scene");
      }

      function updateSceneChrome() {
        sceneTitle.textContent = formatSceneLabel();
        if (state.roomAssetId) {
          sceneSubtitle.textContent = "Drop meshes, then click them inside the viewer to reveal move and rotate gizmos.";
        } else if (state.workflowMode === "create") {
          sceneSubtitle.textContent = "Drop overlapping images to generate a room splat with Depth Anything 3.";
        } else {
          sceneSubtitle.textContent = "Upload a room `.ply` to activate the viewer stage.";
        }
        sceneObjectCount.textContent = String(state.objectCount);
        sceneTrajectoryCount.textContent = String(state.trajectories.length);
        updateDownloadLink();
      }

      function setViewerBadge(label, isLive = false) {
        viewerBadge.textContent = label;
        viewerBadge.className = isLive ? "badge badge-live" : "badge";
      }

      function fileStem(filename) {
        return String(filename || "").replace(/\\.[^.]+$/, "");
      }

      function humanizeName(filename) {
        const base = fileStem(filename).replace(/[_-]+/g, " ").trim();
        return base ? base.replace(/\\b\\w/g, (match) => match.toUpperCase()) : "Mesh";
      }

      function pluralize(count, noun) {
        return `${count} ${noun}${count === 1 ? "" : "s"}`;
      }

      function isExtension(file, allowedExtensions) {
        const lower = String(file?.name || "").toLowerCase();
        return allowedExtensions.some((extension) => lower.endsWith(extension));
      }

      function nextShotName() {
        return `Shot ${state.trajectories.length + 1}`;
      }

      function resetTrajectoryDraft() {
        trajectoryDraftName.textContent = `Next: ${nextShotName()}`;
      }

      function populateTrajectorySelects() {
        for (const selectEl of [trajectorySelect, renderTrajectorySelect]) {
          selectEl.innerHTML = "";
          if (!state.trajectories.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "No shots yet";
            selectEl.appendChild(option);
            continue;
          }
          for (const trajectory of state.trajectories) {
            const option = document.createElement("option");
            option.value = trajectory.id;
            option.textContent = `${trajectory.name} • ${trajectory.keyframes.length} kf`;
            selectEl.appendChild(option);
          }
        }
        captureKeyframeButton.disabled = state.trajectories.length === 0;
        renderButton.disabled = state.trajectories.length === 0;
        updateSceneChrome();
        resetTrajectoryDraft();
      }

      async function fetchJson(url, options = {}) {
        const response = await fetch(url, options);
        let payload = null;
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          payload = await response.json();
        } else {
          const text = await response.text();
          payload = text ? { detail: text } : null;
        }
        if (!response.ok) {
          const detail = payload?.detail || JSON.stringify(payload);
          throw new Error(detail);
        }
        return payload;
      }

      async function createProject() {
        const timestamp = new Date();
        const label = timestamp.toLocaleString([], {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
        return await fetchJson("/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: `Scene ${label}`,
            description: null,
          }),
        });
      }

      async function fetchProject(projectId) {
        return await fetchJson(`/projects/${projectId}`);
      }

      async function fetchTrajectories() {
        if (!state.projectId) {
          state.trajectories = [];
          populateTrajectorySelects();
          return;
        }
        state.trajectories = await fetchJson(`/projects/${state.projectId}/trajectories`);
        populateTrajectorySelects();
      }

      function applyManifest(manifest) {
        state.projectId = manifest.id;
        state.projectName = manifest.name;
        state.roomAssetId = manifest.scene.room_asset_id;
        state.objectCount = manifest.scene.objects.length;
        const roomAsset = manifest.assets.find((asset) => asset.id === manifest.scene.room_asset_id);
        if (roomAsset) {
          state.workflowMode = roomAsset.metadata?.generated_by === "depth_anything_3" ? "create" : "edit";
        }
        localStorage.setItem(PROJECT_STORAGE_KEY, manifest.id);
        updateSceneChrome();
      }

      function clearWorkspaceState(options = {}) {
        const preserveWorkflow = options.preserveWorkflow === true;
        state.projectId = null;
        state.projectName = null;
        state.roomAssetId = null;
        state.objectCount = 0;
        state.trajectories = [];
        if (!preserveWorkflow) {
          state.workflowMode = null;
        }
        localStorage.removeItem(PROJECT_STORAGE_KEY);
        viewerFrame.src = "about:blank";
        renderVideo.removeAttribute("src");
        renderVideo.load();
        populateTrajectorySelects();
        setViewerBadge("waiting");
        stageHint.hidden = false;
        stageHint.innerHTML = STAGE_DEFAULT_HINT;
        updateSceneChrome();
      }

      async function launchViewer(assetId = null) {
        if (!state.projectId) {
          return;
        }
        setViewerBadge("launching");
        stageHint.hidden = false;
        stageHint.innerHTML = "<div><strong>Launching viewer…</strong><div>Preparing the live stage for your room scene.</div></div>";
        try {
          const data = await fetchJson(`/projects/${state.projectId}/viewer/load-room`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(assetId ? { asset_id: assetId } : {}),
          });
          viewerFrame.src = data.viewer_url;
          state.roomAssetId = data.asset_id;
          state.objectCount = data.loaded_object_ids.length;
          setViewerBadge("viewer live", true);
          stageHint.hidden = true;
          updateSceneChrome();
          setStatus(`Viewer ready at ${data.viewer_url}. Drop meshes to add them instantly, then drag them in the viewer.`, "success");
        } catch (error) {
          setViewerBadge("viewer error");
          stageHint.hidden = false;
          stageHint.innerHTML = "<div><strong>Viewer unavailable.</strong><div>Check the status panel for the startup error.</div></div>";
          setStatus(`Viewer launch failed: ${error.message}`, "error");
        }
      }

      async function startRoomScene(file) {
        if (!isExtension(file, [".ply"])) {
          setStatus("Room uploads must be `.ply` Gaussian splat files.", "error");
          return;
        }
        state.workflowMode = "edit";
        showWorkspace();
        clearWorkspaceState({ preserveWorkflow: true });
        setStatus(`Creating a fresh scene for ${file.name}…`);
        setViewerBadge("uploading");
        stageHint.hidden = false;
        stageHint.innerHTML = "<div><strong>Uploading room…</strong><div>Setting up a new scene and preparing the viewer.</div></div>";
        try {
          const project = await createProject();
          applyManifest(project);
          const formData = new FormData();
          formData.append("file", file);
          const upload = await fetchJson(`/projects/${project.id}/assets/upload-room`, {
            method: "POST",
            body: formData,
          });
          const manifest = await fetchProject(project.id);
          applyManifest(manifest);
          await fetchTrajectories();
          await launchViewer(upload.asset.id);
        } catch (error) {
          clearWorkspaceState({ preserveWorkflow: true });
          showEditingLanding();
          setStatus(`Room upload failed: ${error.message}`, "error");
        }
      }

      async function startGeneratedScene(files) {
        if (!Array.isArray(files) || !files.length) {
          setStatus("Upload at least one image to generate a gsplat.", "error");
          return;
        }
        if (files.some((file) => !isExtension(file, [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"]))) {
          setStatus("Generation inputs must be supported image files.", "error");
          return;
        }

        state.workflowMode = "create";
        showWorkspace();
        clearWorkspaceState({ preserveWorkflow: true });
        setStatus(`Generating a gsplat from ${pluralize(files.length, "image")}… The first run may take longer while the DA3 model is prepared.`);
        setViewerBadge("generating");
        stageHint.hidden = false;
        stageHint.innerHTML = "<div><strong>Running Depth Anything 3…</strong><div>Estimating geometry and exporting a room gsplat from your images.</div></div>";
        try {
          const formData = new FormData();
          for (const file of files) {
            formData.append("files", file);
          }
          const data = await fetchJson("/generation/create-gsplat", {
            method: "POST",
            body: formData,
          });
          state.projectId = data.project_id;
          state.projectName = data.project_name;
          state.roomAssetId = data.asset.id;
          state.objectCount = data.loaded_object_ids.length;
          localStorage.setItem(PROJECT_STORAGE_KEY, data.project_id);
          await fetchTrajectories();
          viewerFrame.src = data.viewer_url;
          setViewerBadge("viewer live", true);
          stageHint.hidden = true;
          updateSceneChrome();
          setStatus(
            `Generated a room gsplat from ${pluralize(data.input_image_count, "image")}. The viewer is live, and you can download the generated .ply from the header.`,
            "success",
          );
        } catch (error) {
          clearWorkspaceState({ preserveWorkflow: true });
          showCreationLanding();
          setStatus(`GSplat generation failed: ${error.message}`, "error");
        }
      }

      function nextMeshPosition() {
        const index = state.objectCount;
        const column = index % 4;
        const row = Math.floor(index / 4);
        return [Number(((column - 1.5) * 0.72).toFixed(2)), 0.0, Number((-row * 0.9).toFixed(2))];
      }

      async function addMeshToScene(file) {
        if (!state.projectId || !state.roomAssetId) {
          setStatus("Load a room `.ply` first, then drop mesh files into the scene.", "error");
          return;
        }
        if (!isExtension(file, [".glb", ".gltf"])) {
          setStatus("Mesh uploads must be `.glb` or self-contained `.gltf` files.", "error");
          return;
        }
        setStatus(`Adding ${file.name} to the scene…`);
        try {
          const uploadData = new FormData();
          uploadData.append("file", file);
          const asset = await fetchJson(`/projects/${state.projectId}/assets/upload-object`, {
            method: "POST",
            body: uploadData,
          });
          const response = await fetchJson(`/projects/${state.projectId}/objects`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: humanizeName(file.name),
              asset_id: asset.asset.id,
              transform: {
                position: nextMeshPosition(),
                rotation_euler: [0.0, 0.0, 0.0],
                scale: [1.0, 1.0, 1.0],
              },
              visible: true,
              metadata: {},
            }),
          });
          const manifest = await fetchProject(state.projectId);
          applyManifest(manifest);
          setStatus(`Added ${response.name}. It should appear in the live viewer now; click it there to move or rotate it.`, "success");
        } catch (error) {
          setStatus(`Mesh upload failed: ${error.message}`, "error");
        }
      }

      function attachDropzone(zone, input, extensions, handler, options = {}) {
        const multiple = options.multiple === true;
        for (const eventName of ["dragenter", "dragover"]) {
          zone.addEventListener(eventName, (event) => {
            event.preventDefault();
            zone.classList.add("is-dragging");
          });
        }
        for (const eventName of ["dragleave", "drop"]) {
          zone.addEventListener(eventName, (event) => {
            event.preventDefault();
            zone.classList.remove("is-dragging");
          });
        }
        zone.addEventListener("drop", async (event) => {
          const files = Array.from(event.dataTransfer?.files || []);
          if (!files.length) {
            return;
          }
          if (files.some((file) => !isExtension(file, extensions))) {
            setStatus(`Expected ${extensions.join(" or ")} for this drop target.`, "error");
            return;
          }
          await handler(multiple ? files : files[0]);
        });
        zone.addEventListener("click", () => input.click());
        zone.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            input.click();
          }
        });
        input.addEventListener("change", async () => {
          const files = Array.from(input.files || []);
          input.value = "";
          if (files.length) {
            await handler(multiple ? files : files[0]);
          }
        });
      }

      async function restoreSession() {
        const projectId = localStorage.getItem(PROJECT_STORAGE_KEY);
        if (!projectId) {
          showWorkflowSelector();
          clearWorkspaceState();
          setStatus("Choose a workflow to begin.");
          return;
        }
        try {
          const manifest = await fetchProject(projectId);
          applyManifest(manifest);
          await fetchTrajectories();
          if (!manifest.scene.room_asset_id) {
            showWorkflowSelector();
            setStatus("Your saved scene has no room asset yet. Choose a workflow to continue.");
            return;
          }
          showWorkspace();
          await launchViewer();
        } catch (_error) {
          clearWorkspaceState();
          showWorkflowSelector();
          setStatus("Starting fresh. Choose a workflow to begin.");
        }
      }

      document.getElementById("trajectory-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!state.projectId) {
          setStatus("Load a room first, then create a shot.", "error");
          return;
        }
        setStatus("Creating a new camera shot…");
        try {
          const trajectory = await fetchJson(`/projects/${state.projectId}/trajectories`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: nextShotName(),
              duration_seconds: Number(trajectoryDuration.value || 5),
            }),
          });
          state.trajectories.push(trajectory);
          populateTrajectorySelects();
          trajectorySelect.value = trajectory.id;
          renderTrajectorySelect.value = trajectory.id;
          setStatus(`Created ${trajectory.name}. Capture camera poses whenever you're ready.`, "success");
        } catch (error) {
          setStatus(`Trajectory creation failed: ${error.message}`, "error");
        }
      });

      document.getElementById("keyframe-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!state.projectId || !trajectorySelect.value) {
          setStatus("Create and select a shot first, then capture a keyframe.", "error");
          return;
        }
        setStatus("Capturing the current viewer camera…");
        try {
          const data = await fetchJson(
            `/projects/${state.projectId}/trajectories/${trajectorySelect.value}/capture-keyframe`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                time_seconds: Number(keyframeTimeInput.value || 0),
              }),
            },
          );
          state.trajectories = state.trajectories.map((trajectory) =>
            trajectory.id === data.id ? data : trajectory,
          );
          populateTrajectorySelects();
          trajectorySelect.value = data.id;
          renderTrajectorySelect.value = data.id;
          setStatus(`Captured a keyframe for ${data.name}. It now has ${data.keyframes.length} keyframes.`, "success");
        } catch (error) {
          setStatus(`Keyframe capture failed: ${error.message}`, "error");
        }
      });

      document.getElementById("render-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!state.projectId || !renderTrajectorySelect.value) {
          setStatus("Choose a shot to render first.", "error");
          return;
        }
        setStatus("Rendering trajectory video…");
        try {
          const data = await fetchJson(
            `/projects/${state.projectId}/trajectories/${renderTrajectorySelect.value}/render`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                fps: Number(renderFpsInput.value || 24),
                width: Number(renderWidthInput.value || 1280),
                height: Number(renderHeightInput.value || 720),
              }),
            },
          );
          renderVideo.src = data.artifact_url;
          renderVideo.load();
          setStatus(`Rendered ${data.filename} at ${data.fps} fps with ${data.frame_count} frames.`, "success");
        } catch (error) {
          setStatus(`Render failed: ${error.message}`, "error");
        }
      });

      newSceneButton.addEventListener("click", () => {
        clearWorkspaceState();
        showWorkflowSelector();
        setStatus("Choose a workflow to start a new scene.");
      });

      workflowCreateButton.addEventListener("click", () => {
        state.workflowMode = "create";
        showCreationLanding();
        setStatus("Drop images to generate a fresh gsplat.");
      });
      workflowEditButton.addEventListener("click", () => {
        state.workflowMode = "edit";
        showEditingLanding();
        setStatus("Drop a room `.ply` to begin editing.");
      });

      roomBrowseButton.addEventListener("click", (event) => {
        event.stopPropagation();
        roomFileInput.click();
      });
      generationBrowseButton.addEventListener("click", (event) => {
        event.stopPropagation();
        generationFileInput.click();
      });
      meshBrowseButton.addEventListener("click", (event) => {
        event.stopPropagation();
        meshFileInput.click();
      });
      editingBackButton.addEventListener("click", () => {
        clearWorkspaceState();
        showWorkflowSelector();
        setStatus("Choose a workflow to begin.");
      });
      creationBackButton.addEventListener("click", () => {
        clearWorkspaceState();
        showWorkflowSelector();
        setStatus("Choose a workflow to begin.");
      });

      attachDropzone(roomDropzone, roomFileInput, [".ply"], startRoomScene);
      attachDropzone(
        generationDropzone,
        generationFileInput,
        [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"],
        startGeneratedScene,
        { multiple: true },
      );
      attachDropzone(meshDropzone, meshFileInput, [".glb", ".gltf"], addMeshToScene);

      clearWorkspaceState();
      showWorkflowSelector();
      resetTrajectoryDraft();
      restoreSession();
    </script>
  </body>
</html>"""


@router.post("/projects/{project_id}/viewer/load-room", response_model=ViewerLaunchResponse)
def load_room_viewer(
    project_id: str,
    payload: ViewerLaunchRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerLaunchResponse:
    """Load the active room asset into the viser viewer."""
    try:
        session = viewer_service.load_room(project_id=project_id, asset_id=payload.asset_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidGaussianSplatError, InvalidMeshAssetError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (MissingViewerDependencyError, MissingMeshDependencyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ViewerLaunchResponse(
        viewer_url=session.viewer_url,
        project_id=session.project_id,
        asset_id=session.asset_id,
        source_uri=session.source_uri,
        loaded_object_ids=session.loaded_object_ids,
    )
