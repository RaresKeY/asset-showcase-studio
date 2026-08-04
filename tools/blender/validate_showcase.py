#!/usr/bin/env python3
"""Validate a generated showcase .blend from inside Blender.

Usage:
    blender --background showcase.blend --python validate_showcase.py
"""

from __future__ import annotations

import argparse
import sys

import bpy


REQUIRED_OBJECTS = {
    "SET_Cyclorama",
    "RIG_Turntable",
    "ASSET_Root",
    "RIG_LookTarget",
    "RIG_BackdropTarget",
    "LIGHT_Key_Cyan",
    "LIGHT_Rim_Magenta",
    "LIGHT_Fill_Soft",
    "LIGHT_Backdrop_Wash",
    "CAM_Hero_Turntable",
    "CAM_Orbit",
    "CAM_Flythrough",
}
REQUIRED_COLLECTIONS = {
    "SHOWCASE_STUDIO",
    "SET",
    "PRACTICALS",
    "LIGHTS",
    "CAMERAS_AND_RIGS",
    "DROP_ASSET_HERE",
}
REQUIRED_MARKERS = {"SHOT_01_TURNTABLE", "SHOT_02_ORBIT", "SHOT_03_FLYTHROUGH"}
FLY_START = 481
FLY_END = 660


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-imported-lights-cameras",
        action="store_true",
        help="Do not fail when explicitly retained imported lights/cameras are present",
    )
    parser.add_argument(
        "--allow-no-separate-fly-scene",
        action="store_true",
        help="Do not require the default dedicated fly-through scene",
    )
    return parser.parse_args(argv)


def color_distance(first, second) -> float:
    return sum((float(a) - float(b)) ** 2 for a, b in zip(first, second)) ** 0.5


def has_track_target(obj: bpy.types.Object, target: bpy.types.Object) -> bool:
    return any(
        constraint.type == "TRACK_TO" and constraint.target == target
        for constraint in obj.constraints
    )


def main() -> None:
    args = parse_args()
    scene = bpy.data.scenes.get("Showcase_Master")
    errors: list[str] = []
    if scene is None:
        errors.append("missing Showcase_Master scene")
    else:
        missing_objects = REQUIRED_OBJECTS.difference(bpy.data.objects.keys())
        missing_collections = REQUIRED_COLLECTIONS.difference(bpy.data.collections.keys())
        marker_names = {marker.name for marker in scene.timeline_markers}
        missing_markers = REQUIRED_MARKERS.difference(marker_names)
        if missing_objects:
            errors.append(f"missing objects: {sorted(missing_objects)}")
        if missing_collections:
            errors.append(f"missing collections: {sorted(missing_collections)}")
        if missing_markers:
            errors.append(f"missing shot markers: {sorted(missing_markers)}")
        if scene.camera is None:
            errors.append("master scene has no active camera")
        if not scene.use_nodes or scene.node_tree.nodes.get("Subtle Practical Bloom") is None:
            errors.append("compositor bloom chain is missing")
        turntable = bpy.data.objects.get("RIG_Turntable")
        orbit_rig = bpy.data.objects.get("RIG_CameraOrbit")
        fly_camera = bpy.data.objects.get("CAM_Flythrough")
        asset_root = bpy.data.objects.get("ASSET_Root")
        cyan = bpy.data.objects.get("LIGHT_Key_Cyan")
        magenta = bpy.data.objects.get("LIGHT_Rim_Magenta")
        backdrop_light = bpy.data.objects.get("LIGHT_Backdrop_Wash")
        backdrop_target = bpy.data.objects.get("RIG_BackdropTarget")
        if turntable is not None and not turntable.animation_data:
            errors.append("turntable has no animation")
        if orbit_rig is not None and not orbit_rig.animation_data:
            errors.append("orbit rig has no animation")
        if fly_camera is not None and not fly_camera.animation_data:
            errors.append("fly-through camera has no animation")
        if asset_root is not None and turntable is not None and asset_root.parent != turntable:
            errors.append("ASSET_Root is not parented to RIG_Turntable")

        if cyan is not None and magenta is not None:
            if cyan.type != "LIGHT" or magenta.type != "LIGHT":
                errors.append("named cyan/magenta studio objects are not lights")
            else:
                cyan_color = tuple(cyan.data.color)
                magenta_color = tuple(magenta.data.color)
                if color_distance(cyan_color, magenta_color) < 0.5:
                    errors.append("cyan and magenta studio lights are not distinctly colored")
                if not (cyan_color[1] > cyan_color[0] and cyan_color[2] > cyan_color[0]):
                    errors.append("LIGHT_Key_Cyan does not have a cyan-dominant color")
                if not (magenta_color[0] > magenta_color[1] and magenta_color[2] > magenta_color[1]):
                    errors.append("LIGHT_Rim_Magenta does not have a magenta-dominant color")
                if cyan.data.energy <= 0 or magenta.data.energy <= 0:
                    errors.append("colored studio lights must have positive energy")

        if backdrop_light is not None and backdrop_target is not None:
            if not has_track_target(backdrop_light, backdrop_target):
                errors.append("LIGHT_Backdrop_Wash is not aimed at RIG_BackdropTarget")

        cyclorama = bpy.data.objects.get("SET_Cyclorama")
        if cyclorama is not None and cyclorama.type == "MESH":
            floor_faces = [polygon for polygon in cyclorama.data.polygons if polygon.center.z < 0.15]
            wall_faces = [
                polygon
                for polygon in cyclorama.data.polygons
                if polygon.center.y > 4.85 and polygon.center.z > 2.1
            ]
            if not floor_faces or any(polygon.normal.z <= 0.0 for polygon in floor_faces):
                errors.append("cyclorama floor normals do not point into the studio (+Z)")
            if not wall_faces or any(polygon.normal.y >= 0.0 for polygon in wall_faces):
                errors.append("cyclorama wall normals do not point into the studio (-Y)")

        imported_shot_objects = [
            obj
            for obj in bpy.data.objects
            if obj.type in {"LIGHT", "CAMERA"} and "showcase_import_source" in obj
        ]
        if imported_shot_objects and not args.allow_imported_lights_cameras:
            errors.append(
                "imported lights/cameras were retained without validator opt-in: "
                f"{sorted(obj.name for obj in imported_shot_objects)}"
            )

        fly_scene = bpy.data.scenes.get("Showcase_Flythrough")
        if fly_scene is None:
            if not args.allow_no_separate_fly_scene:
                errors.append("missing dedicated Showcase_Flythrough scene")
        elif fly_camera is not None:
            if fly_scene.camera != fly_camera:
                errors.append("Showcase_Flythrough does not use CAM_Flythrough")
            if (fly_scene.frame_start, fly_scene.frame_end) != (FLY_START, FLY_END):
                errors.append(
                    "Showcase_Flythrough frame range is not "
                    f"{FLY_START}-{FLY_END}"
                )
            if fly_scene.frame_current != FLY_START:
                errors.append(
                    f"Showcase_Flythrough current frame is not its start ({FLY_START})"
                )

    if errors:
        print("[showcase validation] FAILED")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print(
        "[showcase validation] OK: set, asset root, colored lighting, three cameras, "
        "shot markers, compositor, clean imported controls, fly scene, parenting, "
        "cyclorama normals, and animations are correct"
    )


if __name__ == "__main__":
    main()
