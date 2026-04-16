"""Viewer routes and minimal editor page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from apps.api.app.deps import get_repo, get_viewer_service
from apps.api.app.schemas.project import ProjectSummary
from apps.api.app.schemas.viewer import ViewerLaunchRequest, ViewerLaunchResponse
from services.preview.viser_scene import InvalidGaussianSplatError
from services.storage.local_fs import EntityNotFoundError, ProjectNotFoundError, ProjectRepository

router = APIRouter(tags=["viewer"])


@router.get("/editor", response_class=HTMLResponse)
def editor_page(repo: ProjectRepository = Depends(get_repo)) -> str:
    """Serve a minimal editor shell for project creation and room upload."""
    projects = [ProjectSummary.from_manifest(item) for item in repo.list_projects()]
    project_options = "".join(
        f'<option value="{project.id}">{project.name} ({project.id})</option>'
        for project in projects
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>deco editor</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f4f1ea;
        --panel: #fffdf9;
        --ink: #1d1c1a;
        --muted: #6c655d;
        --accent: #c25b2a;
        --line: #d9d2c8;
      }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background: radial-gradient(circle at top, #fff7ee, var(--bg) 45%);
        color: var(--ink);
      }}
      main {{
        max-width: 1100px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}
      .hero {{
        display: grid;
        gap: 12px;
        margin-bottom: 24px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 20px;
      }}
      .card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 12px 30px rgba(60, 40, 20, 0.06);
      }}
      h1, h2 {{
        margin: 0 0 8px;
        font-weight: 600;
      }}
      p {{
        margin: 0;
        color: var(--muted);
      }}
      form {{
        display: grid;
        gap: 10px;
        margin-top: 14px;
      }}
      label {{
        display: grid;
        gap: 6px;
        font-size: 14px;
      }}
      input, select, button {{
        font: inherit;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid var(--line);
      }}
      button {{
        background: var(--accent);
        color: white;
        border: none;
        cursor: pointer;
      }}
      button.secondary {{
        background: #efe7dc;
        color: var(--ink);
      }}
      .viewer-wrap {{
        display: grid;
        gap: 14px;
      }}
      iframe {{
        width: 100%;
        min-height: 700px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: #f8f5f0;
      }}
      #status {{
        white-space: pre-wrap;
        font-size: 13px;
        color: var(--muted);
      }}
      @media (max-width: 900px) {{
        .grid {{
          grid-template-columns: 1fr;
        }}
        iframe {{
          min-height: 480px;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>deco room gsplat viewer</h1>
        <p>Create a project, upload a room `gsplat` PLY, and launch a `viser` viewer session.</p>
      </section>
      <section class="grid">
        <div class="card">
          <h2>Project</h2>
          <p>Use the current API stack as a minimal editor shell.</p>
          <form id="project-form">
            <label>Name<input name="name" placeholder="Living room" required /></label>
            <label>Description<input name="description" placeholder="Optional" /></label>
            <button type="submit">Create project</button>
          </form>
          <form id="upload-form">
            <label>Project
              <select id="project-select" name="project_id" required>
                <option value="">Select project</option>
                {project_options}
              </select>
            </label>
            <label>Room name<input name="name" placeholder="Room scan" /></label>
            <label>PLY upload<input type="file" name="file" accept=".ply" required /></label>
            <button type="submit">Upload gsplat</button>
          </form>
          <form id="launch-form">
            <label>Project
              <select id="launch-project-select" name="project_id" required>
                <option value="">Select project</option>
                {project_options}
              </select>
            </label>
            <button type="submit" class="secondary">Launch viewer</button>
          </form>
          <form id="trajectory-form">
            <label>Trajectory name<input name="name" placeholder="Camera path" required /></label>
            <label>Duration seconds<input name="duration_seconds" type="number" min="1" step="0.1" value="5" /></label>
            <button type="submit">Create trajectory</button>
          </form>
          <form id="keyframe-form">
            <label>Trajectory
              <select id="trajectory-select" name="trajectory_id" required>
                <option value="">Select trajectory</option>
              </select>
            </label>
            <label>Keyframe time<input name="time_seconds" type="number" min="0" step="0.1" value="0" /></label>
            <button type="submit" class="secondary">Capture current view</button>
          </form>
          <form id="render-form">
            <label>Trajectory
              <select id="render-trajectory-select" name="trajectory_id" required>
                <option value="">Select trajectory</option>
              </select>
            </label>
            <label>FPS<input name="fps" type="number" min="1" step="1" value="24" /></label>
            <label>Width<input name="width" type="number" min="64" step="1" value="1280" /></label>
            <label>Height<input name="height" type="number" min="64" step="1" value="720" /></label>
            <button type="submit">Render MP4</button>
          </form>
          <div id="status">Ready.</div>
        </div>
        <div class="viewer-wrap">
          <div class="card">
            <h2>Viewer</h2>
            <p>The room preview loads in a separate `viser` server and is embedded here.</p>
          </div>
          <iframe id="viewer-frame" title="viser viewer"></iframe>
          <div class="card">
            <h2>Trajectory Replay</h2>
            <p>Render playback while the viewer tab is connected.</p>
            <video id="render-video" controls style="width:100%; border-radius:12px; background:#111;"></video>
          </div>
        </div>
      </section>
    </main>
    <script>
      const statusEl = document.getElementById("status");
      const projectSelect = document.getElementById("project-select");
      const launchProjectSelect = document.getElementById("launch-project-select");
      const trajectorySelect = document.getElementById("trajectory-select");
      const renderTrajectorySelect = document.getElementById("render-trajectory-select");
      const viewerFrame = document.getElementById("viewer-frame");
      const renderVideo = document.getElementById("render-video");

      function setStatus(message) {{
        statusEl.textContent = message;
      }}

      function addProjectOption(project) {{
        for (const selectEl of [projectSelect, launchProjectSelect]) {{
          const option = document.createElement("option");
          option.value = project.id;
          option.textContent = `${{project.name}} (${{project.id}})`;
          selectEl.appendChild(option);
        }}
      }}

      function addTrajectoryOption(trajectory) {{
        for (const selectEl of [trajectorySelect, renderTrajectorySelect]) {{
          const option = document.createElement("option");
          option.value = trajectory.id;
          option.textContent = `${{trajectory.name}} (${{trajectory.id}})`;
          selectEl.appendChild(option);
        }}
      }}

      document.getElementById("project-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const payload = {{
          name: form.get("name"),
          description: form.get("description") || null,
        }};
        const response = await fetch("/projects", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Project creation failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        addProjectOption(data);
        projectSelect.value = data.id;
        launchProjectSelect.value = data.id;
        setStatus(`Created project ${{data.name}} (${{data.id}}).`);
        event.currentTarget.reset();
      }});

      document.getElementById("upload-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const projectId = form.get("project_id");
        if (!projectId) {{
          setStatus("Select a project first.");
          return;
        }}
        setStatus("Uploading gsplat...");
        const response = await fetch(`/projects/${{projectId}}/assets/upload-room`, {{
          method: "POST",
          body: form,
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Upload failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        launchProjectSelect.value = projectId;
        setStatus(`Uploaded room asset ${{data.asset.name}} (${{data.asset.id}}).`);
      }});

      document.getElementById("launch-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const projectId = form.get("project_id");
        if (!projectId) {{
          setStatus("Select a project first.");
          return;
        }}
        setStatus("Launching viewer...");
        const response = await fetch(`/projects/${{projectId}}/viewer/load-room`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{}}),
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Viewer launch failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        viewerFrame.src = data.viewer_url;
        setStatus(`Viewer loaded for asset ${{data.asset_id}} at ${{data.viewer_url}}`);
      }});

      document.getElementById("trajectory-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const projectId = launchProjectSelect.value || projectSelect.value;
        if (!projectId) {{
          setStatus("Create or select a project first.");
          return;
        }}
        const form = new FormData(event.currentTarget);
        const payload = {{
          name: form.get("name"),
          duration_seconds: Number(form.get("duration_seconds") || 5),
        }};
        const response = await fetch(`/projects/${{projectId}}/trajectories`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Trajectory creation failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        addTrajectoryOption(data);
        trajectorySelect.value = data.id;
        renderTrajectorySelect.value = data.id;
        setStatus(`Created trajectory ${{data.name}} (${{data.id}}).`);
        event.currentTarget.reset();
      }});

      document.getElementById("keyframe-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const projectId = launchProjectSelect.value || projectSelect.value;
        const form = new FormData(event.currentTarget);
        const trajectoryId = form.get("trajectory_id");
        if (!projectId || !trajectoryId) {{
          setStatus("Select a project and trajectory first.");
          return;
        }}
        const payload = {{
          time_seconds: Number(form.get("time_seconds") || 0),
        }};
        const response = await fetch(`/projects/${{projectId}}/trajectories/${{trajectoryId}}/capture-keyframe`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Keyframe capture failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        setStatus(`Captured keyframe. Trajectory now has ${{data.keyframes.length}} keyframes.`);
      }});

      document.getElementById("render-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const projectId = launchProjectSelect.value || projectSelect.value;
        const form = new FormData(event.currentTarget);
        const trajectoryId = form.get("trajectory_id");
        if (!projectId || !trajectoryId) {{
          setStatus("Select a project and trajectory first.");
          return;
        }}
        setStatus("Rendering trajectory video...");
        const payload = {{
          fps: Number(form.get("fps") || 24),
          width: Number(form.get("width") || 1280),
          height: Number(form.get("height") || 720),
        }};
        const response = await fetch(`/projects/${{projectId}}/trajectories/${{trajectoryId}}/render`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) {{
          setStatus(`Render failed: ${{data.detail || JSON.stringify(data)}}`);
          return;
        }}
        renderVideo.src = data.artifact_url;
        renderVideo.load();
        setStatus(`Rendered ${{data.filename}} with ${{data.frame_count}} frames.`);
      }});
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
    except InvalidGaussianSplatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ViewerLaunchResponse(
        viewer_url=session.viewer_url,
        project_id=session.project_id,
        asset_id=session.asset_id,
        source_uri=session.source_uri,
    )
