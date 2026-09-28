# Deco AI integrations: setup, choices, and improvement plan

Reviewed 28 September 2026 against the implementation and the primary sources linked below. The recommendations are engineering judgments for Deco, not a claim that one model wins every benchmark.

## Recommended configuration

| Need | My recommendation for Deco | Status in this project |
|---|---|---|
| Simple furniture from text | GPT-6 Astra → validated primitive recipe → local GLB | Implemented, API key required |
| Rough furniture approximation from a photo | Astra vision → the same procedural builder | Implemented; not a faithful scan |
| Detailed object from a photo | Keep Hunyuan 2.0 initially; benchmark TRELLIS.2 for the next quality upgrade | Hunyuan integrated; TRELLIS.2 requires a new adapter |
| Detailed object from text | Create/review an isolated reference image, then use an image-to-3D model | HunyuanDiT → Hunyuan is integrated; an OpenAI image stage is a proposed upgrade |
| A convincing room captured on video | COLMAP → Brush for a local open-source pipeline; Postshot for an integrated desktop workflow | Export standard splat PLY and import it into Deco |
| Fast room preview | Selected video frames → existing DA3 path | Image set input supported; extract video frames first |
| Next room reconstruction model to evaluate | WorldMirror 2.0 from HY-World 2.0 | Not yet integrated or benchmarked here |
| Creative video polishing | Aleph 2, with preservation-focused instructions | Adapter supports `aleph2`; legacy `gen4_aleph` remains supported |
| Faithful video finishing | Improve the 3D render first; then conservative denoising/upscaling | Render is integrated; a separate restoration provider is future work |

Keep the present demo environment for presentations. Use a separate GPU environment while bringing up Hunyuan or DA3. In this session `nvidia-smi` could not communicate with the NVIDIA driver; that is a runtime prerequisite to resolve before local GPU testing. Package detection in `/capabilities` does not check model access, loaded weights, CUDA, or provider account permissions.

## 1. What GPT-6 Astra can replace

The [official Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra) documents text/image inputs and text output, plus structured outputs and tools. It does not document native GLB, mesh, or Gaussian-splat output.

The new Deco integration makes this useful for 3D anyway:

1. Astra receives an object description, optionally with a photo.
2. It returns a strict JSON object containing boxes, cylinders, and ellipsoids.
3. Pydantic validates at most 64 parts, bounded sizes/positions, finite numbers, and RGB colors.
4. Trimesh constructs and exports the GLB locally, centered in X/Y with its base at Z=0.
5. Deco stores the GLB and a `.recipe.json` beside the assets, preserving provenance in metadata.

There is no execution of model-generated Python or shell code. The API uses `gpt-6-astra` through Responses with `store=false` and a JSON schema. This architecture follows the documented [Structured Outputs mechanism](https://developers.openai.com/api/docs/guides/structured-outputs); procedural mesh construction is our own implementation.

This is useful for tables, shelving, sofas, cabinetry, lamps, and architectural placeholders. It is not an adequate substitute for intricate upholstery, carved objects, organic shapes, product-exact silhouettes, UV maps, or PBR texture generation. A photograph cannot establish exact metric dimensions by itself: provide dimensions in the prompt and verify the result. “Meters” is the procedural builder's convention; imported room coordinates may still need calibration.

### Setup and UI

Install/update the base environment, then set a server-side API key with access to Astra:

```bash
.venv/bin/python -m pip install -r requirements.txt
# Enter the secret without putting its value in shell history:
read -rsp 'OpenAI API key: ' OPENAI_API_KEY
export OPENAI_API_KEY
printf '\n'
./scripts/demo.sh
```

Alternatively, put `OPENAI_API_KEY=...` or `DECO_OPENAI_API_KEY=...` in the existing ignored `.env` file. Do not replace that file wholesale; it may already contain other settings. `DECO_OPENAI_API_KEY` takes precedence. Restart the server after changing keys. An API account/key is separate from selecting Astra in Codex.

Open a room → **AI tools** → **Object provider** → **GPT-6 Astra**. The UI identifies this as a billed API operation and notes that reference images are sent to OpenAI. It needs no local CUDA or Hunyuan install. No paid live Astra requests were made during this implementation; account access and actual output quality remain to be validated with your key.

Suggested text prompt:

> One Scandinavian oak coffee table, 1.2 m wide, 0.7 m deep, 0.42 m tall. Rounded-looking top approximated with simple forms, four tapered-looking legs, warm natural wood colors, no accessories. Keep the base on the floor.

For image input, choose **Generate From Image**. The Prompt field may specify known dimensions or which object to approximate. Inputs are limited to 20 MB and resized to a maximum 1536-pixel dimension before transmission. The output is a colored procedural approximation, not a textured reconstruction.

### API examples

Choose a real project ID from `GET /projects`:

```bash
curl http://localhost:8000/projects
export DECO_PROJECT_ID='proj_replace_me'

curl --fail-with-body -X POST \
  "http://localhost:8000/projects/${DECO_PROJECT_ID}/assets/astra/from-text" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Oak coffee table","prompt":"One oak coffee table, 1.2 m wide, 0.7 m deep and 0.42 m tall, four legs."}'

curl --fail-with-body -X POST \
  "http://localhost:8000/projects/${DECO_PROJECT_ID}/assets/astra/from-image" \
  -F 'file=@/absolute/path/chair.png' \
  -F 'name=Reference chair' \
  -F 'prompt=Approximate this chair. Overall height is 0.85 m; seat height is 0.45 m.'
```

These endpoints register an asset. The editor also creates a scene instance automatically; direct API callers must separately `POST /projects/{id}/objects` using the returned `asset.id`.

### A better high-detail text-to-3D design

For detailed products I would use Astra to clarify the object specification and create a reference-image prompt; use an image-generation model for the picture; let the user approve that picture; and only then spend GPU time on Hunyuan or TRELLIS.2. This separates prompt/image failures from geometry failures. OpenAI lists image generation as a separate model family in its [model catalog](https://developers.openai.com/api/docs/models). That hybrid image-generation stage is a recommendation, not an implemented provider in Deco today.

## 2. Hunyuan: image-to-3D and text-to-3D

### Hardware and installation

The current adapter targets **Hunyuan3D 2.0**, not 2.1. Upstream reports approximately 6 GB VRAM for shape and 16 GB for shape plus texture. Treat these as upstream figures, not guaranteed peaks for Deco; retained models and other GPU processes increase memory demand. Upstream's texture path also builds two native renderer extensions. See [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2).

Start by making `nvidia-smi` work on the host. If running in a container, also verify GPU device/runtime access. A Python package install does not repair a missing or inaccessible kernel driver.

Create a separate environment:

```bash
python3.11 -m venv .venv-ai
source .venv-ai/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Install a compatible CUDA-enabled `torch`/`torchvision` combination using the [PyTorch installation selector](https://pytorch.org/get-started/locally/). Match the CUDA wheel, driver, and any toolkit used to compile extensions. Then:

```bash
python -m pip install -r requirements-hunyuan.txt
python -m pip check
python - <<'PY'
import torch
print('PyTorch:', torch.__version__, 'CUDA build:', torch.version.cuda)
print('CUDA available:', torch.cuda.is_available())
assert torch.cuda.is_available(), 'Resolve the GPU runtime before continuing'
print('GPU:', torch.cuda.get_device_name(0))
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
print('Shape runtime imports successfully')
PY
```

A successful import is only a preflight check. Run one real shape request before enabling texture or presenting generation live. After a working setup, save `python -m pip freeze > configs/ai-working-requirements.txt` along with the CUDA/driver versions and model IDs. The optional requirements currently contain broad ranges and are not a reproducible GPU lockfile.

Set the known adapter configuration explicitly:

```bash
export DECO_HUNYUAN_DEVICE=cuda
export DECO_HUNYUAN_SHAPE_MODEL=tencent/Hunyuan3D-2
export DECO_HUNYUAN_SHAPE_SUBFOLDER=hunyuan3d-dit-v2-0
export DECO_HUNYUAN_TEXTURE_MODEL=tencent/Hunyuan3D-2
export DECO_HUNYUAN_TEXT2IMAGE_MODEL=Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled
DECO_PYTHON="$PWD/.venv-ai/bin/python" ./scripts/demo.sh
```

The launcher otherwise uses `.venv`, even if `.venv-ai` is activated. Model weights download on first use unless already cached. Allow disk space and prewarm the exact flow before a live presentation.

### Image-to-3D first

Use one isolated object with the entire silhouette visible, a clear three-quarter view, diffuse lighting, and little background clutter. Avoid a whole furnished-room image for an object generator. Thin legs, glass, mirrors, and occluded backs are useful stress cases, not good first smoke tests.

In the UI choose **Hunyuan** and **Shape only**. The editor now defaults to this lower-dependency path. After it works, try **Textured**.

For API control:

```bash
curl --fail-with-body -X POST \
  "http://localhost:8000/projects/${DECO_PROJECT_ID}/assets/generate-from-image" \
  -F 'file=@/absolute/path/chair.png' \
  -F 'name=Generated chair' \
  -F 'include_texture=false' \
  -F 'remove_background=true' \
  -F 'seed=42' \
  -F 'num_inference_steps=30' \
  -F 'octree_resolution=256'
```

Those values are Deco's baseline settings with a fixed seed for comparisons. Increase mesh resolution only after you have a good silhouette and sufficient memory. More steps do not repair missing observations or a poor source image.

### Enable texture

When the pip runtime cannot import the texture rasterizers, use a compatible checkout and build them in the same environment as the application. This repository already has an `external/Hunyuan3D-2` checkout; inspect its revision before using it. Do not overwrite it with another clone.

```bash
export DECO_HUNYUAN_REPO_PATH="$PWD/external/Hunyuan3D-2"
python -m pip install -e "$DECO_HUNYUAN_REPO_PATH"
(cd "$DECO_HUNYUAN_REPO_PATH/hy3dgen/texgen/custom_rasterizer" && python setup.py install)
(cd "$DECO_HUNYUAN_REPO_PATH/hy3dgen/texgen/differentiable_renderer" && python setup.py install)
python -c 'from hy3dgen.texgen import Hunyuan3DPaintPipeline; print("Texture runtime imports")'
```

These build steps follow the upstream 2.0 layout; they need a working compiler/CUDA toolkit. Retry the same reference image with `include_texture=true`. If texture fails, retain the shape-only workflow while diagnosing the extension or VRAM error.

### Text-to-3D

The existing text path runs **HunyuanDiT text-to-image → Hunyuan shape → optional paint**. It is not a direct text-conditioned mesh model. The extra image model increases downloads and memory needs.

```bash
curl --fail-with-body -X POST \
  "http://localhost:8000/projects/${DECO_PROJECT_ID}/assets/generate-from-text" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Oak chair","prompt":"A single modern oak dining chair, three-quarter product view, full object visible, plain white background, soft studio lighting, no text","include_texture":false,"seed":42,"num_inference_steps":30,"octree_resolution":256}'
```

For production, expose the intermediate image, allow approval/regeneration, and persist it with the output mesh. This is a higher-value improvement than simply increasing the number of diffusion steps.

### Better object models to evaluate

- **TRELLIS.2:** my first challenger for detailed single-image objects and richer material output. Its official implementation requires Linux and at least 24 GB NVIDIA GPU memory; it models base color, roughness, metallic, and opacity. The project declares its code/model MIT, while dependencies have separate terms. Build it in its own environment and import exported GLBs into Deco before writing an adapter. [Official repository](https://github.com/microsoft/TRELLIS.2).
- **Hunyuan3D 2.1:** evaluate when PBR materials are a priority. Its upstream memory figures are substantially higher: 10 GB shape, 21 GB texture, 29 GB combined. This needs a version-specific adapter and environment; changing the 2.0 model environment variable is not sufficient. [Official repository](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1).
- **Multiple actual product views:** preferable to asking a single-image system to invent hidden structure. The current Deco upload contract accepts one image; multiview support needs a new input schema and a compatible model pipeline. Independent invented views can contradict one another.

My evaluation set would include an upholstered sofa, a thin-leg chair, open shelving, a lamp, a glass table, and an ornate object. Score silhouette, back-side plausibility, leg/support connectivity, materials, polygon count, GLB size, scale, latency, and peak VRAM. Inspect from four views before accepting an asset.

## 3. Room video to 3D: what is best here?

For this product, I would start with **a real captured room trained into a Gaussian splat**, then use Deco to place new furniture. “Best” depends on whether you prioritize a photoreal walkthrough, fast approximate geometry, or a dimensionally reliable editable room mesh.

| Approach | When I would use it | Main tradeoff |
|---|---|---|
| COLMAP + Brush | Repeatable local reconstruction and integration control | Camera calibration/alignment plus a per-scene training stage |
| Postshot | Fastest operator workflow for a prepared presentation capture | External desktop tool rather than an in-app pipeline |
| DA3 | Immediate preview from selected frames in the existing project | Quality, scale, and consistency must be checked before final use |
| WorldMirror 2.0 | Next feed-forward reconstruction benchmark | New adapter, dependencies, and capture-level evaluation needed |
| Photogrammetry or RGB-D/LiDAR mesh | Measured geometry, collision, floor/wall editing | Different output and quality criteria from photoreal splat viewing |

Brush trains from COLMAP or Nerfstudio datasets and supports multiple desktop GPU platforms. Postshot accepts video directly and can export PLY from its Splat profile. These capabilities make both practical sources for Deco's existing room import. My preference for fitted splats for the presentation is an engineering recommendation, not a head-to-head benchmark result. [Brush](https://github.com/ArthurBrussee/brush), [Postshot workflow](https://www.jawset.com/docs/d/Postshot%2BUser%2BGuide/Getting%2BStarted).

WorldMirror 2.0 is the reconstruction component of HY-World 2.0 and accepts multi-view/video inputs to predict geometry, cameras, and 3DGS attributes. It is distinct from Hunyuan3D object generation and from text-to-world synthesis. I would benchmark it against DA3 on the same room before replacing the current adapter. [HY-World 2.0](https://github.com/Tencent-Hunyuan/HY-World-2.0).

A splat is not a CAD model or a collection of removable furniture objects. Existing furniture in the capture stays baked into the room. For virtual staging of an empty room, capture it empty or add a separate segmentation/removal/reconstruction pipeline. New meshes also need floor alignment, scale calibration, occlusion, and lighting work to blend convincingly.

### Capture protocol I suggest

1. Capture one static room without people moving through it. Keep lighting and exposure stable; avoid changing lenses or zoom mid-shot.
2. Walk slowly around the perimeter and through a few interior positions. Translate the camera, rather than only spinning in place. Aim for repeated overlapping views of each region.
3. Include wall/floor junctions, corners, and furniture from multiple sides. Add higher and lower passes where practical. Revisit the starting area to help assess accumulated drift.
4. Keep motion blur low. Mirrors, shiny surfaces, blank walls, and windows are hard cases; ensure nearby textured surfaces also appear in the views.
5. Record a known distance in the room. Check reconstructed scale against it before interpreting mesh dimensions as real-world measurements.
6. Hold out a few frames for evaluation. A good training-view image alone does not show whether the room is stable from a new viewpoint.

These are starting capture practices, not model guarantees. COLMAP's [capture/reconstruction tutorial](https://colmap.github.io/tutorial.html) gives the underlying photogrammetry workflow.

### Extract a manageable frame set

The current Deco room endpoint accepts images, not MP4. With FFmpeg installed, start with a short 15-second, steadily moving section at 2 fps:

```bash
mkdir -p /tmp/deco-room-frames
ffmpeg -n -i /absolute/path/room.mp4 -t 15 \
  -vf "fps=2,scale=1280:-2" -q:v 2 \
  /tmp/deco-room-frames/frame_%04d.jpg
```

Use a new output directory for each capture. Inspect all extracted frames and remove blurred, redundant, or moving-person frames. Thirty frames is an initial trial, not a recommendation to feed all frames of a long video into one DA3 call. GPU memory grows with view count and resolution. For fitted splats, use a larger well-covered set after alignment succeeds.

For the highest control, run camera estimation and image undistortion in COLMAP, import the resulting dataset into Brush, train and inspect held-out views, export a standard Gaussian PLY, and use **Open an existing room gsplat** in Deco. Confirm the export contains `scale_*`, `rot_*`, `opacity`, and `f_dc_*` properties; a point-cloud PLY is not interchangeable with a Gaussian-splat PLY.

### DA3 setup and preview

Use a separate environment if the Hunyuan dependencies conflict:

```bash
python3.11 -m venv .venv-da3
source .venv-da3/bin/activate
python -m pip install -r requirements.txt
# Install the CUDA-enabled PyTorch build appropriate to the host first.
python -m pip install -r requirements-da3.txt
python -m pip check
python -c 'import torch; from depth_anything_3.api import DepthAnything3; print(torch.cuda.is_available())'

export DECO_DA3_MODEL=depth-anything/DA3NESTED-GIANT-LARGE-1.1
export DECO_DA3_DEVICE=cuda
export DECO_DA3_PROCESS_RES=504
DECO_PYTHON="$PWD/.venv-da3/bin/python" ./scripts/demo.sh
```

Use the explicit model setting even if an older `.env` already exists. The refreshed nested checkpoint supports Gaussian output; a smaller depth-only checkpoint is not a drop-in replacement. Upstream documents additional Gaussian-head dependencies, including its pinned `gsplat` build; if your installed DA3 version requires those imports, follow the upstream installation instructions in this isolated environment. Deco's export-only path avoids rendering with that library, but does not guarantee every upstream version can omit it. [DA3 repository](https://github.com/ByteDance-Seed/Depth-Anything-3).

The nested checkpoint's model table marks it **CC BY-NC 4.0**. Account for that constraint before choosing it for a commercial product. Do not assume all checkpoints share one license.

Choose **Create a room from photos**, then select the extracted JPEGs. The adapter calls inference with Gaussian output enabled and registers the exported room PLY. It does not currently accept external camera poses or perform explicit floor/scale calibration. DA3 supports pose-conditioned inference upstream, making that a useful future extension. [DA3 API](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/docs/API.md).

## 4. Video enhancement

Use two distinct modes in the product:

- **Faithful finishing:** improve geometry/materials/rendering and apply conservative restoration or upscaling. Evaluate whether edges and textures changed.
- **Creative restyling:** use Aleph with a preservation-focused prompt and review the whole output. It can alter furniture details, windows, dimensions, or camera interpretation. An attractive video is not proof that the underlying 3D scene improved.

The current Runway model catalog lists `aleph2` for video editing and separately offers video upscaling. Deco now supports Aleph 2's request shape, omitting the old ratio field; its existing `gen4_aleph` configuration remains available. A separate restoration/upscale integration is not implemented. [Runway model catalog](https://docs.dev.runwayml.com/guides/models/).

### Configure and run

Create a Runway developer account/API key with credits and verify model access. Follow the [Runway API guide](https://docs.dev.runwayml.com/guides/using-the-api/) for account setup and request lifecycle.

```bash
.venv/bin/python -m pip install -r requirements.txt
read -rsp 'Runway API key: ' DECO_RUNWAY_API_KEY
export DECO_RUNWAY_API_KEY
printf '\n'
export DECO_RUNWAY_API_VERSION=2024-11-06
export DECO_RUNWAY_VIDEO_MODEL=aleph2
export DECO_RUNWAY_POLL_INTERVAL_SECONDS=5
./scripts/demo.sh
```

The project also accepts `RUNWAYML_API_SECRET`. Set only the intended key source and restart the server. No paid enhancement request was made during these changes; Aleph 2 request construction is verified against the installed SDK and covered by a mocked task test.

Render a short clip locally first, ideally with the intended output aspect ratio. In **Shots & export**, set the enhancement prompt and click **Enhance Last Render**. Confirm the currently selected clip is the one you intend to submit; the API uploads that local video to Runway.

Suggested prompt:

> Preserve the exact room layout, camera movement, furniture count, object silhouettes, and positions. Refine material appearance and soft daylight, reduce floating splat artifacts, and maintain stable surfaces across frames. Keep all windows, doors, and architectural proportions unchanged. No new objects, text, or camera cuts.

This requests preservation; it cannot enforce geometric fidelity. Compare the original and result at the beginning, middle, and end, and watch for temporal flicker and changing furniture geometry.

API equivalent, using a filename returned by the render list:

```bash
export DECO_RENDER_FILE='replace_with_render_filename.mp4'
curl --fail-with-body -X POST \
  "http://localhost:8000/projects/${DECO_PROJECT_ID}/renders/${DECO_RENDER_FILE}/enhance" \
  -H 'Content-Type: application/json' \
  -d '{"width":1280,"height":720,"ai_wait_timeout_seconds":900,"prompt":"Preserve the exact room layout and camera movement. Refine daylight and material appearance, reduce floating artifacts, and keep all furniture silhouettes and positions unchanged."}'
```

The service polls and downloads a completed output. If the wait expires, it returns the task ID and last status. It currently has no durable resume/poll UI: do not resubmit blindly, since that creates a new task. Check the existing task in the provider account. A persisted task record with resume and cancellation is the highest-priority enhancement improvement.

For Aleph 2 the adapter sends the source video and prompt; the width/height fields do not resize the input or force the output resolution. Check the provider's current duration, input, and delivery limits before submitting long or high-resolution clips. Keep the raw render as the source of truth.

## 5. Improvements I would prioritize

| Priority | Area | Specific improvement | Acceptance check |
|---|---|---|---|
| P0 | All AI jobs | Persistent queue, per-GPU concurrency limit, progress, timeout, cancellation, retry/resume | Refresh/restart preserves job state; repeated clicks cannot silently create duplicate paid jobs |
| P0 | Runtime | Separate model worker environments, preflight and prewarm, explicit unloading/offload | Measure cold/warm latency and peak VRAM; no model overlap OOM |
| P0 | Room coordinates | Store camera poses, floor plane, scene origin, unit scale, and world transforms | A 1 m object stays 1 m and rests on the floor after reload |
| P0 | Object ingest | Normalize up axis, origin, real-world dimensions, and sensible spawn position | Hunyuan, Astra, and uploaded GLBs all arrive upright and at usable scale |
| P1 | Text-to-3D | Persist/preview the intermediate image; allow approval before meshing | Reject a bad concept without paying for shape and paint stages |
| P1 | Image-to-3D | Segmentation preview, preserve valid input alpha, multiview input, mesh cleanup | Thin legs survive, fewer floating components, correct subject isolation |
| P1 | Object quality | Four-view QA renders, triangle/texture budgets, PBR materials, LODs | Several generated objects remain responsive in the browser |
| P1 | Room capture | Video upload, blur/duplicate filtering, coverage report, frame cap | A bad capture gets actionable feedback before GPU inference |
| P1 | Room reconstruction | Fit/refine splats after feed-forward initialization and evaluate held-out views | Less drift/floating geometry than baseline DA3 on the same capture |
| P1 | Viewer | Preserve higher-order spherical harmonics, improve mesh/splat occlusion and lighting | Consistent appearance on camera moves; objects blend into the room |
| P1 | Video | Persist provider task IDs, compare raw/enhanced, add faithful finishing separately | No lost paid job and clear distinction between restyling and restoration |
| P2 | Astra | Editable recipe parameters and assembly-level parts | User can change table width/leg height without regenerating everything |
| P2 | Real products | Retrieve manufacturer/catalog GLBs before generating approximations | Exact SKU and dimensions when the asset exists |

Two current implementation details matter: Hunyuan service instances are created per request, so their internal model caches are not a durable shared worker cache; and the room viewer currently reads DC color rather than the full view-dependent spherical-harmonic representation. Both can matter more than swapping model names.

## 6. Troubleshooting and validation status

| Symptom | Next check |
|---|---|
| Astra controls disabled | Set the server-side OpenAI key, restart, and inspect `/capabilities` |
| Astra 401/403/404 | Key validity, project permissions, and account access to `gpt-6-astra` |
| Astra 429 | API quota/rate limits; avoid blind retries |
| Astra output too crude | Use a detailed mesh model or a real catalog asset; primitives have deliberate limits |
| Hunyuan CUDA error | Host driver, container GPU access, and `torch.cuda.is_available()` |
| Hunyuan texture import error | Build the two native extensions in the application environment; use shape only meanwhile |
| GPU OOM | Lower frame count/resolution or shape resolution; unload other model workers; disable texture first |
| DA3 produces depth but no room splat | Confirm a Gaussian-capable checkpoint and compatible Gaussian-head dependencies |
| Imported room is tilted or wrong scale | Calibrate coordinate frame and scale; do not compensate by guessing every object's transform |
| Runway returns pending | Retain/check the returned task ID; the current UI does not resume it automatically |
| Enhanced video looks better but changes design | Prefer the raw render or conservative finishing; review model output against the original |

Verified locally: bounded Astra recipes, real GLB creation, API routing, reference-image encoding, missing-key behavior, and Aleph 2 request fields using mocked provider responses. All 56 backend tests pass. An isolated Chrome check also verified provider selection, missing-key controls, and both generation flows through scene insertion using mocked provider responses, with no browser errors. Not verified in this environment: live Astra quality/account access, live paid Runway output, GPU Hunyuan/DA3 inference, or benchmark comparisons with TRELLIS.2 and WorldMirror 2.0.
