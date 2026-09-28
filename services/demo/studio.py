"""A small architectural splat scene and editable furniture, with no model downloads."""
from __future__ import annotations

import numpy as np
import trimesh
from plyfile import PlyData, PlyElement

from services.scene_core.project_manifest import (
    AssetRecord, CameraKeyframe, ObjectInstance, ProjectManifest, TrajectoryRecord, Transform,
)
from services.storage.local_fs import ProjectRepository


def create_demo(repo: ProjectRepository) -> ProjectManifest:
    """Create a fresh sample; never overwrite someone's edited demo."""
    project = repo.create_project(ProjectManifest(
        name="The daylight studio",
        description="Procedural sample • an editable room study, not an AI reconstruction.",
    ))
    try:
        root = repo.project_dir(project.id) / "assets"
        room_path = root / "daylight-studio.ply"
        _room(room_path)
        room = AssetRecord(name="Daylight studio shell", kind="gsplat_ply", role="room",
                           source_uri=str(room_path.relative_to(repo.root)),
                           metadata={"generated_by": "deco_demo", "preserve_origin": True})
        project.assets.append(room)
        project.scene.room_asset_id = room.id
        for name, meshes, position in _furniture():
            path = root / (name.lower().replace(" ", "-") + ".glb")
            trimesh.Scene(meshes).export(str(path))
            asset = AssetRecord(name=name, kind="glb", role="object",
                                source_uri=str(path.relative_to(repo.root)))
            project.assets.append(asset)
            project.scene.objects.append(ObjectInstance(
                name=name, asset_id=asset.id, transform=Transform(position=position)))
        project.trajectories.append(TrajectoryRecord(
            name="Studio reveal", duration_seconds=4,
            keyframes=[CameraKeyframe(time_seconds=t, position=p, target=[0, .3, .9],
                                      up_direction=[0, 0, 1], fov_degrees=55)
                       for t, p in [(0, [5.8, -7.8, 5.2]), (2, [3.7, -7.4, 3.8]),
                                    (4, [1.2, -6.5, 3.1])]],
        ))
        return repo.update_project(project)
    except Exception:
        repo.delete_project(project.id)
        raise


def _room(path):
    rng = np.random.default_rng(23)
    points, colors, scales = [], [], []

    def plane(axis, fixed, a_range, b_range, color, wood=False):
        axes = [i for i in range(3) if i != axis]
        a, b = np.meshgrid(np.arange(*a_range, .045), np.arange(*b_range, .045))
        xyz = np.zeros((a.size, 3), dtype=np.float32)
        xyz[:, axis] = fixed
        xyz[:, axes[0]], xyz[:, axes[1]] = a.ravel(), b.ravel()
        rgb = np.tile(np.array(color) / 255, (len(xyz), 1))
        variation = rng.normal(0, .008, (len(xyz), 1))
        if wood:
            variation += .025 * np.sin(xyz[:, 0:1] * 33)
            seams = np.remainder(xyz[:, 0], .28) < .027
            variation[seams] -= .08
        rgb = np.clip(rgb + variation, 0, 1)
        sigma = np.full((len(xyz), 3), .034)
        sigma[:, axis] = .008
        points.append(xyz); colors.append(rgb); scales.append(sigma)

    plane(2, 0, (-3, 3.01), (-2.8, 2.81), [166, 132, 94], True)
    plane(1, 2.8, (-3, 3.01), (0, 3.05), [225, 218, 201])
    # Left wall frames a large pale blue window; front and right remain open.
    plane(0, -3, (-2.8, 2.81), (0, .8), [212, 209, 194])
    plane(0, -3, (-2.8, 2.81), (2.5, 3.05), [212, 209, 194])
    plane(0, -3, (-2.8, -1.8), (.8, 2.51), [212, 209, 194])
    plane(0, -3, (1.6, 2.81), (.8, 2.51), [212, 209, 194])
    plane(0, -3.02, (-1.8, 1.61), (.8, 2.51), [164, 199, 208])
    xyz, rgb, sigma = np.concatenate(points), np.concatenate(colors), np.concatenate(scales)
    names = ['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity',
             'scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3']
    vertices = np.zeros(len(xyz), dtype=[(n, '<f4') for n in names])
    for i, n in enumerate(['x','y','z']): vertices[n] = xyz[:, i]
    for i in range(3):
        vertices[f'f_dc_{i}'] = (rgb[:, i] - .5) / .28209479177387814
        vertices[f'scale_{i}'] = np.log(sigma[:, i])
    vertices['opacity'] = 5
    vertices['rot_0'] = 1
    PlyData([PlyElement.describe(vertices, 'vertex')], text=False).write(path)


def _box(size, at, color):
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(at)
    mesh.visual.vertex_colors = color
    return mesh


def _cylinder(radius, height, at, color):
    mesh = trimesh.creation.cylinder(radius, height, sections=40)
    mesh.apply_translation(at)
    mesh.visual.vertex_colors = color
    return mesh


def _furniture():
    cream, fabric, wood, dark = [224, 214, 192, 255], [173, 183, 155, 255], [115, 72, 44, 255], [47, 51, 45, 255]
    sofa = [_box([2.6, .9, .22], [0, 0, .32], wood),
            _box([2.6, .2, .7], [0, .4, .72], fabric)]
    for x in [-.85, 0, .85]:
        sofa.append(_box([.81, .76, .2], [x, -.03, .52], cream))
        sofa.append(_box([.79, .15, .44], [x, .27, .86], cream))
    for x in [-1.28, 1.28]: sofa.append(_box([.16, .92, .42], [x, 0, .62], fabric))
    for x in [-1.1, 1.1]:
        for y in [-.3, .3]: sofa.append(_cylinder(.045, .22, [x, y, .11], dark))
    yield "Linen sofa", sofa, [0, 1.6, 0]
    table = [_cylinder(.72, .09, [0, 0, .53], wood), _cylinder(.26, .48, [0, 0, .24], wood),
             _box([.28, .22, .035], [.15, 0, .60], cream),
             _cylinder(.09, .16, [-.2, .1, .65], [190, 123, 88, 255])]
    yield "Oak coffee table", table, [0, -.1, 0]
    yield "Woven rug", [_box([3.4, 2.4, .025], [0, 0, .018], [202, 190, 165, 255])], [0, .15, 0]
    lamp = [_cylinder(.24, .045, [0, 0, .025], dark), _cylinder(.025, 1.7, [0, 0, .86], dark),
            _cylinder(.33, .38, [0, 0, 1.7], cream)]
    yield "Reading lamp", lamp, [2, 1.7, 0]
    plant = [_cylinder(.24, .42, [0, 0, .21], [176, 101, 73, 255]),
             _cylinder(.022, .95, [0, 0, .88], wood)]
    for x, y, z in [(-.22, 0, 1.05), (.19, .12, 1.3), (0, -.13, 1.55), (.04, .05, 1.75)]:
        leaf = trimesh.creation.icosphere(subdivisions=2, radius=1)
        leaf.apply_scale([.31, .26, .36]); leaf.apply_translation([x, y, z])
        leaf.visual.vertex_colors = [68, 103 + int(z * 10), 65, 255]
        plant.append(leaf)
    yield "Ficus in terracotta", plant, [-2.25, 1.85, 0]
    art = [_box([1.45, .06, 1.05], [0, 0, 0], wood),
           _box([1.35, .025, .95], [0, -.045, 0], cream),
           _box([.55, .02, .67], [-.24, -.065, -.06], [177, 108, 77, 255]),
           _box([.44, .02, .45], [.29, -.07, .19], [80, 108, 98, 255])]
    yield "Abstract wall study", art, [.2, 2.73, 2]
