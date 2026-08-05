class_name ShowcaseAssetSlot
extends Node3D

const MESH_LINE_SHADER: Shader = preload("res://shaders/mesh_lines.gdshader")

signal asset_loaded(source_path: String)
signal asset_load_failed(source_path: String, reason: String)
signal asset_fitted(local_bounds: AABB)
signal presentation_mode_changed(mesh_lines_enabled: bool)

@export_category("Displayed Asset")
@export var asset_scene: PackedScene
@export_file("*.glb", "*.gltf", "*.obj", "*.tscn") var external_asset_path := ""
@export var auto_fit_to_stage := true
@export_range(0.1, 10.0, 0.05) var target_height := 2.35
@export_range(0.1, 10.0, 0.05) var target_diameter := 2.6
@export var center_on_stage := true
@export_range(0.0, 0.25, 0.001, "suffix:m") var vertical_offset := 0.008

@export_category("Presentation Surface")
@export var start_with_mesh_lines := false
@export var mesh_line_color := Color(0.12, 0.82, 1.0, 0.34)
@export_range(0.0, 0.02, 0.0001, "suffix:m") var mesh_line_offset := 0.0015

var _imported_root: Node3D
var _mesh_lines_enabled := false
var _mesh_line_material: ShaderMaterial
var _original_overlays: Dictionary[int, Material] = {}

func _ready() -> void:
	_mesh_lines_enabled = start_with_mesh_lines
	_mesh_line_material = _create_mesh_line_material()
	var command_line_path := _get_command_line_asset()
	if not command_line_path.is_empty():
		load_asset(command_line_path)
	elif not external_asset_path.is_empty():
		load_asset(external_asset_path)
	elif asset_scene != null:
		mount_scene(asset_scene, "Inspector PackedScene")
	call_deferred("_apply_presentation_mode")

func mount_scene(scene: PackedScene, source_label: String = "PackedScene") -> bool:
	var instance: Node3D = scene.instantiate() as Node3D
	if instance == null:
		asset_load_failed.emit(source_label, "PackedScene root must inherit Node3D.")
		return false
	_mount_instance(instance)
	asset_loaded.emit(source_label)
	return true

func load_asset(source_path: String) -> bool:
	if not ResourceLoader.exists(source_path):
		asset_load_failed.emit(source_path, "File is not imported by Godot or does not exist.")
		push_warning("Showcase asset not found: %s" % source_path)
		return false
	var resource: Resource = ResourceLoader.load(source_path)
	var instance: Node3D
	if resource is PackedScene:
		instance = resource.instantiate() as Node3D
	elif resource is Mesh:
		var mesh_instance: MeshInstance3D = MeshInstance3D.new()
		mesh_instance.mesh = resource as Mesh
		instance = mesh_instance
	if instance == null:
		asset_load_failed.emit(source_path, "Expected an imported 3D scene or mesh.")
		push_warning("Unsupported showcase asset resource: %s" % source_path)
		return false
	_mount_instance(instance)
	asset_loaded.emit(source_path)
	return true

func toggle_mesh_lines() -> bool:
	set_mesh_lines_enabled(not _mesh_lines_enabled)
	return _mesh_lines_enabled

func set_mesh_lines_enabled(value: bool) -> void:
	if _mesh_lines_enabled == value:
		return
	_mesh_lines_enabled = value
	_apply_presentation_mode()
	presentation_mode_changed.emit(_mesh_lines_enabled)

func mesh_lines_enabled() -> bool:
	return _mesh_lines_enabled

func _mount_instance(instance: Node3D) -> void:
	_restore_original_overlays()
	_original_overlays.clear()
	if is_instance_valid(_imported_root):
		_imported_root.queue_free()
	_imported_root = instance
	_imported_root.name = "ImportedAsset"
	add_child(_imported_root)
	var placeholder: Node3D = get_node_or_null("PlaceholderAsset") as Node3D
	if placeholder != null:
		placeholder.visible = false
	call_deferred("_apply_presentation_mode")
	if auto_fit_to_stage:
		call_deferred("_fit_imported_asset")

func _apply_presentation_mode() -> void:
	if not is_instance_valid(_mesh_line_material):
		_mesh_line_material = _create_mesh_line_material()
	_mesh_line_material.set_shader_parameter("line_color", mesh_line_color)
	_mesh_line_material.set_shader_parameter("line_offset", mesh_line_offset)
	for mesh_instance in _collect_mesh_instances(self):
		var instance_id := mesh_instance.get_instance_id()
		if _mesh_lines_enabled:
			if not _original_overlays.has(instance_id):
				_original_overlays[instance_id] = mesh_instance.material_overlay
			mesh_instance.material_overlay = _mesh_line_material
		elif _original_overlays.has(instance_id):
			mesh_instance.material_overlay = _original_overlays[instance_id]
	if not _mesh_lines_enabled:
		_original_overlays.clear()

func _restore_original_overlays() -> void:
	for mesh_instance in _collect_mesh_instances(self):
		var instance_id := mesh_instance.get_instance_id()
		if _original_overlays.has(instance_id):
			mesh_instance.material_overlay = _original_overlays[instance_id]

func _collect_mesh_instances(root: Node) -> Array[MeshInstance3D]:
	var meshes: Array[MeshInstance3D] = []
	var queue: Array[Node] = [root]
	while not queue.is_empty():
		# Array pop methods return Variant even for typed arrays. Cast before use
		# so Godot's static analyzer never has to infer through Variant.
		var current: Node = queue.pop_back() as Node
		if current == null:
			continue
		var mesh_instance: MeshInstance3D = current as MeshInstance3D
		if mesh_instance != null and mesh_instance.mesh != null:
			meshes.append(mesh_instance)
		for child in current.get_children():
			queue.push_back(child)
	return meshes

func _create_mesh_line_material() -> ShaderMaterial:
	var material: ShaderMaterial = ShaderMaterial.new()
	material.shader = MESH_LINE_SHADER
	material.set_shader_parameter("line_color", mesh_line_color)
	material.set_shader_parameter("line_offset", mesh_line_offset)
	return material

func _fit_imported_asset() -> void:
	if not is_instance_valid(_imported_root):
		return
	var bounds := _collect_bounds(_imported_root)
	if bounds.size.length_squared() <= 0.000001:
		push_warning("Imported showcase asset has no visible mesh bounds; automatic fitting skipped.")
		return
	var horizontal_diameter := maxf(bounds.size.x, bounds.size.z)
	var height_scale := target_height / bounds.size.y if bounds.size.y > 0.0001 else INF
	var diameter_scale := target_diameter / horizontal_diameter if horizontal_diameter > 0.0001 else INF
	var fit_scale := minf(height_scale, diameter_scale)
	if is_finite(fit_scale):
		_imported_root.scale *= fit_scale
		bounds = _collect_bounds(_imported_root)
	if center_on_stage:
		var center := bounds.position + bounds.size * 0.5
		_imported_root.position.x -= center.x
		_imported_root.position.z -= center.z
		bounds = _collect_bounds(_imported_root)
	_imported_root.position.y += vertical_offset - bounds.position.y
	bounds = _collect_bounds(_imported_root)
	asset_fitted.emit(bounds)

func _collect_bounds(root: Node) -> AABB:
	var merged: AABB = AABB()
	var has_bounds := false
	for mesh_instance in _collect_mesh_instances(root):
		var local_bounds: AABB = mesh_instance.get_aabb()
		var relative_transform: Transform3D = (
			global_transform.affine_inverse() * mesh_instance.global_transform
		)
		local_bounds = relative_transform * local_bounds
		if has_bounds:
			merged = merged.merge(local_bounds)
		else:
			merged = local_bounds
			has_bounds = true
	return merged

func _get_command_line_asset() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--asset="):
			return argument.trim_prefix("--asset=")
	return ""
