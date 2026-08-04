# Drop showcase assets here

GLB is the recommended interchange format. Copy each subject into its own
subfolder, for example:

```text
assets/showcase/server_rack/server_rack.glb
assets/showcase/server_rack/textures/...
```

After Godot imports the file, select `Stage/Turntable/AssetSlot` in the main
showcase scene and set **External Asset Path**. The studio keeps imported scene
hierarchies intact, calculates the combined visible mesh bounds, centers the
subject, places its lowest point on the turntable, and scales it to the target
height.

Keep source textures beside the model, use meters, apply transforms before
export, and prefer +Y up. Imported cameras and lights should remain disabled so
the studio lighting and framing stay consistent between assets.

