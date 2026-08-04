# Filming guide

## A reliable asset reel

1. Start with `L` in **Neutral Check**. Inspect front, right, rear, and top views
   for broken normals, transparency ordering, missing textures, floating parts,
   and incorrect scale.
2. Switch back to **Cyan / Magenta** for the hero reel. Keep the turntable at
   18 degrees/second for a 20-second revolution or 30 degrees/second for a
   tighter 12-second reel.
3. Record the locked hero shot before moving the camera. A fixed camera makes
   comparisons between different assets much easier.
4. Add the detail and cinematic fly-through as optional inserts. Avoid shallow
   depth of field when small topology or surface details must remain readable.
5. Keep the AVI or PNG sequence as the master; make web delivery copies in
   H.264 MP4 with `yuv420p` pixel format.

## Suggested shot order

| Duration | Shot | Purpose |
|---:|---|---|
| 2 s | Hero three-quarter still | Immediate silhouette read |
| 12–20 s | Full turntable | Complete form and material coverage |
| 2 s | Top/inspection | Footprint and upper surfaces |
| 2 s | Detail | Recognition accent or best material |
| 8–12 s | Fly-through | Optional cinematic closer |

## Import checklist

- Applied transforms, meters, +Y up, useful object names.
- GLB textures present and correct color-space/ORM channels.
- No imported camera or light is required for the model to read correctly.
- Lowest visible mesh point meets the stage with only a few millimeters of
  clearance.
- Neutral and glam lighting both preserve the intended albedo.
- Fine geometry survives motion blur and the final delivery resolution.

