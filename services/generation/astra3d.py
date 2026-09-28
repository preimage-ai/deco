"""GPT-6 Astra plans bounded primitives; local code creates a real GLB.

This is procedural furniture approximation, not native neural mesh reconstruction.
No model-generated Python or shell code is executed.
"""
from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Annotated, Literal

import httpx
import numpy as np
import trimesh
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.assets.file_ingest import AssetIngestService
from services.generation.hunyuan3d import GenerationUnavailableError

Number = Annotated[float, Field(ge=-20, le=20, allow_inf_nan=False)]
Dimension = Annotated[float, Field(gt=0, le=20, allow_inf_nan=False)]
Vector = Annotated[list[Number], Field(min_length=3, max_length=3)]
Dimensions = Annotated[list[Dimension], Field(min_length=3, max_length=3)]
Color = Annotated[list[Annotated[int, Field(ge=0, le=255)]], Field(min_length=3, max_length=3)]


class Primitive(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["box", "cylinder", "ellipsoid"]
    size: Dimensions
    position: Vector
    rotation_euler: Vector
    color: Color


class ObjectRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(max_length=1000)
    parts: list[Primitive] = Field(min_length=1, max_length=64)


class AstraGenerationError(RuntimeError):
    """The provider failed or did not return a usable object specification."""


def recipe_to_scene(recipe: ObjectRecipe) -> trimesh.Scene:
    meshes = []
    for part in recipe.parts:
        if part.kind == "box":
            mesh = trimesh.creation.box(extents=part.size)
        elif part.kind == "cylinder":
            mesh = trimesh.creation.cylinder(radius=1, height=1, sections=32)
            mesh.apply_scale([part.size[0] / 2, part.size[1] / 2, part.size[2]])
        else:
            mesh = trimesh.creation.icosphere(subdivisions=2, radius=1)
            mesh.apply_scale(np.asarray(part.size) / 2)
        mesh.apply_transform(trimesh.transformations.euler_matrix(*part.rotation_euler))
        mesh.apply_translation(part.position)
        mesh.visual.vertex_colors = [*part.color, 255]
        meshes.append(mesh)
    scene = trimesh.Scene(meshes)
    bounds = scene.bounds
    # Standardize placement: centered horizontally, base resting at Z=0.
    scene.apply_translation([-float(bounds[:, 0].mean()), -float(bounds[:, 1].mean()), -float(bounds[0, 2])])
    return scene


class Astra3DService:
    def __init__(self, ingest: AssetIngestService, *, api_key: str | None, model: str = "gpt-6-astra"):
        self.ingest = ingest
        self.api_key = api_key
        self.model = model

    def generate(self, *, project_id: str, name: str, prompt: str, image_path: Path | None = None):
        self.ingest.repo.get_project(project_id)  # Fail before a billed request if missing.
        if not self.api_key:
            raise GenerationUnavailableError("Set OPENAI_API_KEY or DECO_OPENAI_API_KEY to use GPT-6 Astra procedural objects.")
        content = [{"type": "input_text", "text": prompt}]
        if image_path is not None:
            content.append({"type": "input_image", "image_url": self._image_data(image_path), "detail": "high"})
        recipe = self._request_recipe(content)
        scene = recipe_to_scene(recipe)
        with tempfile.TemporaryDirectory(prefix="deco-astra-") as directory:
            output = Path(directory) / "object.glb"
            scene.export(str(output))
            asset = self.ingest.ingest_object_mesh(project_id, name, output)
        recipe_path = self.ingest.repo.project_dir(project_id) / "assets" / f"{asset.id}.recipe.json"
        recipe_path.write_text(recipe.model_dump_json(indent=2) + "\n")
        metadata = {**asset.metadata, "generator": self.model,
                    "generation_method": "procedural_primitives", "source_type": "image" if image_path else "text",
                    "prompt": prompt, "textured": False, "units": "meters",
                    "dimensions_estimated": True, "part_count": len(recipe.parts),
                    "recipe_uri": str(recipe_path.relative_to(self.ingest.repo.root))}
        manifest = self.ingest.repo.update_asset(project_id, asset.id, {"kind": "generated_glb", "metadata": metadata})
        return next(item for item in manifest.assets if item.id == asset.id)

    @staticmethod
    def _image_data(path: Path) -> str:
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Reference image must be at most 20 MB.")
        try:
            with Image.open(path) as source:
                if source.width * source.height > 40_000_000:
                    raise ValueError("Reference image must contain at most 40 megapixels.")
                source.seek(0)
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1536, 1536))
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=90)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Upload a valid PNG, JPEG, or WebP reference image.") from exc
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def _request_recipe(self, content: list[dict]) -> ObjectRecipe:
        instructions = (
            "Design ONE furniture or decor object using 1 to 64 colored primitives. "
            "Use meters, Z up, X width, Y depth; front faces -Y. size is full XYZ dimensions, "
            "position is the primitive center, rotation_euler is XYZ radians. A cylinder's axis "
            "is local Z and size X/Y are diameters. Ellipsoid size is full diameters. "
            "Create a recognizable, proportionate, useful approximation with coherent supporting parts. "
            "Honor supplied dimensions; otherwise estimate ordinary furniture dimensions. "
            "For photos approximate the main object, omit the background and shadows. "
            "Prefer 8-30 parts. Use solid RGB colors. No textures, text, URLs, or executable code. "
            "Keep every coordinate between -20 and 20, every size greater than 0 and at most 20. "
            "State that this is a procedural approximation in the description."
        )
        payload = {"model": self.model, "store": False,
                   "reasoning": {"effort": "medium"}, "max_output_tokens": 12000,
                   "instructions": instructions, "input": [{"role": "user", "content": content}],
                   "text": {"format": {"type": "json_schema", "name": "furniture_recipe", "strict": True,
                                         "schema": ObjectRecipe.model_json_schema()}}}
        try:
            with httpx.Client(timeout=180) as client:
                response = client.post("https://api.openai.com/v1/responses", json=payload,
                                       headers={"Authorization": f"Bearer {self.api_key}"})
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            message = ("Check the API key and access to gpt-6-astra." if code in (401, 403, 404)
                       else "Check API quota and retry later." if code == 429
                       else "The provider rejected or could not complete the request.")
            raise AstraGenerationError(f"OpenAI request failed ({code}). {message}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AstraGenerationError("OpenAI request failed or timed out. Check connectivity before retrying.") from exc
        if data.get("status") != "completed":
            raise AstraGenerationError("Astra did not finish the object plan. Try a simpler description.")
        parts = [part for item in data.get("output", []) if item.get("type") == "message"
                 for part in item.get("content", [])]
        if any(part.get("type") == "refusal" for part in parts):
            raise AstraGenerationError("Astra declined this request. Try a different furniture description.")
        output = "".join(part.get("text", "") for part in parts if part.get("type") == "output_text")
        try:
            return ObjectRecipe.model_validate_json(output)
        except (ValidationError, ValueError) as exc:
            raise AstraGenerationError("Astra returned an invalid object plan; no mesh was saved.") from exc
