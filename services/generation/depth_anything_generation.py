"""Depth Anything 3 powered gsplat generation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from typing import Sequence

from services.assets.file_ingest import AssetIngestService
from services.scene_core.project_manifest import AssetRecord, ProjectManifest
from services.storage.local_fs import ProjectRepository


class MissingDepthAnythingDependencyError(ImportError):
    """Raised when the optional Depth Anything 3 stack is unavailable."""


class DepthAnythingGenerationError(RuntimeError):
    """Raised when image-to-gsplat generation fails."""


@dataclass(frozen=True)
class GeneratedGsplatProject:
    """Summary of a newly generated gsplat project."""

    project_id: str
    project_name: str
    asset: AssetRecord
    input_image_count: int


class DepthAnythingGenerationService:
    """Create project room gsplats from image sets using Depth Anything 3."""

    def __init__(
        self,
        repo: ProjectRepository,
        *,
        model_name: str,
        device: str = "auto",
        process_res: int = 504,
    ) -> None:
        self.repo = repo
        self.model_name = model_name
        self.device = device
        self.process_res = process_res
        self.ingest = AssetIngestService(repo)
        self._torch = None
        self._model = None
        self._depth_anything_cls = None
        self._save_gaussian_ply = None
        self._resolved_model_source: str | None = None

    def create_project_from_images(self, image_paths: Sequence[Path]) -> GeneratedGsplatProject:
        """Generate a room gsplat from input images and register it in a fresh project."""
        normalized_paths = self._normalize_image_paths(image_paths)
        manifest = ProjectManifest(
            name=self._build_project_name(),
            description=f"Generated from {len(normalized_paths)} input image(s) with Depth Anything 3.",
        )
        self.repo.create_project(manifest)

        try:
            copied_inputs = self._copy_inputs(manifest.id, normalized_paths)
            generated_ply = self._generate_gsplat(copied_inputs, manifest.id)
            asset = self.ingest.ingest_room_gsplat(
                project_id=manifest.id,
                name="Generated GSplat",
                source_path=generated_ply,
            )
            asset = self._annotate_generated_asset(
                project_id=manifest.id,
                asset_id=asset.id,
                input_image_count=len(copied_inputs),
            )
            return GeneratedGsplatProject(
                project_id=manifest.id,
                project_name=manifest.name,
                asset=asset,
                input_image_count=len(copied_inputs),
            )
        except Exception:
            self._cleanup_failed_project(manifest.id)
            raise

    def _normalize_image_paths(self, image_paths: Sequence[Path]) -> list[Path]:
        allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
        normalized_paths = [Path(path) for path in image_paths]
        if not normalized_paths:
            raise DepthAnythingGenerationError("Upload at least one input image to create a gsplat.")

        for path in normalized_paths:
            suffix = path.suffix.lower()
            if suffix not in allowed_suffixes:
                raise DepthAnythingGenerationError(
                    "Supported image types are .jpg, .jpeg, .png, .webp, .bmp, .tif, and .tiff."
                )
            if not path.exists():
                raise DepthAnythingGenerationError(f"Input image is missing on disk: {path}")
        return normalized_paths

    def _copy_inputs(self, project_id: str, image_paths: Sequence[Path]) -> list[Path]:
        target_dir = self.repo.project_dir(project_id) / "inputs" / "da3"
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_paths: list[Path] = []
        for index, source_path in enumerate(image_paths):
            safe_name = source_path.name.replace(" ", "_")
            destination = target_dir / f"{index:04d}_{safe_name}"
            shutil.copy2(source_path, destination)
            copied_paths.append(destination)
        return copied_paths

    def _generate_gsplat(self, image_paths: Sequence[Path], project_id: str) -> Path:
        torch = self._get_torch()
        model = self._get_model()
        save_gaussian_ply = self._get_save_gaussian_ply()
        export_path = self.repo.project_dir(project_id) / "generation" / "da3" / "gs_ply" / "0000.ply"

        try:
            prediction = model.inference(
                image=[str(path) for path in image_paths],
                infer_gs=True,
                process_res=self.process_res,
            )
        except MissingDepthAnythingDependencyError:
            raise
        except Exception as exc:
            raise DepthAnythingGenerationError(
                f"Depth Anything 3 inference failed while creating the gsplat: {exc}"
            ) from exc

        gaussians = getattr(prediction, "gaussians", None)
        depth = getattr(prediction, "depth", None)
        if gaussians is None or depth is None:
            raise DepthAnythingGenerationError(
                "Depth Anything 3 did not return gaussian splat data for the uploaded images."
            )

        export_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            save_gaussian_ply(
                gaussians=gaussians,
                save_path=str(export_path),
                ctx_depth=torch.from_numpy(depth).unsqueeze(-1).to(gaussians.means),
                shift_and_scale=False,
                save_sh_dc_only=True,
                gs_views_interval=1,
                inv_opacity=True,
                prune_by_depth_percent=0.9,
                prune_border_gs=True,
                match_3dgs_mcmc_dev=False,
            )
        except Exception as exc:
            raise DepthAnythingGenerationError(
                f"Depth Anything 3 produced gaussians, but exporting them to PLY failed: {exc}"
            ) from exc

        return export_path

    def _annotate_generated_asset(
        self,
        *,
        project_id: str,
        asset_id: str,
        input_image_count: int,
    ) -> AssetRecord:
        manifest = self.repo.get_project(project_id)
        asset = next(asset for asset in manifest.assets if asset.id == asset_id)
        manifest = self.repo.update_asset(
            project_id,
            asset_id,
            {
                "metadata": {
                    **asset.metadata,
                    "generated_by": "depth_anything_3",
                    "generation_model": self._resolved_model_source or self.model_name,
                    "input_image_count": input_image_count,
                }
            },
        )
        return next(asset for asset in manifest.assets if asset.id == asset_id)

    @staticmethod
    def _build_project_name() -> str:
        timestamp = datetime.now().strftime("%b %d %H:%M")
        return f"Generated Scene {timestamp}"

    def _get_torch(self):
        if self._torch is None:
            self._load_da3_components()
        return self._torch

    def _get_model(self):
        if self._model is None:
            self._load_da3_components()
            device = self._resolve_device(self._torch)
            model_source = self._resolve_model_source()
            try:
                self._model = self._depth_anything_cls.from_pretrained(model_source).to(device)
            except Exception as exc:
                try:
                    # Support preset names such as `da3-giant` in addition to local paths or HF ids.
                    self._model = self._depth_anything_cls(model_name=model_source).to(device)
                except Exception as preset_exc:
                    raise DepthAnythingGenerationError(
                        "Unable to load the configured Depth Anything 3 model "
                        f"`{model_source}`: {preset_exc}"
                    ) from exc
            self._model.eval()
        return self._model

    def _resolve_model_source(self) -> str:
        """Return the resolved DA3 model source used for loading."""
        if self._resolved_model_source is None:
            self._resolved_model_source = self.model_name
        return self._resolved_model_source

    def _get_save_gaussian_ply(self):
        if self._save_gaussian_ply is None:
            self._load_da3_components()
        return self._save_gaussian_ply

    def _load_da3_components(self) -> None:
        if self._torch is not None and self._save_gaussian_ply is not None:
            return

        try:
            import torch
            from depth_anything_3.api import DepthAnything3
            from depth_anything_3.utils.gsply_helpers import save_gaussian_ply
        except ImportError as exc:
            raise MissingDepthAnythingDependencyError(
                "Depth Anything 3 generation requires the optional DA3 dependencies. "
                "Install the packages from `requirements-da3.txt` first."
            ) from exc

        self._torch = torch
        self._depth_anything_cls = DepthAnything3
        self._save_gaussian_ply = save_gaussian_ply

    def _resolve_device(self, torch_module) -> str:
        configured = self.device.strip().lower()
        if configured and configured != "auto":
            return configured
        if torch_module.cuda.is_available():
            return "cuda"
        if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _cleanup_failed_project(self, project_id: str) -> None:
        try:
            self.repo.delete_project(project_id)
        except Exception:
            return
