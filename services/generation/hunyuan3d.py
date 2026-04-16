"""Hunyuan3D adapter for image-to-3D and text-to-3D generation."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.assets.file_ingest import AssetIngestService
from services.scene_core.project_manifest import AssetRecord


class GenerationUnavailableError(RuntimeError):
    """Raised when Hunyuan3D cannot run in the current environment."""


@dataclass(frozen=True)
class Hunyuan3DConfig:
    """Runtime configuration for the Hunyuan3D adapter."""

    repo_path: Path
    shape_model: str
    shape_subfolder: str
    texture_model: str
    text2image_model: str
    device: str = "auto"


class Hunyuan3DService:
    """Lazy-loading wrapper around the upstream Hunyuan3D pipelines."""

    def __init__(self, ingest: AssetIngestService, config: Hunyuan3DConfig) -> None:
        self._ingest = ingest
        self._config = config
        self._shape_pipeline: Any | None = None
        self._texture_pipeline: Any | None = None
        self._text2image_pipeline: Any | None = None
        self._background_remover: Any | None = None

    def generate_from_image(
        self,
        *,
        project_id: str,
        name: str,
        image_path: Path,
        include_texture: bool = True,
        remove_background: bool = True,
        seed: int = 0,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        octree_resolution: int = 256,
        num_chunks: int = 20000,
    ) -> AssetRecord:
        """Generate a GLB from an input image and register it as a project asset."""
        runtime = self._runtime()
        image = runtime["Image"].open(image_path).convert("RGBA")
        image = self._prepare_image(image, remove_background=remove_background)
        mesh = self._shape_generator()(
            image=image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=runtime["torch"].manual_seed(seed),
            octree_resolution=octree_resolution,
            num_chunks=num_chunks,
            output_type="trimesh",
        )[0]
        if include_texture:
            mesh = self._texture_generator()(mesh, image=image)
        return self._store_generated_mesh(
            project_id=project_id,
            name=name,
            mesh=mesh,
            source_type="image",
            include_texture=include_texture,
            seed=seed,
        )

    def generate_from_text(
        self,
        *,
        project_id: str,
        name: str,
        prompt: str,
        include_texture: bool = True,
        remove_background: bool = True,
        seed: int = 0,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        octree_resolution: int = 256,
        num_chunks: int = 20000,
    ) -> AssetRecord:
        """Generate a GLB from a prompt via the upstream text-to-image stage."""
        image = self._text_to_image_generator()(prompt, seed=seed)
        image = self._prepare_image(image.convert("RGBA"), remove_background=remove_background)
        mesh = self._shape_generator()(
            image=image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=self._runtime()["torch"].manual_seed(seed),
            octree_resolution=octree_resolution,
            num_chunks=num_chunks,
            output_type="trimesh",
        )[0]
        if include_texture:
            mesh = self._texture_generator()(mesh, image=image)
        return self._store_generated_mesh(
            project_id=project_id,
            name=name,
            mesh=mesh,
            source_type="text",
            include_texture=include_texture,
            seed=seed,
            prompt=prompt,
        )

    def _prepare_image(self, image, *, remove_background: bool):
        if remove_background or image.mode == "RGB":
            return self._background_worker()(image.convert("RGB"))
        return image

    def _store_generated_mesh(
        self,
        *,
        project_id: str,
        name: str,
        mesh,
        source_type: str,
        include_texture: bool,
        seed: int,
        prompt: str | None = None,
    ) -> AssetRecord:
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
            output_path = Path(tmp.name)
        try:
            mesh.export(output_path)
            asset = self._ingest.ingest_object_mesh(project_id, name, output_path)
            metadata = dict(asset.metadata)
            metadata.update(
                {
                    "generator": "hunyuan3d-2",
                    "source_type": source_type,
                    "textured": include_texture,
                    "seed": seed,
                }
            )
            if prompt is not None:
                metadata["prompt"] = prompt
            updated = self._ingest.repo.update_asset(
                project_id,
                asset.id,
                {
                    "kind": "generated_glb",
                    "metadata": metadata,
                },
            )
            return next(item for item in updated.assets if item.id == asset.id)
        finally:
            output_path.unlink(missing_ok=True)

    def _shape_generator(self):
        if self._shape_pipeline is None:
            runtime = self._runtime()
            self._shape_pipeline = runtime["Hunyuan3DDiTFlowMatchingPipeline"].from_pretrained(
                self._config.shape_model,
                subfolder=self._config.shape_subfolder,
                variant="fp16",
            )
        return self._shape_pipeline

    def _texture_generator(self):
        if self._texture_pipeline is None:
            runtime = self._runtime()
            self._texture_pipeline = runtime["Hunyuan3DPaintPipeline"].from_pretrained(
                self._config.texture_model
            )
        return self._texture_pipeline

    def _text_to_image_generator(self):
        if self._text2image_pipeline is None:
            runtime = self._runtime()
            self._text2image_pipeline = runtime["HunyuanDiTPipeline"](
                model_path=self._config.text2image_model,
                device=self._device(runtime["torch"]),
            )
        return self._text2image_pipeline

    def _background_worker(self):
        if self._background_remover is None:
            runtime = self._runtime()
            self._background_remover = runtime["BackgroundRemover"]()
        return self._background_remover

    def _runtime(self) -> dict[str, Any]:
        if not self._config.repo_path.exists():
            raise GenerationUnavailableError(
                f"Hunyuan3D repo not found at {self._config.repo_path}"
            )
        try:
            import torch
            from PIL import Image
            from hy3dgen.rembg import BackgroundRemover
            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
            from hy3dgen.texgen import Hunyuan3DPaintPipeline
            from hy3dgen.text2image import HunyuanDiTPipeline
        except Exception as exc:  # pragma: no cover - depends on local runtime
            raise GenerationUnavailableError(
                "Hunyuan3D dependencies are not importable in the current environment"
            ) from exc

        device = self._device(torch)
        if device != "cuda":
            raise GenerationUnavailableError(
                "Hunyuan3D generation is configured for CUDA workloads; no CUDA device is available"
            )
        return {
            "torch": torch,
            "Image": Image,
            "BackgroundRemover": BackgroundRemover,
            "Hunyuan3DDiTFlowMatchingPipeline": Hunyuan3DDiTFlowMatchingPipeline,
            "Hunyuan3DPaintPipeline": Hunyuan3DPaintPipeline,
            "HunyuanDiTPipeline": HunyuanDiTPipeline,
        }

    def _device(self, torch_module) -> str:
        if self._config.device != "auto":
            return self._config.device
        return "cuda" if torch_module.cuda.is_available() else "cpu"
