"""Trajectory interpolation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from viser import transforms as tf

from services.scene_core.project_manifest import CameraKeyframe, TrajectoryRecord


@dataclass
class CameraSample:
    """Interpolated camera state for a single frame."""

    time_seconds: float
    position: np.ndarray
    target: np.ndarray
    up_direction: np.ndarray
    fov_radians: float
    wxyz: np.ndarray


def sample_trajectory(trajectory: TrajectoryRecord, fps: int) -> list[CameraSample]:
    """Sample a stored trajectory into per-frame camera states."""
    keyframes = sorted(trajectory.keyframes, key=lambda item: item.time_seconds)
    if len(keyframes) < 2:
        raise ValueError("At least two keyframes are required to sample a trajectory")

    duration = max(trajectory.duration_seconds, keyframes[-1].time_seconds)
    frame_count = max(int(round(duration * fps)), 2)
    sample_times = np.linspace(0.0, duration, frame_count, endpoint=True)

    positions = np.array([frame.position for frame in keyframes], dtype=np.float64)
    targets = np.array(
        [frame.target if frame.target is not None else frame.position for frame in keyframes],
        dtype=np.float64,
    )
    ups = np.array(
        [
            frame.up_direction if frame.up_direction is not None else [0.0, 0.0, 1.0]
            for frame in keyframes
        ],
        dtype=np.float64,
    )
    fovs = np.array(
        [
            np.deg2rad(frame.fov_degrees if frame.fov_degrees is not None else 75.0)
            for frame in keyframes
        ],
        dtype=np.float64,
    )
    times = np.array([frame.time_seconds for frame in keyframes], dtype=np.float64)

    samples: list[CameraSample] = []
    for sample_time in sample_times:
        if trajectory.spline == "catmull_rom":
            position = _catmull_rom_component(times, positions, sample_time)
            target = _catmull_rom_component(times, targets, sample_time)
            up = _catmull_rom_component(times, ups, sample_time)
            fov = float(_catmull_rom_component(times, fovs[:, None], sample_time)[0])
        else:
            position = _linear_component(times, positions, sample_time)
            target = _linear_component(times, targets, sample_time)
            up = _linear_component(times, ups, sample_time)
            fov = float(_linear_component(times, fovs[:, None], sample_time)[0])

        up = _normalize(up)
        wxyz = camera_wxyz_from_look_at(position, target, up)
        samples.append(
            CameraSample(
                time_seconds=float(sample_time),
                position=position.astype(np.float64),
                target=target.astype(np.float64),
                up_direction=up.astype(np.float64),
                fov_radians=fov,
                wxyz=wxyz.astype(np.float64),
            )
        )
    return samples


def camera_wxyz_from_look_at(
    position: np.ndarray,
    target: np.ndarray,
    up_direction: np.ndarray,
) -> np.ndarray:
    """Construct a camera quaternion from look-at camera vectors."""
    look = _normalize(np.asarray(target, dtype=np.float64) - np.asarray(position, dtype=np.float64))
    up = _normalize(np.asarray(up_direction, dtype=np.float64))
    right = _normalize(np.cross(look, up))
    corrected_up = _normalize(np.cross(right, look))
    rotation = np.stack([right, -corrected_up, look], axis=1)
    return tf.SO3.from_matrix(rotation).wxyz.astype(np.float64)


def keyframe_from_camera_state(
    *,
    time_seconds: float,
    position: np.ndarray,
    target: np.ndarray,
    up_direction: np.ndarray,
    fov_radians: float,
) -> CameraKeyframe:
    """Convert a live camera state into a stored keyframe."""
    return CameraKeyframe(
        time_seconds=float(time_seconds),
        position=np.asarray(position, dtype=float).tolist(),
        target=np.asarray(target, dtype=float).tolist(),
        up_direction=np.asarray(up_direction, dtype=float).tolist(),
        fov_degrees=float(np.rad2deg(fov_radians)),
    )


def _linear_component(times: np.ndarray, values: np.ndarray, sample_time: float) -> np.ndarray:
    indices = np.searchsorted(times, sample_time, side="right") - 1
    i1 = int(np.clip(indices, 0, len(times) - 1))
    i2 = int(np.clip(i1 + 1, 0, len(times) - 1))
    if i1 == i2 or times[i2] == times[i1]:
        return values[i1]
    alpha = (sample_time - times[i1]) / (times[i2] - times[i1])
    return (1.0 - alpha) * values[i1] + alpha * values[i2]


def _catmull_rom_component(times: np.ndarray, values: np.ndarray, sample_time: float) -> np.ndarray:
    idx = np.searchsorted(times, sample_time, side="right") - 1
    i1 = int(np.clip(idx, 0, len(times) - 2))
    i0 = max(i1 - 1, 0)
    i2 = min(i1 + 1, len(times) - 1)
    i3 = min(i2 + 1, len(times) - 1)

    t1 = times[i1]
    t2 = times[i2]
    if t2 == t1:
        return values[i1]
    u = float((sample_time - t1) / (t2 - t1))

    p0 = values[i0]
    p1 = values[i1]
    p2 = values[i2]
    p3 = values[i3]
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * u
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * (u**2)
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * (u**3)
    )


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm < 1e-8:
        return np.array([0.0, 0.0, 1.0], dtype=np.float64)
    return vector / norm
