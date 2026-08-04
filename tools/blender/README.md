# Blender Showcase Studio

> [!WARNING]
> **Use this only as a new-file generator.** Running `build_showcase.py` deletes every object, non-active scene, collection, and world in the currently open `.blend` before building the studio. Run it in a fresh Blender file or through the background command below. It can also overwrite the path supplied with `--output`.

`build_showcase.py` creates a complete product-shot room without external add-ons. It includes:

- a seamless floor-to-wall cyclorama and architectural framing;
- a layered motorized pedestal with an emissive turntable ring;
- cyan key and magenta rim lights, soft fill, backdrop wash, and practical light panels;
- a static hero turntable shot, a full camera-orbit shot, and a cinematic fly-through;
- camera depth of field, AgX/Filmic fallback color management, and subtle compositor glow;
- Eevee Next, legacy Eevee, and Cycles compatibility paths;
- timeline camera markers and a separate `Showcase_Flythrough` scene by default;
- optional GLB/GLTF, OBJ, or FBX import with automatic centering, grounding, and scaling.

Embedded lights and cameras are removed from imported assets by default. This prevents a GLB or FBX from silently changing the studio look or overriding a shot. Use `--keep-imported-lights-cameras` only when that behavior is intentional.

When no asset is supplied, the project contains a polished procedural placeholder. This makes the generated `.blend` immediately renderable and shows the intended asset scale.

## Generate from the command line

```bash
blender --background --python tools/blender/build_showcase.py -- \
  --asset /absolute/path/to/my_asset.glb \
  --output /absolute/path/to/asset_showcase_studio.blend
```

For a lightweight project using the built-in placeholder:

```bash
blender --background --python tools/blender/build_showcase.py -- \
  --resolution-percent 50 \
  --output /absolute/path/to/asset_showcase_studio.blend
```

Useful options:

```text
--engine auto|eevee|cycles
--target-height 2.4
--resolution-x 1920 --resolution-y 1080 --resolution-percent 100
--fps 30
--keep-imported-lights-cameras
--no-separate-fly-scene
--render-still
--render-shot turntable|orbit|fly
--no-save
```

`--render-shot` renders a PNG sequence under the `.blend` file's `renders/` directory. Image sequences are deliberate: they survive interrupted renders and can be encoded later without losing the entire take.

## Generate in Blender's GUI

1. Open Blender and switch to **Scripting**.
2. Open `build_showcase.py` in the Text Editor.
3. Press **Run Script**.
4. With no command-line arguments, Blender saves `asset_showcase_studio.blend` in its current working directory and uses the placeholder asset.

To use a specific imported asset from the GUI, the cleanest workflow is to generate from the command line once. Alternatively, run the script, remove the placeholder objects in `DROP_ASSET_HERE`, import your model into that collection, then parent it under `ASSET_Root` and place its lowest point at turntable height `Z = 1.04`.

## Shot layout

| Shot | Frames | Camera | Purpose |
|---|---:|---|---|
| Turntable | 1–240 | `CAM_Hero_Turntable` | Locked hero composition while the product completes one rotation |
| Orbit | 241–480 | `CAM_Orbit` | Camera circles the resting product for a more dimensional reveal |
| Fly-through | 481–660 | `CAM_Flythrough` | Low-to-high cinematic pass with eased motion |

Timeline markers bind the correct camera at each shot boundary in `Showcase_Master`, whose 1–660 frame range plays the complete reel. The optional `Showcase_Flythrough` scene is already trimmed to frames 481–660.

For clean editing, render each range separately. The generated master starts on frame 40, a useful three-quarter hero angle.

## Replace the placeholder later

The safest repeatable method is to regenerate with `--asset`. For manual replacement:

1. Delete `ASSET_PlaceholderBody`, `ASSET_LuminousCore`, and both `ASSET_Collar_*` objects.
2. Import your asset and move it into `DROP_ASSET_HERE`.
3. Parent only the asset's top-level objects to `ASSET_Root` while preserving transforms.
4. Scale it to roughly 2.4 m tall and ground it at `Z = 1.04`.

Do not parent the product directly to the pedestal mesh if it already has animation or an armature; the dedicated `ASSET_Root` keeps imported hierarchy intact.

Automatic normalization evaluates render-enabled geometry through Blender's dependency graph at the scene's current frame, so modifiers, the current armature pose, and conventional Geometry Nodes bounds are included. It does not scan animation ranges, simulation caches, or every procedural state. For an animated asset, generate from a representative static/rest pose, then inspect extreme poses manually before the final render.

## Validate a generated file

```bash
blender --background /absolute/path/to/asset_showcase_studio.blend \
  --python tools/blender/validate_showcase.py
```

Validation checks the named set, collections, lights, camera rigs, shot markers, compositor, and all three animation systems. A successful run exits with status 0.

If the project was intentionally generated with a non-default structural option, mirror that opt-in during validation:

```bash
blender --background /absolute/path/to/asset_showcase_studio.blend \
  --python tools/blender/validate_showcase.py -- \
  --allow-imported-lights-cameras --allow-no-separate-fly-scene
```

## Practical render notes

- **Eevee** is the best default for rapid iteration and live camera work.
- **Cycles** gives richer glossy reflections; increase samples only for the final take.
- Render PNG sequences first, then encode them in Blender's Video Sequencer or FFmpeg.
- Keep the two colored lights on opposite sides of the asset. Their separated edge highlights are what make material and silhouette reads look expensive.
- If an imported model is extremely wide or flat, adjust `--target-height`, then fine-tune `ASSET_Root` rather than changing the camera rigs.
