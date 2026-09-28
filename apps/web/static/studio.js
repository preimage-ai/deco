/* Presentation layer over the persistent scene, object, trajectory and render APIs. */
function escapeHtml(value) {
  const el = document.createElement("span");
  el.textContent = String(value);
  return el.innerHTML.replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function parseVector(value) {
  const values = value.split(",").map(part => Number(part.trim()));
  if (values.length !== 3 || values.some(n => !Number.isFinite(n)) || value.split(",").some(p => !p.trim())) {
    throw new Error("Enter three numbers separated by commas, for example: 0, 1, 0.");
  }
  return values;
}

function setTab(tab) {
  document.querySelectorAll("[data-tool]").forEach(el => { el.hidden = el.dataset.tool !== tab; });
  document.querySelectorAll("[data-tab]").forEach(el => el.setAttribute("aria-pressed", String(el.dataset.tab === tab)));
}

async function openProject(id) {
  if (state.rendering || state.generating) throw new Error("Wait for the current export to finish before switching spaces.");
  clearWorkspaceState();
  const manifest = await fetchProject(id);
  applyManifest(manifest);
  if (!state.roomAssetId) {
    showWorkflowSelector();
    setStatus("This space has no room yet. Import a room or try the sample studio.");
    return;
  }
  showWorkspace();
  await fetchObjects();
  await fetchTrajectories();
  await launchViewer();
  await loadRenderLibrary();
  setTab("objects");
}

async function loadProjectLibrary() {
  const container = document.getElementById("project-library");
  try {
    const projects = await fetchJson("/projects");
    container.replaceChildren();
    if (!projects.length) {
      container.innerHTML = '<p class="ghost-note">A fresh canvas. Explore the demo or import your first room.</p>';
    }
    for (const project of projects.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at))) {
      const button = document.createElement("button");
      button.className = "project-card";
      button.type = "button";
      button.innerHTML = `<span class="project-icon" aria-hidden="true">⌑</span><strong>${escapeHtml(project.name)}</strong><span>${new Date(project.updated_at).toLocaleDateString(undefined, {month: "short", day: "numeric"})} · Open space ↗</span>`;
      button.addEventListener("click", async () => {
        button.disabled = true;
        try { await openProject(project.id); }
        catch (error) { setStatus(error.message, "error"); }
        finally { button.disabled = false; }
      });
      container.append(button);
    }
  } catch (error) { container.textContent = `Could not load saved spaces: ${error.message}`; }
}

async function duplicateObject(object) {
  try {
    const current = await fetchJson(`/projects/${state.projectId}/objects/${object.id}`);
    const position = [...current.transform.position];
    position[0] += .5;
    await fetchJson(`/projects/${state.projectId}/objects`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name: `${current.name} copy`, asset_id: current.asset_id,
        transform: {...current.transform, position}, visible: true}),
    });
    await fetchObjects();
    setStatus("Piece duplicated. Select it to adjust its placement.", "success");
  } catch (error) { setStatus(error.message, "error"); }
}

function renderKeyframes() {
  const container = document.getElementById("keyframe-list");
  if (!container) return;
  container.replaceChildren();
  const shot = state.trajectories.find(item => item.id === trajectorySelect.value);
  document.getElementById("delete-shot").disabled = !shot;
  if (!shot?.keyframes.length) {
    container.innerHTML = '<p class="ghost-note">No camera views captured yet.</p>';
    return;
  }
  for (const [index, frame] of shot.keyframes.entries()) {
    const row = document.createElement("div");
    row.className = "keyframe-row";
    row.innerHTML = `<span><b>${String(index + 1).padStart(2, "0")}</b> View at ${frame.time_seconds.toFixed(1)}s</span><button class="button button-secondary" type="button" aria-label="Remove keyframe ${index + 1}">Remove</button>`;
    row.querySelector("button").addEventListener("click", async () => {
      try {
        await fetchJson(`/projects/${state.projectId}/trajectories/${shot.id}`, {
          method: "PATCH", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({keyframes: shot.keyframes.filter(item => item.id !== frame.id)}),
        });
        await fetchTrajectories();
      } catch (error) { setStatus(error.message, "error"); }
    });
    container.append(row);
  }
}

async function loadRenderLibrary() {
  const container = document.getElementById("render-library");
  container.replaceChildren();
  if (!state.projectId) return;
  const clips = await fetchJson(`/projects/${state.projectId}/renders`);
  if (!clips.length) {
    container.innerHTML = '<p class="ghost-note">Your exported films will appear here.</p>';
    renderVideo.closest(".render-card").hidden = true;
    return;
  }
  renderVideo.closest(".render-card").hidden = false;
  const last = clips.find(clip => !clip.filename.includes("_enhanced")) || clips[0];
  state.lastRenderFilename = last.filename;
  renderVideo.src = last.artifact_url;
  for (const clip of clips) {
    const row = document.createElement("div");
    row.className = "render-row";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "clip-button";
    button.textContent = clip.filename;
    button.addEventListener("click", () => {
      renderVideo.src = clip.artifact_url;
      state.lastRenderFilename = clip.filename;
      updateRenderActions();
    });
    const link = document.createElement("a");
    link.className = "button button-secondary";
    link.href = clip.artifact_url;
    link.download = clip.filename;
    link.textContent = `Download · ${(clip.size_bytes / 1024 / 1024).toFixed(1)} MB`;
    row.append(button, link);
    container.append(row);
  }
  updateRenderActions();
}

async function initializeStudio() {
  // The tool rail stays short enough to keep the live room on screen.
  const objectPanel = objectList.closest("section");
  const aiPanel = generateTextPrompt.closest("section");
  const rail = document.querySelector(".rail");
  for (const el of [objectPanel, document.getElementById("mesh-dropzone")]) el.dataset.tool = "objects";
  aiPanel.dataset.tool = "ai";
  for (const id of ["trajectory-form", "keyframe-form", "render-form"]) document.getElementById(id).dataset.tool = "shots";
  rail.insertBefore(objectPanel, document.getElementById("mesh-dropzone"));
  document.querySelectorAll("[data-tab]").forEach(button => button.addEventListener("click", () => setTab(button.dataset.tab)));
  setTab("objects");
  rail.addEventListener("pointerenter", () => {
    if (state.projectId && document.activeElement === viewerFrame) fetchObjects().catch(error => setStatus(error.message, "error"));
  });
  renderVideo.closest(".render-card").hidden = true;
  enhancedRenderVideo.closest(".render-card").hidden = true;
  enhancedRenderVideo.addEventListener("loadedmetadata", () => { enhancedRenderVideo.closest(".render-card").hidden = false; });
  trajectorySelect.addEventListener("change", renderKeyframes);
  renderTrajectorySelect.addEventListener("change", updateRenderActions);
  document.getElementById("demo-button").addEventListener("click", async event => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Preparing your studio…";
    setStatus("Building the sample space and its furniture…");
    try {
      const project = await fetchJson("/demo/projects", {method: "POST"});
      await openProject(project.id);
    } catch (error) { setStatus(`Could not open the sample: ${error.message}`, "error"); }
    finally { button.disabled = false; button.textContent = "Explore the demo studio ↗"; }
  });
  document.getElementById("rename-project").addEventListener("click", async () => {
    const name = window.prompt("Name your space", state.projectName);
    if (!name?.trim()) return;
    try {
      const manifest = await fetchJson(`/projects/${state.projectId}`, {
        method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({name: name.trim()}),
      });
      applyManifest(manifest);
      setStatus("Space renamed and saved.", "success");
    } catch (error) { setStatus(error.message, "error"); }
  });
  document.getElementById("delete-shot").addEventListener("click", async () => {
    if (!trajectorySelect.value) return;
    try {
      await fetchJson(`/projects/${state.projectId}/trajectories/${trajectorySelect.value}`, {method: "DELETE"});
      await fetchTrajectories();
      setStatus("Shot deleted.");
    } catch (error) { setStatus(error.message, "error"); }
  });
  document.getElementById("reset-view").addEventListener("click", () => {
    if (state.rendering) { setStatus("Wait for the export to finish before resetting the viewer."); return; }
    launchViewer();
  });
  try {
    state.capabilities = await fetchJson("/capabilities");
    document.getElementById("generation-provider").addEventListener("change", updateGenerationActions);
    if (state.capabilities.astra && !state.capabilities.hunyuan) document.getElementById("generation-provider").value = "astra";
    updateGenerationActions();
    if (!state.capabilities.da3) {
      workflowCreateButton.querySelector(".flow-note").textContent = "Requires the optional DA3 runtime and model weights.";
    }
    if (!state.capabilities.runway) {
      document.querySelector(".runway-field").hidden = true;
      enhanceButton.title = "Configure a Runway API key to enable optional enhancement.";
      const note = document.createElement("p");
      note.className = "ghost-note";
      note.textContent = "Local MP4 export is ready. AI enhancement requires a Runway API key.";
      document.getElementById("render-form").append(note);
    }
  } catch (error) { setStatus(`Could not check optional tools: ${error.message}`, "error"); }
  await loadProjectLibrary();
  await restoreSession();
}

initializeStudio().catch(error => setStatus(`Studio startup failed: ${error.message}`, "error"));


function updateGenerationActions() {
  const provider = document.getElementById("generation-provider").value;
  const ready = Boolean(state.capabilities?.[provider]);
  generateImageButton.disabled = state.generating || !ready;
  generateTextButton.disabled = state.generating || !ready;
  document.getElementById("generation-provider").disabled = Boolean(state.generating);
  document.getElementById("texture-option").hidden = provider !== "hunyuan";
  document.getElementById("generation-provider-note").textContent = provider === "astra"
    ? (ready ? "Uses the OpenAI API (billed). Builds a colored, simplified GLB from text or a reference image. No local GPU; no photoreal textures. Image references are sent to OpenAI."
             : "Set OPENAI_API_KEY on the server and restart. Astra creates simplified procedural furniture, not a detailed reconstruction.")
    : (ready ? "Local Hunyuan runtime detected. Requires working CUDA and model weights. Start with shape only."
             : "Install the optional Hunyuan runtime and configure CUDA. Mesh uploads and the demo work independently.");
}
