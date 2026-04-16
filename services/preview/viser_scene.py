"""Utilities for loading gsplat PLY files into a viser scene."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - environment-dependent
    np = None

try:
    from plyfile import PlyData
except ImportError:  # pragma: no cover - environment-dependent
    PlyData = None

try:
    from viser import transforms as tf
except ImportError:  # pragma: no cover - environment-dependent
    tf = None


class InvalidGaussianSplatError(ValueError):
    """Raised when a PLY file is not compatible with gaussian splat viewing."""


@dataclass
class GaussianSplatData:
    """Typed arrays ready for viser.SceneApi.add_gaussian_splats()."""

    centers: np.ndarray
    rgbs: np.ndarray
    opacities: np.ndarray
    covariances: np.ndarray


def load_gaussian_splat_ply(path: Path, *, center: bool = True) -> GaussianSplatData:
    """Load a gaussian splat PLY into arrays expected by viser."""
    if np is None or PlyData is None or tf is None:
        raise InvalidGaussianSplatError(
            "Gaussian splat viewing requires `numpy`, `plyfile`, and `viser` to be installed"
        )

    ply_data = PlyData.read(path)
    vertex = ply_data["vertex"]
    required = {
        "x",
        "y",
        "z",
        "scale_0",
        "scale_1",
        "scale_2",
        "rot_0",
        "rot_1",
        "rot_2",
        "rot_3",
        "f_dc_0",
        "f_dc_1",
        "f_dc_2",
        "opacity",
    }
    available = {prop.name for prop in vertex.properties}
    missing = sorted(required - available)
    if missing:
        raise InvalidGaussianSplatError(
            f"PLY is missing gaussian splat fields: {', '.join(missing)}"
        )

    sh_c0 = 0.28209479177387814
    centers = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=-1).astype(np.float32)
    scales = np.exp(
        np.stack([vertex["scale_0"], vertex["scale_1"], vertex["scale_2"]], axis=-1)
    ).astype(np.float32)
    wxyz = np.stack(
        [vertex["rot_0"], vertex["rot_1"], vertex["rot_2"], vertex["rot_3"]],
        axis=-1,
    ).astype(np.float32)
    rgbs = np.clip(
        0.5 + sh_c0 * np.stack([vertex["f_dc_0"], vertex["f_dc_1"], vertex["f_dc_2"]], axis=-1),
        0.0,
        1.0,
    ).astype(np.float32)
    opacities = (
        1.0 / (1.0 + np.exp(-np.asarray(vertex["opacity"], dtype=np.float32)[:, None]))
    ).astype(np.float32)

    if center:
        centers = centers - np.mean(centers, axis=0, keepdims=True)

    rotations = tf.SO3(wxyz).as_matrix().astype(np.float32)
    covariances = np.einsum(
        "nij,njk,nlk->nil",
        rotations,
        np.eye(3, dtype=np.float32)[None, :, :] * scales[:, None, :] ** 2,
        rotations,
    ).astype(np.float32)

    return GaussianSplatData(
        centers=centers,
        rgbs=rgbs,
        opacities=opacities,
        covariances=covariances,
    )
