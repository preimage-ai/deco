"""Viewer routes and minimal editor page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.orchestration.viewer_service import MissingViewerDependencyError
from apps.api.app.schemas.viewer import (
    ViewerLaunchRequest,
    ViewerLaunchResponse,
    ViewerObjectSelectionRequest,
    ViewerObjectSelectionResponse,
)
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
      .object-list {
        display: grid;
        gap: 10px;
      }
      .object-card {
        display: grid;
        gap: 12px;
        padding: 14px;
        border-radius: 18px;
        border: 1px solid rgba(149, 179, 222, 0.14);
        background: rgba(255, 255, 255, 0.03);
      }
      .object-card.is-selected {
        border-color: rgba(110, 231, 200, 0.55);
        box-shadow: 0 0 0 1px rgba(110, 231, 200, 0.16) inset;
      }
      .object-card strong {
        font-size: 15px;
      }
      .object-card-summary {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        cursor: pointer;
      }
      .object-card-summary button {
        flex: 1;
        text-align: left;
        background: transparent;
        color: inherit;
        border: none;
        padding: 0;
      }
      .object-card-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 999px;
        border: 1px solid rgba(149, 179, 222, 0.2);
        background: rgba(255, 255, 255, 0.04);
        color: var(--ink);
        font-size: 14px;
        transition: transform 160ms ease;
      }
      .object-card.is-open .object-card-toggle {
        transform: rotate(180deg);
      }
      .object-card-body[hidden] {
        display: none !important;
      }
      .object-card p {
        margin: 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
      }
      .empty-state {
        padding: 18px;
        border-radius: 18px;
        border: 1px dashed rgba(149, 179, 222, 0.18);
        color: var(--muted);
        text-align: center;
      }
      .stage-frame {
        position: relative;
        min-height: 720px;
        height: min(78vh, 960px);
        border-radius: calc(var(--radius-lg) - 4px);
        overflow: hidden;
        border: 1px solid rgba(149, 179, 222, 0.14);
        background: linear-gradient(180deg, rgba(6, 12, 23, 0.84), rgba(6, 12, 23, 0.92));
      }
      iframe,
      video {
        width: 100%;
        border: 0;
        border-radius: calc(var(--radius-lg) - 4px);
        background: rgba(4, 8, 16, 0.8);
      }
      iframe {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        min-height: 100%;
        display: block;
      }
      video {
        display: block;
        min-height: 100%;
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
        .workspace-grid {
          grid-template-columns: 1fr;
        }
        .workspace-header {
          flex-direction: column;
          align-items: flex-start;
        }
        .stage-frame {
          min-height: 520px;
          height: 62vh;
        }
        .inline-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <section id="landing" class="landing">
        <div class="landing-card">
          <div class="landing-copy">
            <span class="eyebrow">deco studio</span>
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
              <span class="ghost-note">The first drop creates a new scene automatically.</span>
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

            <section class="panel stack">
              <div class="panel-header">
                <div>
                  <h2>Scene Objects</h2>
                  <p>Edit, hide, select, or delete placed meshes. Changes persist to the project manifest.</p>
                </div>
                <button id="refresh-objects-button" class="button button-secondary" type="button">Refresh</button>
              </div>
              <div id="object-list" class="object-list">
                <div class="empty-state">No meshes placed yet.</div>
              </div>
            </section>

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
              <div id="status">Drop a room `.ply` to begin.</div>
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
                    <div>Upload a room first, then drop meshes into the scene.</div>
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
    <input id="mesh-file-input" class="file-input" type="file" accept=".glb,.gltf" />

    <script>
      const PROJECT_STORAGE_KEY = "deco_active_project_id";
      const landing = document.getElementById("landing");
      const workspace = document.getElementById("workspace");
      const roomDropzone = document.getElementById("room-dropzone");
      const meshDropzone = document.getElementById("mesh-dropzone");
      const roomFileInput = document.getElementById("room-file-input");
      const meshFileInput = document.getElementById("mesh-file-input");
      const roomBrowseButton = document.getElementById("room-browse-button");
      const meshBrowseButton = document.getElementById("mesh-browse-button");
      const newSceneButton = document.getElementById("new-scene-button");
      const sceneTitle = document.getElementById("scene-title");
      const sceneSubtitle = document.getElementById("scene-subtitle");
      const sceneObjectCount = document.getElementById("scene-object-count");
      const sceneTrajectoryCount = document.getElementById("scene-trajectory-count");
      const viewerBadge = document.getElementById("viewer-badge");
      const stageHint = document.getElementById("stage-hint");
      const objectList = document.getElementById("object-list");
      const refreshObjectsButton = document.getElementById("refresh-objects-button");
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
      const viewerFrame = document.getElementById("viewer-frame");
      const renderVideo = document.getElementById("render-video");

      const state = {
        projectId: null,
        roomAssetId: null,
        objectCount: 0,
        trajectories: [],
        objects: [],
        selectedObjectId: null,
        openObjectId: null,
      };

      function setStatus(message, tone = "info") {
        statusCard.dataset.tone = tone;
        statusEl.textContent = message;
      }

      function showLanding() {
        landing.hidden = false;
        workspace.hidden = true;
      }

      function showWorkspace() {
        landing.hidden = true;
        workspace.hidden = false;
      }

      function formatSceneLabel(projectId) {
        return projectId ? `Scene ${projectId.slice(-6)}` : "Fresh Scene";
      }

      function updateSceneChrome() {
        sceneTitle.textContent = formatSceneLabel(state.projectId);
        sceneSubtitle.textContent = state.roomAssetId
          ? "Drop meshes, then click them inside the viewer to reveal move and rotate gizmos."
          : "Upload a room `.ply` to activate the viewer stage.";
        sceneObjectCount.textContent = String(state.objectCount);
        sceneTrajectoryCount.textContent = String(state.trajectories.length);
      }

      function formatVector(values) {
        return values.map((value) => Number(value).toFixed(2)).join(", ");
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

      function renderObjectList() {
        objectList.innerHTML = "";
        if (!state.objects.length) {
          objectList.innerHTML = '<div class="empty-state">No meshes placed yet.</div>';
          return;
        }

        for (const object of state.objects) {
          const card = document.createElement("div");
          const isOpen = state.openObjectId === object.id;
          card.className = `object-card${state.selectedObjectId === object.id ? " is-selected" : ""}${isOpen ? " is-open" : ""}`;
          const transform = object.transform || {};
          card.innerHTML = `
            <div class="object-card-summary">
              <button type="button" data-action="toggle-open">
                <strong>${object.name}</strong>
                <p>${object.id}</p>
              </button>
              <div class="action-row">
                <span class="badge">${object.visible ? "visible" : "hidden"}</span>
                <button class="object-card-toggle" type="button" data-action="toggle-open" aria-label="Toggle object details">▾</button>
              </div>
            </div>
            <div class="object-card-body" ${isOpen ? "" : "hidden"}>
              <p>Position: ${formatVector(transform.position || [0, 0, 0])}</p>
              <p>Rotation: ${formatVector(transform.rotation_euler || [0, 0, 0])}</p>
              <p>Scale: ${formatVector(transform.scale || [1, 1, 1])}</p>
              <label>
                Name
                <input data-field="name" value="${object.name.replace(/"/g, "&quot;")}" />
              </label>
              <div class="inline-grid">
                <label>
                  Position
                  <input data-field="position" value="${formatVector(transform.position || [0, 0, 0])}" />
                </label>
                <label>
                  Rotation
                  <input data-field="rotation" value="${formatVector(transform.rotation_euler || [0, 0, 0])}" />
                </label>
                <label>
                  Scale
                  <input data-field="scale" value="${formatVector(transform.scale || [1, 1, 1])}" />
                </label>
              </div>
              <div class="action-row">
                <button class="button button-secondary" type="button" data-action="select">Select</button>
                <button class="button button-secondary" type="button" data-action="save">Save</button>
                <button class="button button-secondary" type="button" data-action="toggle">${object.visible ? "Hide" : "Show"}</button>
                <button class="button button-secondary" type="button" data-action="delete">Delete</button>
              </div>
            </div>
          `;

          for (const toggleEl of card.querySelectorAll('[data-action="toggle-open"]')) {
            toggleEl.addEventListener("click", () => {
              state.openObjectId = state.openObjectId === object.id ? null : object.id;
              renderObjectList();
            });
          }

          card.querySelector('[data-action="select"]').addEventListener("click", async () => {
            state.selectedObjectId = object.id;
            state.openObjectId = object.id;
            renderObjectList();
            await selectObjectInViewer(object.id);
          });

          card.querySelector('[data-action="save"]').addEventListener("click", async () => {
            const nameInput = card.querySelector('[data-field="name"]');
            const scaleInput = card.querySelector('[data-field="scale"]');
            await saveObject(object.id, {
              name: nameInput.value.trim() || object.name,
              transform: {
                scale: parseVector(scaleInput.value, 1.0),
              },
            });
          });

          card.querySelector('[data-action="toggle"]').addEventListener("click", async () => {
            await updateObject(object.id, { visible: !object.visible });
          });

          card.querySelector('[data-action="delete"]').addEventListener("click", async () => {
            await deleteObject(object.id);
          });

          objectList.appendChild(card);
        }
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

      async function fetchObjects() {
        if (!state.projectId) {
          state.objects = [];
          renderObjectList();
          return;
        }
        state.objects = await fetchJson(`/projects/${state.projectId}/objects`);
        state.objectCount = state.objects.length;
        if (state.selectedObjectId && !state.objects.some((object) => object.id === state.selectedObjectId)) {
          state.selectedObjectId = null;
        }
        if (state.openObjectId && !state.objects.some((object) => object.id === state.openObjectId)) {
          state.openObjectId = null;
        }
        updateSceneChrome();
        renderObjectList();
      }

      function applyManifest(manifest) {
        state.projectId = manifest.id;
        state.roomAssetId = manifest.scene.room_asset_id;
        state.objectCount = manifest.scene.objects.length;
        localStorage.setItem(PROJECT_STORAGE_KEY, manifest.id);
        updateSceneChrome();
      }

      function clearWorkspaceState() {
        state.projectId = null;
        state.roomAssetId = null;
        state.objectCount = 0;
        state.trajectories = [];
        state.objects = [];
        state.selectedObjectId = null;
        state.openObjectId = null;
        localStorage.removeItem(PROJECT_STORAGE_KEY);
        viewerFrame.src = "about:blank";
        renderVideo.removeAttribute("src");
        renderVideo.load();
        populateTrajectorySelects();
        setViewerBadge("waiting");
        stageHint.hidden = false;
        stageHint.innerHTML = "<div><strong>The viewer will appear here.</strong><div>Upload a room first, then drop meshes into the scene.</div></div>";
        updateSceneChrome();
        renderObjectList();
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
          await fetchObjects();
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
        showWorkspace();
        clearWorkspaceState();
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
          await fetchObjects();
          await fetchTrajectories();
          await launchViewer(upload.asset.id);
        } catch (error) {
          setStatus(`Room upload failed: ${error.message}`, "error");
          showLanding();
          clearWorkspaceState();
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
          await fetchObjects();
          setStatus(`Added ${response.name}. It should appear in the live viewer now; click it there to move or rotate it.`, "success");
        } catch (error) {
          setStatus(`Mesh upload failed: ${error.message}`, "error");
        }
      }

      async function selectObjectInViewer(objectId) {
        const object = state.objects.find((item) => item.id === objectId);
        if (!object) {
          return;
        }
        try {
          await fetchJson(`/projects/${state.projectId}/viewer/select-object`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ object_id: objectId }),
          });
          state.selectedObjectId = objectId;
          await fetchObjects();
          setStatus(`Selected ${object.name}. Its transform gizmo should now be visible in the viewer.`, "success");
        } catch (error) {
          setStatus(`Object selection failed: ${error.message}`, "error");
        }
      }

      async function updateObject(objectId, patch) {
        if (!state.projectId) {
          return;
        }
        try {
          await fetchJson(`/projects/${state.projectId}/objects/${objectId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(patch),
          });
          state.selectedObjectId = objectId;
          await fetchObjects();
          setStatus("Object updated and pushed into the live viewer.", "success");
        } catch (error) {
          setStatus(`Object update failed: ${error.message}`, "error");
        }
      }

      async function saveObject(objectId, patch = {}) {
        if (!state.projectId) {
          return;
        }
        try {
          await fetchJson(`/projects/${state.projectId}/viewer/save-object`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              object_id: objectId,
              ...(patch.name ? { name: patch.name } : {}),
              ...(patch.transform?.scale ? { scale: patch.transform.scale } : {}),
            }),
          });
          state.selectedObjectId = null;
          await fetchObjects();
          setStatus("Object pose saved and gizmo hidden.", "success");
        } catch (error) {
          setStatus(`Object save failed: ${error.message}`, "error");
        }
      }

      async function deleteObject(objectId) {
        if (!state.projectId) {
          return;
        }
        try {
          await fetchJson(`/projects/${state.projectId}/objects/${objectId}`, {
            method: "DELETE",
          });
          if (state.selectedObjectId === objectId) {
            state.selectedObjectId = null;
          }
          if (state.openObjectId === objectId) {
            state.openObjectId = null;
          }
          await fetchObjects();
          setStatus("Object deleted from the scene.", "success");
        } catch (error) {
          setStatus(`Object deletion failed: ${error.message}`, "error");
        }
      }

      function attachDropzone(zone, input, extensions, handler) {
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
          const file = event.dataTransfer?.files?.[0];
          if (!file) {
            return;
          }
          if (!isExtension(file, extensions)) {
            setStatus(`Expected ${extensions.join(" or ")} for this drop target.`, "error");
            return;
          }
          await handler(file);
        });
        zone.addEventListener("click", () => input.click());
        zone.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            input.click();
          }
        });
        input.addEventListener("change", async () => {
          const file = input.files?.[0];
          input.value = "";
          if (file) {
            await handler(file);
          }
        });
      }

      async function restoreSession() {
        const projectId = localStorage.getItem(PROJECT_STORAGE_KEY);
        if (!projectId) {
          showLanding();
          clearWorkspaceState();
          setStatus("Drop a room `.ply` to begin.");
          return;
        }
        try {
          const manifest = await fetchProject(projectId);
          applyManifest(manifest);
          await fetchObjects();
          await fetchTrajectories();
          if (!manifest.scene.room_asset_id) {
            showLanding();
            setStatus("Your saved scene has no room asset yet. Drop a `.ply` to continue.");
            return;
          }
          showWorkspace();
          await launchViewer();
        } catch (_error) {
          clearWorkspaceState();
          showLanding();
          setStatus("Starting fresh. Drop a room `.ply` to begin.");
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
        showLanding();
        setStatus("Drop a room `.ply` to start a new scene.");
      });

      refreshObjectsButton.addEventListener("click", async () => {
        await fetchObjects();
        setStatus("Scene object list refreshed from disk.", "success");
      });

      roomBrowseButton.addEventListener("click", (event) => {
        event.stopPropagation();
        roomFileInput.click();
      });
      meshBrowseButton.addEventListener("click", (event) => {
        event.stopPropagation();
        meshFileInput.click();
      });

      attachDropzone(roomDropzone, roomFileInput, [".ply"], startRoomScene);
      attachDropzone(meshDropzone, meshFileInput, [".glb", ".gltf"], addMeshToScene);

      clearWorkspaceState();
      showLanding();
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


@router.post(
    "/projects/{project_id}/viewer/select-object",
    response_model=ViewerObjectSelectionResponse,
)
def select_viewer_object(
    project_id: str,
    payload: ViewerObjectSelectionRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerObjectSelectionResponse:
    """Show one object's gizmo or clear viewer selection."""
    try:
        loaded_object_ids = viewer_service.set_selected_object(project_id, payload.object_id)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ViewerObjectSelectionResponse(
        selected_object_id=payload.object_id,
        loaded_object_ids=loaded_object_ids,
    )


@router.post(
    "/projects/{project_id}/viewer/save-object",
    response_model=ViewerObjectSelectionResponse,
)
def save_viewer_object(
    project_id: str,
    payload: ViewerObjectSelectionRequest,
    viewer_service=Depends(get_viewer_service),
) -> ViewerObjectSelectionResponse:
    """Persist the current object transform from the viewer and hide its gizmo."""
    if not payload.object_id:
        raise HTTPException(status_code=400, detail="object_id is required")

    try:
        viewer_service.persist_object_state(
            project_id,
            payload.object_id,
            name=payload.name,
            scale=payload.scale,
        )
        loaded_object_ids = viewer_service.set_selected_object(project_id, None)
    except (ProjectNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ViewerObjectSelectionResponse(
        selected_object_id=None,
        loaded_object_ids=loaded_object_ids,
    )
