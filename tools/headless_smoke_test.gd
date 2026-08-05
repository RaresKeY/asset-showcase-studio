extends SceneTree

func _initialize() -> void:
	var packed := load("res://scenes/showcase_studio.tscn") as PackedScene
	if packed == null:
		_fail("Main showcase scene could not be loaded.")
		return
	var studio: Node = packed.instantiate()
	root.add_child(studio)
	await process_frame
	var required: Array[NodePath] = [
		^"Stage/Turntable/AssetSlot",
		^"Lighting/KeyLight",
		^"Lighting/RimLight",
		^"Cameras/OrbitCameraRig",
		^"Cameras/FlyCameraRig",
		^"Interface",
	]
	for path: NodePath in required:
		if studio.get_node_or_null(path) == null:
			_fail("Missing required node: %s" % path)
			return
	var turntable := studio.get_node("Stage/Turntable") as ShowcaseTurntable
	var asset_slot := studio.get_node("Stage/Turntable/AssetSlot") as ShowcaseAssetSlot
	var placeholder_mesh := studio.get_node(
		"Stage/Turntable/AssetSlot/PlaceholderAsset/Body"
	) as MeshInstance3D
	if turntable == null or asset_slot == null or placeholder_mesh == null:
		_fail("Typed showcase nodes could not be resolved.")
		return
	if not InputMap.has_action("toggle_mesh_lines"):
		_fail("Mesh-line input action is missing.")
		return
	asset_slot.set_mesh_lines_enabled(true)
	var overlay_material := placeholder_mesh.material_overlay as ShaderMaterial
	if overlay_material == null or overlay_material.shader == null:
		_fail("Mesh-line mode did not mount its shader overlay.")
		return
	var uniform_names: Array[StringName] = []
	var shader_uniforms: Array[Dictionary] = (
		overlay_material.shader.get_shader_uniform_list()
	)
	for uniform_data: Dictionary in shader_uniforms:
		uniform_names.append(StringName(uniform_data.get("name", "")))
	var required_uniforms: Array[StringName] = [&"line_color", &"line_offset"]
	for required_uniform: StringName in required_uniforms:
		if required_uniform not in uniform_names:
			_fail("Mesh-line shader is missing uniform: %s" % required_uniform)
			return
	asset_slot.set_mesh_lines_enabled(false)
	if placeholder_mesh.material_overlay != null:
		_fail("Smooth mode did not restore the placeholder's original overlay.")
		return
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
