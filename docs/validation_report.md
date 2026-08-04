# Validation report

Build date: 2026-08-04

## Passed in the build environment

- All literal project `res://` dependencies resolve.
- Required studio, turntable, light, camera, asset slot, and interface nodes are
  present.
- GDScript parses with the current `tree-sitter-gdscript` grammar.
- Blender Python and project Python parse as valid Python.
- Shell helpers pass `bash -n`.
- No external art assets or Blender add-ons are required.

## Requires local engine verification

The build environment did not contain Godot, Blender, a display server, Vulkan,
or a GPU. It therefore could not perform a clean Godot import, native scene
parse, hardware render, `.blend` generation, or Blender render. Commands for
those checks are in the root README.

