#!/usr/bin/env python3
"""Build a reusable, cinematic asset showcase studio in Blender.

Run from Blender's Scripting workspace, or from a shell:

    blender --background --python build_showcase.py -- \
        --asset /path/to/asset.glb --output /path/to/showcase.blend

The generator is intentionally self-contained and does not require add-ons.
It targets Blender 3.6 LTS and Blender 4.x, using guarded compatibility paths
for Eevee and OBJ import operator changes.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


STUDIO_VERSION = "1.0.0"
TURN_START = 1
TURN_END = 240
ORBIT_START = 241
ORBIT_END = 480
FLY_START = 481
FLY_END = 660


def parse_args() -> argparse.Namespace:
    """Parse only arguments after Blender's conventional `--` separator."""
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, help="Optional GLB, GLTF, OBJ, or FBX asset")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "asset_showcase_studio.blend",
        help="Destination .blend file",
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "eevee", "cycles"),
        default="auto",
        help="Render engine; auto prefers Eevee for portable previews",
    )
    parser.add_argument("--resolution-x", type=int, default=1920)
    parser.add_argument("--resolution-y", type=int, default=1080)
    parser.add_argument("--resolution-percent", type=int, default=100)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--target-height", type=float, default=2.4)
    parser.add_argument(
        "--keep-imported-lights-cameras",
        action="store_true",
        help="Keep cameras and lights embedded in the imported asset (off by default)",
    )
    parser.add_argument(
        "--no-separate-fly-scene",
        action="store_true",
        help="Keep only the master scene instead of creating a fly-through shot scene",
    )
    parser.add_argument("--render-still", action="store_true", help="Render frame 40 after building")
    parser.add_argument(
        "--render-shot",
        choices=("turntable", "orbit", "fly"),
        help="Render an animation after building (can take a long time)",
    )
    parser.add_argument("--no-save", action="store_true", help="Build without saving the .blend")
    return parser.parse_args(argv)


def set_if_present(owner: object, attr: str, value: object) -> bool:
    if hasattr(owner, attr):
        try:
            setattr(owner, attr, value)
            return True
        except (AttributeError, TypeError, ValueError):
            pass
    return False


def clean_file() -> None:
    # Keep the currently active scene so a GUI run does not invalidate its
    # context, but remove generated/extra scenes and every old object directly.
    # Direct datablock removal also catches hidden objects that select_all misses.
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    active_scene = bpy.context.scene
    for scene in list(bpy.data.scenes):
        if scene != active_scene:
            bpy.data.scenes.remove(scene)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    active_scene.world = None
    for world in list(bpy.data.worlds):
        bpy.data.worlds.remove(world)
    for marker in list(active_scene.timeline_markers):
        active_scene.timeline_markers.remove(marker)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def material_principled(
    name: str,
    base: Sequence[float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.45,
    emission: Sequence[float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = tuple(base)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = tuple(base)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission is not None:
            emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            strength_input = bsdf.inputs.get("Emission Strength")
            if emission_input:
                emission_input.default_value = tuple(emission)
            if strength_input:
                strength_input.default_value = emission_strength
    return mat


def add_mesh_primitive(
    operator,
    name: str,
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    **kwargs,
) -> bpy.types.Object:
    operator(**kwargs)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, collection)
    if material:
        obj.data.materials.append(material)
    return obj


def add_empty(name: str, collection: bpy.types.Collection, location=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "CIRCLE"
    obj.empty_display_size = 0.4
    obj.location = location
    collection.objects.link(obj)
    return obj


def parent_keep_transform(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    """Parent an object without changing its evaluated world-space transform."""
    world_matrix = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world_matrix


def look_at(obj: bpy.types.Object, target: bpy.types.Object, track_axis: str = "TRACK_NEGATIVE_Z") -> None:
    constraint = obj.constraints.new(type="TRACK_TO")
    constraint.name = "Aim at showcase target"
    constraint.target = target
    constraint.track_axis = track_axis
    constraint.up_axis = "UP_Y"


def keyframe_linear(obj: bpy.types.Object, data_path: str, frames: Iterable[int]) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    for fcurve in action_fcurves(action):
        if fcurve.data_path == data_path:
            for point in fcurve.keyframe_points:
                if round(point.co.x) in frames:
                    point.interpolation = "LINEAR"


def action_fcurves(action: bpy.types.Action) -> list[object]:
    """Return F-curves from legacy or Blender 4.4+ layered actions."""
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        try:
            return list(legacy)
        except (AttributeError, RuntimeError, TypeError):
            pass
    curves: list[object] = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for channelbag in getattr(strip, "channelbags", []):
                curves.extend(list(getattr(channelbag, "fcurves", [])))
    return curves


def build_cyclorama(collection: bpy.types.Collection, material: bpy.types.Material) -> bpy.types.Object:
    """Build a wide floor-to-wall cyclorama with a true quarter-round sweep."""
    half_width = 9.0
    profile: list[tuple[float, float]] = [(-10.0, 0.0), (3.0, 0.0)]
    for step in range(1, 13):
        theta = (math.pi * 0.5) * step / 12.0
        profile.append((3.0 + 2.0 * math.sin(theta), 2.0 - 2.0 * math.cos(theta)))
    profile.append((5.0, 8.0))

    vertices = []
    for x in (-half_width, half_width):
        vertices.extend((x, y, z) for y, z in profile)
    count = len(profile)
    faces = []
    for index in range(count - 1):
        # Winding points toward the studio interior: +Z across the floor and
        # -Y on the rear wall. Solidify therefore grows away from the set.
        faces.append((index, count + index, count + index + 1, index + 1))
    mesh = bpy.data.meshes.new("Cyclorama_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("SET_Cyclorama", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    solidify = obj.modifiers.new("Architectural thickness", "SOLIDIFY")
    solidify.thickness = 0.12
    solidify.offset = -1.0
    bevel = obj.modifiers.new("Soft architectural edges", "BEVEL")
    bevel.width = 0.06
    bevel.segments = 3
    return obj


def build_set(
    set_collection: bpy.types.Collection,
    practical_collection: bpy.types.Collection,
    mats: dict[str, bpy.types.Material],
) -> tuple[bpy.types.Object, bpy.types.Object]:
    build_cyclorama(set_collection, mats["cyclorama"])

    # Layered pedestal: a dark plinth, brushed turntable, and emissive reveal.
    add_mesh_primitive(
        bpy.ops.mesh.primitive_cylinder_add,
        "SET_PedestalBase",
        set_collection,
        mats["charcoal"],
        vertices=96,
        radius=2.25,
        depth=0.72,
        location=(0, 0, 0.36),
    )
    add_mesh_primitive(
        bpy.ops.mesh.primitive_cylinder_add,
        "SET_PedestalInset",
        set_collection,
        mats["black"],
        vertices=96,
        radius=1.98,
        depth=0.22,
        location=(0, 0, 0.78),
    )
    turntable = add_mesh_primitive(
        bpy.ops.mesh.primitive_cylinder_add,
        "RIG_Turntable",
        set_collection,
        mats["brushed"],
        vertices=128,
        radius=1.88,
        depth=0.18,
        location=(0, 0, 0.94),
    )
    bevel = turntable.modifiers.new("Turntable edge", "BEVEL")
    bevel.width = 0.05
    bevel.segments = 3

    ring = add_mesh_primitive(
        bpy.ops.mesh.primitive_torus_add,
        "PRACTICAL_PedestalRing",
        practical_collection,
        mats["cyan_emission"],
        major_radius=1.985,
        minor_radius=0.035,
        major_segments=96,
        minor_segments=12,
        location=(0, 0, 0.89),
    )
    ring.rotation_euler.x = 0.0

    # Side monoliths frame reflections without crowding the product.
    for x, color_mat in ((-6.4, mats["cyan_emission"]), (6.4, mats["magenta_emission"])):
        add_mesh_primitive(
            bpy.ops.mesh.primitive_cube_add,
            f"SET_Monolith_{'L' if x < 0 else 'R'}",
            set_collection,
            mats["black"],
            location=(x, 3.85, 2.55),
            scale=(0.36, 0.32, 2.55),
        )
        strip = add_mesh_primitive(
            bpy.ops.mesh.primitive_cube_add,
            f"PRACTICAL_Strip_{'Cyan' if x < 0 else 'Magenta'}",
            practical_collection,
            color_mat,
            location=(x, 3.48, 2.55),
            scale=(0.07, 0.035, 2.15),
        )
        bevel_strip = strip.modifiers.new("Glow strip edge", "BEVEL")
        bevel_strip.width = 0.06
        bevel_strip.segments = 4

    # Ceiling softbox visible in glossy reflections, outside the hero framing.
    add_mesh_primitive(
        bpy.ops.mesh.primitive_cube_add,
        "PRACTICAL_CeilingSoftbox",
        practical_collection,
        mats["white_emission"],
        location=(0, 0.8, 6.5),
        scale=(2.6, 1.1, 0.035),
    )
    target = add_empty("RIG_LookTarget", set_collection, (0, 0, 2.15))
    backdrop_target = add_empty("RIG_BackdropTarget", set_collection, (0, 4.9, 3.0))
    return turntable, target, backdrop_target


def add_area_light(
    name: str,
    collection: bpy.types.Collection,
    location: Sequence[float],
    color: Sequence[float],
    energy: float,
    size: float,
    target: bpy.types.Object,
    shape: str = "DISK",
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.color = tuple(color)
    data.energy = energy
    data.shape = shape
    data.size = size
    if shape == "RECTANGLE":
        data.size_y = size * 0.55
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    look_at(obj, target)
    return obj


def build_lighting(
    collection: bpy.types.Collection,
    target: bpy.types.Object,
    backdrop_target: bpy.types.Object,
) -> None:
    # The signature split: cool cyan key from camera-left, hot magenta rim right/rear.
    add_area_light("LIGHT_Key_Cyan", collection, (-5.8, -4.6, 5.6), (0.02, 0.78, 1.0), 1050, 4.0, target)
    add_area_light("LIGHT_Rim_Magenta", collection, (5.6, 1.0, 4.6), (1.0, 0.015, 0.35), 1300, 3.5, target)
    add_area_light("LIGHT_Fill_Soft", collection, (0.0, -1.8, 7.0), (0.78, 0.86, 1.0), 700, 5.0, target, "RECTANGLE")
    add_area_light(
        "LIGHT_Backdrop_Wash",
        collection,
        (0.0, 3.5, 2.2),
        (0.18, 0.12, 0.45),
        500,
        3.0,
        backdrop_target,
    )


def imported_objects_since(before: set[str]) -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.objects if obj.name not in before]


def remove_imported_lights_cameras(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    """Remove embedded shot-control objects while preserving asset geometry."""
    removed = [obj for obj in objects if obj.type in {"LIGHT", "CAMERA"}]
    kept = [obj for obj in objects if obj.type not in {"LIGHT", "CAMERA"}]
    removed_names = {obj.name for obj in removed}

    # An exporter can technically use a camera/light as a hierarchy node. Keep
    # any renderable descendants stable before deleting those control objects.
    for obj in kept:
        parent = obj.parent
        if parent is None or parent.name not in removed_names:
            continue
        world_matrix = obj.matrix_world.copy()
        while parent is not None and parent.name in removed_names:
            parent = parent.parent
        obj.parent = parent
        obj.matrix_world = world_matrix

    for obj in removed:
        obj_type = obj.type
        obj_name = obj.name
        data = obj.data
        print(f"[showcase] Removing imported {obj_type.lower()}: {obj_name}")
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            if obj_type == "LIGHT":
                bpy.data.lights.remove(data)
            else:
                bpy.data.cameras.remove(data)
    return kept


def import_asset(path: Path) -> list[bpy.types.Object]:
    if not path.exists():
        raise FileNotFoundError(f"Asset does not exist: {path}")
    before = {obj.name for obj in bpy.data.objects}
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        elif hasattr(bpy.ops.import_scene, "obj"):
            bpy.ops.import_scene.obj(filepath=str(path))
        else:
            raise RuntimeError("This Blender build has no OBJ import operator")
    else:
        raise ValueError(f"Unsupported asset extension {suffix}; use GLB, GLTF, OBJ, or FBX")
    imported = imported_objects_since(before)
    if not imported:
        raise RuntimeError(f"Import completed without creating objects: {path}")
    return imported


def world_bbox(objects: Iterable[bpy.types.Object]) -> tuple[Vector, Vector]:
    """Bounds of render-enabled geometry evaluated at the current scene frame.

    evaluated_get includes modifiers, armature deformation, and the current
    Geometry Nodes result where Blender exposes a conventional object bound box.
    It intentionally does not scan an animation, simulation cache, or every
    possible procedural state.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.hide_render or obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            continue
        try:
            evaluated = obj.evaluated_get(depsgraph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            # A few third-party/custom object types cannot provide evaluated
            # bounds. Their original bound remains preferable to dropping them.
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("Asset contains no renderable geometry with a bounding box")
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def normalize_asset(
    objects: list[bpy.types.Object],
    collection: bpy.types.Collection,
    turntable: bpy.types.Object,
    target_height: float,
) -> bpy.types.Object:
    # Move only imported objects out of transient importer collections.
    for obj in objects:
        move_to_collection(obj, collection)
    root = add_empty("ASSET_Root", collection)
    top_level = [obj for obj in objects if obj.parent not in objects]
    for obj in top_level:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix
    bpy.context.view_layer.update()

    low, high = world_bbox(objects)
    dimensions = high - low
    largest = max(dimensions.x, dimensions.y, dimensions.z)
    if largest <= 1e-6:
        raise RuntimeError("Asset bounds are effectively zero-sized")
    desired = max(0.25, target_height)
    scale = desired / max(dimensions.z, largest * 0.65)
    root.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    low, high = world_bbox(objects)
    center = (low + high) * 0.5
    platform_z = 1.04
    root.location += Vector((-center.x, -center.y, platform_z - low.z))
    bpy.context.view_layer.update()
    parent_keep_transform(root, turntable)
    root["source_asset"] = str(objects[0].get("source_asset", "imported"))
    return root


def build_placeholder(
    collection: bpy.types.Collection,
    turntable: bpy.types.Object,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    root = add_empty("ASSET_Root", collection, (0, 0, 1.04))
    parent_keep_transform(root, turntable)
    root["source_asset"] = "procedural showcase placeholder"

    body = add_mesh_primitive(
        bpy.ops.mesh.primitive_cube_add,
        "ASSET_PlaceholderBody",
        collection,
        mats["placeholder"],
        location=(0, 0, 2.28),
        scale=(0.95, 0.72, 1.18),
    )
    parent_keep_transform(body, root)
    bevel = body.modifiers.new("Product bevel", "BEVEL")
    bevel.width = 0.19
    bevel.segments = 5

    for z, radius in ((1.22, 0.88), (3.34, 0.72)):
        collar = add_mesh_primitive(
            bpy.ops.mesh.primitive_torus_add,
            f"ASSET_Collar_{z:.2f}",
            collection,
            mats["brushed"],
            major_radius=radius,
            minor_radius=0.08,
            major_segments=64,
            minor_segments=12,
            location=(0, 0, z),
            rotation=(0, 0, 0),
        )
        parent_keep_transform(collar, root)
    lens = add_mesh_primitive(
        bpy.ops.mesh.primitive_uv_sphere_add,
        "ASSET_LuminousCore",
        collection,
        mats["cyan_emission"],
        segments=64,
        ring_count=32,
        location=(0, -0.72, 2.33),
        scale=(0.48, 0.18, 0.48),
    )
    parent_keep_transform(lens, root)
    return root


def animate_turntable(turntable: bpy.types.Object) -> None:
    turntable.rotation_mode = "XYZ"
    turntable.rotation_euler.z = 0.0
    turntable.keyframe_insert("rotation_euler", frame=TURN_START, index=2)
    turntable.rotation_euler.z = math.tau
    turntable.keyframe_insert("rotation_euler", frame=TURN_END, index=2)
    # Hold a visually identical rest pose for orbit and fly shots.
    turntable.keyframe_insert("rotation_euler", frame=ORBIT_START, index=2)
    turntable.keyframe_insert("rotation_euler", frame=FLY_END, index=2)
    keyframe_linear(turntable, "rotation_euler", {TURN_START, TURN_END})


def add_camera(
    name: str,
    collection: bpy.types.Collection,
    location: Sequence[float],
    target: bpy.types.Object,
    lens: float,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36.0
    data.dof.use_dof = True
    data.dof.focus_object = target
    data.dof.aperture_fstop = 4.0
    data.dof.aperture_blades = 8
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    look_at(obj, target)
    return obj


def build_cameras(collection: bpy.types.Collection, target: bpy.types.Object) -> dict[str, bpy.types.Object]:
    hero = add_camera("CAM_Hero_Turntable", collection, (7.8, -10.8, 5.3), target, 58)
    hero.data.dof.aperture_fstop = 3.5

    orbit_rig = add_empty("RIG_CameraOrbit", collection, (0, 0, 2.0))
    orbit = add_camera("CAM_Orbit", collection, (8.8, -10.8, 4.9), target, 62)
    orbit.parent = orbit_rig
    orbit.matrix_parent_inverse = orbit_rig.matrix_world.inverted()
    orbit_rig.rotation_euler.z = 0.0
    orbit_rig.keyframe_insert("rotation_euler", frame=ORBIT_START, index=2)
    orbit_rig.rotation_euler.z = math.tau
    orbit_rig.keyframe_insert("rotation_euler", frame=ORBIT_END, index=2)
    keyframe_linear(orbit_rig, "rotation_euler", {ORBIT_START, ORBIT_END})

    fly = add_camera("CAM_Flythrough", collection, (-7.8, -8.8, 1.8), target, 48)
    fly.data.dof.aperture_fstop = 5.0
    fly.rotation_mode = "XYZ"
    fly_positions = {
        FLY_START: (-7.8, -8.8, 1.8),
        525: (-4.0, -5.0, 3.2),
        575: (0.3, -3.7, 4.5),
        620: (4.2, -4.7, 3.0),
        FLY_END: (7.6, -8.0, 2.1),
    }
    for frame, position in fly_positions.items():
        fly.location = position
        fly.keyframe_insert("location", frame=frame)
    if fly.animation_data and fly.animation_data.action:
        for curve in action_fcurves(fly.animation_data.action):
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

    return {"hero": hero, "orbit": orbit, "fly": fly, "orbit_rig": orbit_rig}


def set_engine(scene: bpy.types.Scene, requested: str) -> str:
    candidates = {
        "eevee": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"),
        "cycles": ("CYCLES",),
        "auto": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"),
    }[requested]
    for engine in candidates:
        try:
            scene.render.engine = engine
            break
        except (TypeError, ValueError):
            continue
    else:
        raise RuntimeError(f"None of the requested render engines are available: {candidates}")

    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        scene.cycles.preview_samples = 32
    else:
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            set_if_present(eevee, "taa_render_samples", 96)
            set_if_present(eevee, "taa_samples", 32)
            set_if_present(eevee, "use_gtao", True)
            set_if_present(eevee, "gtao_distance", 3.0)
            set_if_present(eevee, "gtao_factor", 1.25)
            set_if_present(eevee, "use_raytracing", True)
    return scene.render.engine


def configure_world(scene: bpy.types.Scene) -> None:
    world = bpy.data.worlds.new("WORLD_Showcase")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.002, 0.004, 0.014, 1.0)
    background.inputs["Strength"].default_value = 0.12
    scene.world = world


def configure_compositor(scene: bpy.types.Scene) -> None:
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    render_layers.name = "Render Layers"
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.name = "Subtle Practical Bloom"
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 1.15
    glare.size = 7
    composite = tree.nodes.new("CompositorNodeComposite")
    viewer = tree.nodes.new("CompositorNodeViewer")
    render_layers.location = (-320, 0)
    glare.location = (-80, 0)
    composite.location = (180, 30)
    viewer.location = (180, -100)
    tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], composite.inputs["Image"])
    tree.links.new(glare.outputs["Image"], viewer.inputs["Image"])


def configure_color(scene: bpy.types.Scene) -> None:
    view = scene.view_settings
    try:
        view.view_transform = "AgX"
    except (TypeError, ValueError):
        view.view_transform = "Filmic"
    available = {item.identifier for item in view.bl_rna.properties["look"].enum_items}
    preferred = ("AgX - Medium High Contrast", "Medium High Contrast", "Medium High Contrast")
    for look in preferred:
        if look in available:
            view.look = look
            break
    view.exposure = 0.35
    view.gamma = 1.0
    view.use_curve_mapping = False


def configure_render(scene: bpy.types.Scene, args: argparse.Namespace) -> None:
    render = scene.render
    render.resolution_x = max(64, args.resolution_x)
    render.resolution_y = max(64, args.resolution_y)
    render.resolution_percentage = max(1, min(100, args.resolution_percent))
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGB"
    render.image_settings.color_depth = "8"
    render.film_transparent = False
    render.use_file_extension = True
    render.fps = max(1, args.fps)
    render.filepath = "//renders/master/frame_"
    set_if_present(render, "use_motion_blur", True)
    set_if_present(render, "motion_blur_shutter", 0.35)
    scene.frame_start = TURN_START
    scene.frame_end = FLY_END
    scene.render.image_settings.color_mode = "RGB"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"


def add_timeline_markers(scene: bpy.types.Scene, cameras: dict[str, bpy.types.Object]) -> None:
    markers = (
        ("SHOT_01_TURNTABLE", TURN_START, cameras["hero"]),
        ("SHOT_02_ORBIT", ORBIT_START, cameras["orbit"]),
        ("SHOT_03_FLYTHROUGH", FLY_START, cameras["fly"]),
    )
    for name, frame, camera in markers:
        marker = scene.timeline_markers.new(name, frame=frame)
        marker.camera = camera
    for name, frame in (("END_TURNTABLE", TURN_END), ("END_ORBIT", ORBIT_END), ("END_FLYTHROUGH", FLY_END)):
        scene.timeline_markers.new(name, frame=frame)


def make_fly_scene(master: bpy.types.Scene, camera: bpy.types.Object) -> bpy.types.Scene:
    fly = master.copy()
    fly.name = "Showcase_Flythrough"
    fly.camera = camera
    fly.frame_start = FLY_START
    fly.frame_end = FLY_END
    fly.frame_set(FLY_START)
    fly.render.filepath = "//renders/flythrough/frame_"
    fly["shot_description"] = "Dedicated cinematic camera fly-through"
    return fly


def build_materials() -> dict[str, bpy.types.Material]:
    return {
        "cyclorama": material_principled("MAT_Cyclorama", (0.012, 0.016, 0.032, 1), roughness=0.31),
        "charcoal": material_principled("MAT_Charcoal", (0.008, 0.01, 0.016, 1), metallic=0.25, roughness=0.2),
        "black": material_principled("MAT_Black", (0.002, 0.003, 0.006, 1), metallic=0.55, roughness=0.16),
        "brushed": material_principled("MAT_BrushedMetal", (0.18, 0.21, 0.25, 1), metallic=0.92, roughness=0.23),
        "placeholder": material_principled("MAT_Placeholder", (0.06, 0.085, 0.12, 1), metallic=0.78, roughness=0.2),
        "cyan_emission": material_principled(
            "MAT_CyanEmission", (0.0, 0.24, 0.34, 1), metallic=0.15, roughness=0.2,
            emission=(0.0, 0.72, 1.0, 1), emission_strength=8.0,
        ),
        "magenta_emission": material_principled(
            "MAT_MagentaEmission", (0.3, 0.0, 0.08, 1), metallic=0.15, roughness=0.2,
            emission=(1.0, 0.0, 0.25, 1), emission_strength=8.0,
        ),
        "white_emission": material_principled(
            "MAT_WhiteEmission", (0.8, 0.86, 1.0, 1), roughness=0.28,
            emission=(0.75, 0.85, 1.0, 1), emission_strength=3.0,
        ),
    }


def select_shot(scene: bpy.types.Scene, cameras: dict[str, bpy.types.Object], shot: str) -> None:
    ranges = {
        "turntable": (TURN_START, TURN_END, cameras["hero"], "//renders/turntable/frame_"),
        "orbit": (ORBIT_START, ORBIT_END, cameras["orbit"], "//renders/orbit/frame_"),
        "fly": (FLY_START, FLY_END, cameras["fly"], "//renders/flythrough/frame_"),
    }
    start, end, camera, path = ranges[shot]
    scene.frame_start = start
    scene.frame_end = end
    scene.camera = camera
    scene.render.filepath = path


def build(args: argparse.Namespace) -> bpy.types.Scene:
    clean_file()
    scene = bpy.context.scene
    scene.name = "Showcase_Master"
    scene["studio_generator_version"] = STUDIO_VERSION
    scene["usage"] = "Reusable asset turntable, orbit, and camera fly-through studio"

    root = make_collection("SHOWCASE_STUDIO")
    set_collection = make_collection("SET", root)
    practical_collection = make_collection("PRACTICALS", root)
    light_collection = make_collection("LIGHTS", root)
    camera_collection = make_collection("CAMERAS_AND_RIGS", root)
    asset_collection = make_collection("DROP_ASSET_HERE", root)

    mats = build_materials()
    turntable, target, backdrop_target = build_set(set_collection, practical_collection, mats)
    build_lighting(light_collection, target, backdrop_target)

    if args.asset:
        try:
            imported = import_asset(args.asset.expanduser().resolve())
            for obj in imported:
                obj["showcase_import_source"] = str(args.asset)
            if not args.keep_imported_lights_cameras:
                imported = remove_imported_lights_cameras(imported)
            normalize_asset(imported, asset_collection, turntable, args.target_height)
        except Exception as error:
            print(f"[showcase] Asset import failed: {error}", file=sys.stderr)
            raise
    else:
        build_placeholder(asset_collection, turntable, mats)

    animate_turntable(turntable)
    cameras = build_cameras(camera_collection, target)
    scene.camera = cameras["hero"]
    add_timeline_markers(scene, cameras)
    configure_world(scene)
    configure_compositor(scene)
    configure_color(scene)
    configure_render(scene, args)
    engine = set_engine(scene, args.engine)
    scene["configured_render_engine"] = engine
    scene.frame_set(40)

    if not args.no_separate_fly_scene:
        make_fly_scene(scene, cameras["fly"])

    if not args.no_save:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
        print(f"[showcase] Saved: {output}")
    print(f"[showcase] Built studio with {engine}; Blender {bpy.app.version_string}")
    return scene


def main() -> None:
    args = parse_args()
    scene = build(args)
    if args.render_still:
        scene.camera = bpy.data.objects["CAM_Hero_Turntable"]
        scene.frame_set(40)
        scene.render.filepath = "//renders/stills/hero_0040.png"
        bpy.ops.render.render(write_still=True, scene=scene.name)
    elif args.render_shot:
        cameras = {
            "hero": bpy.data.objects["CAM_Hero_Turntable"],
            "orbit": bpy.data.objects["CAM_Orbit"],
            "fly": bpy.data.objects["CAM_Flythrough"],
        }
        select_shot(scene, cameras, args.render_shot)
        if bpy.context.window is not None:
            bpy.context.window.scene = scene
        bpy.ops.render.render(animation=True, scene=scene.name)


if __name__ == "__main__":
    main()
