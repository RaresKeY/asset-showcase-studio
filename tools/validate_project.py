#!/usr/bin/env python3
"""Static validation for the portable showcase project.

This intentionally uses only the Python standard library so it can run before
Godot or Blender is installed. Engine-native smoke tests remain the authority.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RES_PATH = re.compile(r'(?P<path>res://[^"\'\s\)\]]+)')
CLASS_NAME = re.compile(r"^class_name\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
COMMA_FILE_FILTER = re.compile(
    r'''@export_(?:global_file|file(?:_path)?)\(\s*(["'])([^"']*,[^"']*)\1'''
)
VARIANT_ARRAY_INFERENCE = re.compile(
    r"^\s*var\s+[A-Za-z_][A-Za-z0-9_]*\s*:=\s*.*"
    r"\.(?:pop_back|pop_front|pop_at|front|back)\s*\(",
    re.MULTILINE,
)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_python(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            fail(errors, f"Python syntax: {path.relative_to(ROOT)}: {error}")


def validate_shell(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.sh")):
        result = subprocess.run(
            ["bash", "-n", str(path)], capture_output=True, text=True, check=False
        )
        if result.returncode:
            fail(errors, f"Shell syntax: {path.relative_to(ROOT)}: {result.stderr.strip()}")


def validate_resource_paths(errors: list[str]) -> None:
    source_suffixes = {".gd", ".gdshader", ".tscn", ".tres", ".godot"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in source_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for match in RES_PATH.finditer(text):
            resource = match.group("path")
            # Paths supplied as examples or runtime arguments are allowed to be absent.
            if "<" in resource or resource.startswith("res://assets/showcase/"):
                continue
            target = ROOT / resource.removeprefix("res://")
            if not target.exists():
                fail(errors, f"Missing resource from {path.relative_to(ROOT)}: {resource}")


def validate_godot_sources(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.gd")):
        text = path.read_text(encoding="utf-8")
        for match in COMMA_FILE_FILTER.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            fail(
                errors,
                f"Comma-separated file export filter at "
                f"{path.relative_to(ROOT)}:{line_number}; "
                "pass each filter as a separate string argument",
            )
        for match in VARIANT_ARRAY_INFERENCE.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            fail(
                errors,
                f"Variant-returning Array method inferred with := at "
                f"{path.relative_to(ROOT)}:{line_number}; "
                "declare the variable type and cast the popped value",
            )


def validate_godot_shape(errors: list[str]) -> None:
    project = ROOT / "project.godot"
    if not project.exists():
        fail(errors, "Missing project.godot")
        return
    project_text = project.read_text(encoding="utf-8")

    main_match = re.search(r'^run/main_scene="res://([^\"]+)"', project_text, re.MULTILINE)
    if not main_match:
        fail(errors, "project.godot has no run/main_scene")
    elif not (ROOT / main_match.group(1)).exists():
        fail(errors, f"Main scene does not exist: {main_match.group(1)}")

    if 'renderer/rendering_method="forward_plus"' not in project_text:
        fail(errors, "Desktop renderer is not configured for Forward+")
    for action in (
        "toggle_ui",
        "toggle_turntable",
        "reverse_turntable",
        "slower_turntable",
        "faster_turntable",
        "switch_camera",
        "reset_camera",
        "cycle_lighting",
        "capture_frame",
        "toggle_mesh_lines",
        "shot_1",
        "shot_2",
        "shot_3",
        "shot_4",
        "shot_5",
        "shot_6",
        "shot_7",
        "fly_forward",
        "fly_back",
        "fly_left",
        "fly_right",
        "fly_up",
        "fly_down",
        "fly_fast",
    ):
        if f"{action}={{" not in project_text:
            fail(errors, f"project.godot is missing input action: {action}")

    classes: dict[str, Path] = {}
    for path in sorted(ROOT.rglob("*.gd")):
        text = path.read_text(encoding="utf-8")
        match = CLASS_NAME.search(text)
        if not match:
            continue
        name = match.group(1)
        if name in classes:
            fail(
                errors,
                f"Duplicate GDScript class_name {name}: "
                f"{classes[name].relative_to(ROOT)} and {path.relative_to(ROOT)}",
            )
        classes[name] = path

    main_scene = ROOT / "scenes/showcase_studio.tscn"
    if main_scene.exists():
        scene_text = main_scene.read_text(encoding="utf-8")
        for required in (
            "AssetSlot",
            "Turntable",
            "KeyLight",
            "RimLight",
            "OrbitCameraRig",
            "FlyCameraRig",
            "StudioReflectionProbe",
            "Interface",
            "Surface",
        ):
            if f'name="{required}"' not in scene_text:
                fail(errors, f"Main scene is missing required node: {required}")
        if "ambient_light_source = 2" not in scene_text:
            fail(errors, "Studio environment is not using its authored ambient color")
        if "ambient_light_sky_contribution = 0.0" not in scene_text:
            fail(errors, "Studio environment still mixes an undefined sky into ambient light")

    mesh_line_shader = ROOT / "shaders/mesh_lines.gdshader"
    if mesh_line_shader.exists():
        shader_text = mesh_line_shader.read_text(encoding="utf-8")
        for required in (
            "uniform vec4 line_color",
            "uniform float line_offset",
            "MODEL_MATRIX",
            "VERTEX += NORMAL",
        ):
            if required not in shader_text:
                fail(errors, f"Mesh-line shader is missing: {required}")

    fly_scene = ROOT / "scenes/flythrough_showcase.tscn"
    if not fly_scene.exists():
        fail(errors, "Missing cinematic fly-through scene")
    else:
        fly_text = fly_scene.read_text(encoding="utf-8")
        if "res://scripts/cinematic_flythrough.gd" not in fly_text:
            fail(errors, "Fly-through scene is not driven by the cinematic script")


def validate_clean_package(errors: list[str]) -> None:
    junk = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if junk:
        fail(errors, "Generated cache files are present: " + ", ".join(map(str, junk)))
    for required in (
        ROOT / "README.md",
        ROOT / "shaders/mesh_lines.gdshader",
        ROOT / "tools/validate_godot.sh",
        ROOT / "tools/render_godot_movie.sh",
        ROOT / "tools/blender/build_showcase.py",
        ROOT / "docs/filming_guide.md",
    ):
        if not required.exists():
            fail(errors, f"Missing deliverable file: {required.relative_to(ROOT)}")


def main() -> int:
    errors: list[str] = []
    validate_python(errors)
    validate_shell(errors)
    validate_resource_paths(errors)
    validate_godot_sources(errors)
    validate_godot_shape(errors)
    validate_clean_package(errors)
    if errors:
        print("SHOWCASE_STATIC_VALIDATION_FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    count = sum(1 for path in ROOT.rglob("*") if path.is_file())
    print(f"SHOWCASE_STATIC_VALIDATION_OK ({count} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
