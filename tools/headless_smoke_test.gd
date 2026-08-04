extends SceneTree

func _initialize() -> void:
	var packed := load("res://scenes/showcase_studio.tscn") as PackedScene
	if packed == null:
		_fail("Main showcase scene could not be loaded.")
		return
	var studio := packed.instantiate()
	root.add_child(studio)
	await process_frame
	var required := [
		"Stage/Turntable/AssetSlot",
		"Lighting/KeyLight",
		"Lighting/RimLight",
		"Cameras/OrbitCameraRig",
		"Cameras/FlyCameraRig",
		"Interface",
	]
	for path in required:
		if studio.get_node_or_null(path) == null:
			_fail("Missing required node: %s" % path)
			return
	var turntable := studio.get_node("Stage/Turntable") as ShowcaseTurntable
	var initial_rotation := turntable.rotation.y
	turntable._process(1.0)
	if is_equal_approx(initial_rotation, turntable.rotation.y):
		_fail("Turntable did not rotate during deterministic process step.")
		return
	print("SHOWCASE_SMOKE_TEST_OK")
	quit(0)

func _fail(message: String) -> void:
	push_error(message)
	quit(1)

