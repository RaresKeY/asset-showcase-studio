# Validation report

Review date: 2026-08-05

## Passed in the build environment

- All literal project `res://` dependencies resolve.
- Required studio, turntable, light, camera, asset slot, and interface nodes are
  present.
- GDScript parses with the current `tree-sitter-gdscript` grammar. This is a
  syntax-shape check, not Godot-native semantic validation.
- Regression fixtures reject comma-packed export filters and `:=` inference
  from Variant-returning Array access/removal methods.
- Blender Python and project Python parse as valid Python.
- Shell helpers pass `bash -n`.
- No external art assets or Blender add-ons are required.

## Repaired during the full-source review

- The asset-tree traversal now casts `Array.pop_back()` results to `Node`
  before typed use; bounds reuse that collector instead of duplicating the
  Variant-returning traversal.
- The mesh-line shader is a first-class `.gdshader` resource and uses a
  scale-compensated normal offset so equal-depth testing does not hide the wire
  after auto-fitting unusually large or small source assets.
- The studio uses its authored ambient color instead of selecting a missing
  Sky source.
- The presentation-mode label and help text are scene-owned and visible in the
  editor.
- The Blender set-builder return annotation matches its three returned objects.

## Requires local engine verification

The review environment did not contain Godot, Blender, a display server,
Vulkan, or a GPU. It therefore could not perform a clean Godot import, native
scene parse, shader compilation, Forward+ render comparison, `.blend`
generation, or Blender render. Run `tools/validate_godot.sh` with Godot 4.7 (the
wrapper rejects the wrong engine series) and inspect one smooth/mesh-line
screenshot pair before treating the visual path as engine-verified.
