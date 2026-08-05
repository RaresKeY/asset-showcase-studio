class_name ShowcaseStudio
extends Node3D

@export_category("Studio Lighting")
@export var key_color := Color("37d8ff")
@export var rim_color := Color("ff3eb5")
@export_range(0.0, 32.0, 0.1) var key_energy := 8.0
@export_range(0.0, 32.0, 0.1) var rim_energy := 7.0
@export_range(0.0, 16.0, 0.1) var overhead_energy := 2.2
@export var neutral_key_color := Color("fff7ec")
@export var neutral_rim_color := Color("dce8ff")
@export_range(0.0, 32.0, 0.1) var neutral_key_energy := 5.5
@export_range(0.0, 32.0, 0.1) var neutral_rim_energy := 3.8
@export_category("Recording")
@export var start_with_ui_visible := true
@export var start_in_fly_camera := false
@export var capture_directory: String = "user://showcase_captures"
@export_range(1.0, 30.0, 1.0) var speed_adjust_step := 3.0

@onready var turntable: ShowcaseTurntable = $Stage/Turntable
@onready var orbit_camera: ShowcaseOrbitCamera = $Cameras/OrbitCameraRig
@onready var fly_camera: ShowcaseFlyCamera = $Cameras/FlyCameraRig
@onready var overlay: CanvasLayer = $Interface
@onready var status_label: Label = $Interface/Margin/Panel/VBox/Status
@onready var camera_label: Label = $Interface/Margin/Panel/VBox/Camera
@onready var lighting_label: Label = $Interface/Margin/Panel/VBox/Lighting
@onready var surface_label: Label = $Interface/Margin/Panel/VBox/Surface
@onready var asset_slot: ShowcaseAssetSlot = $Stage/Turntable/AssetSlot

var _fly_mode := false
var _lighting_preset := 0

func _ready() -> void:
	_apply_lighting_preset(0)
	overlay.visible = start_with_ui_visible
	if "--clean-capture" in OS.get_cmdline_user_args():
		overlay.visible = false
	set_fly_camera(start_in_fly_camera)
	turntable.playback_changed.connect(_on_turntable_changed)
	turntable.speed_changed.connect(_on_speed_changed)
	asset_slot.asset_fitted.connect(_on_asset_fitted)
	asset_slot.presentation_mode_changed.connect(_on_presentation_mode_changed)
	_update_status()
	_update_surface_status(asset_slot.mesh_lines_enabled())

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_ui"):
		overlay.visible = not overlay.visible
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("toggle_turntable"):
		turntable.toggle_pause()
	elif event.is_action_pressed("reverse_turntable"):
		turntable.reverse()
	elif event.is_action_pressed("slower_turntable"):
		turntable.adjust_speed(-speed_adjust_step)
	elif event.is_action_pressed("faster_turntable"):
		turntable.adjust_speed(speed_adjust_step)
	elif event.is_action_pressed("switch_camera"):
		set_fly_camera(not _fly_mode)
	elif event.is_action_pressed("reset_camera"):
		turntable.reset_rotation()
		if _fly_mode:
			fly_camera.reset_pose()
		else:
			orbit_camera.reset_pose()
	elif event.is_action_pressed("shot_1"):
		_apply_shot(1)
	elif event.is_action_pressed("shot_2"):
		_apply_shot(2)
	elif event.is_action_pressed("shot_3"):
		_apply_shot(3)
	elif event.is_action_pressed("shot_4"):
		_apply_shot(4)
	elif event.is_action_pressed("shot_5"):
		_apply_shot(5)
	elif event.is_action_pressed("shot_6"):
		_apply_shot(6)
	elif event.is_action_pressed("shot_7"):
		_apply_shot(7)
	elif event.is_action_pressed("capture_frame"):
		_capture_frame()
	elif event.is_action_pressed("cycle_lighting"):
		_apply_lighting_preset((_lighting_preset + 1) % 2)
	elif event.is_action_pressed("toggle_mesh_lines"):
		asset_slot.toggle_mesh_lines()

func set_fly_camera(value: bool) -> void:
	_fly_mode = value
	orbit_camera.set_active(not _fly_mode)
	fly_camera.set_active(_fly_mode)
	if is_instance_valid(camera_label):
		camera_label.text = "CAMERA  %s" % ("FLY" if _fly_mode else "HERO / ORBIT")

func _on_turntable_changed(_paused: bool) -> void:
	_update_status()

func _on_speed_changed(_speed: float) -> void:
	_update_status()

func _on_presentation_mode_changed(mesh_lines_enabled: bool) -> void:
	_update_surface_status(mesh_lines_enabled)

func _update_status() -> void:
	if not is_instance_valid(status_label):
		return
	var state := "PAUSED" if turntable.paused else "ROLLING"
	var direction := "CW" if turntable.clockwise else "CCW"
	status_label.text = "TURNTABLE  %s  |  %.1f°/s  %s" % [state, turntable.speed_degrees, direction]

func _update_surface_status(mesh_lines_enabled: bool) -> void:
	surface_label.text = "SURFACE  %s" % ("TEXTURED + MESH LINES" if mesh_lines_enabled else "TEXTURED SMOOTH")

func _on_asset_fitted(bounds: AABB) -> void:
	bounds = asset_slot.global_transform * bounds
	orbit_camera.frame_bounds(bounds)

func _apply_shot(index: int) -> void:
	if _fly_mode:
		set_fly_camera(false)
	orbit_camera.apply_shot_preset(index)

func _capture_frame() -> void:
	var ui_was_visible := overlay.visible
	overlay.visible = false
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var stamp := Time.get_datetime_string_from_system().replace(":", "-")
	var absolute_directory := ProjectSettings.globalize_path(capture_directory)
	var directory_result := DirAccess.make_dir_recursive_absolute(absolute_directory)
	var path := capture_directory.path_join("showcase_%s.png" % stamp)
	if directory_result != OK:
		overlay.visible = ui_was_visible
		push_warning("Could not create capture directory %s (error %s)." % [absolute_directory, directory_result])
		return
	var result := image.save_png(path)
	overlay.visible = ui_was_visible
	if result == OK:
		var absolute_path := ProjectSettings.globalize_path(path)
		print("Showcase frame saved: %s" % absolute_path)
		status_label.text = "CAPTURE SAVED  |  %s" % path.get_file()
		get_tree().create_timer(3.0).timeout.connect(_update_status)
	else:
		push_warning("Could not save showcase frame (error %s)." % result)

func _apply_lighting_preset(index: int) -> void:
	_lighting_preset = index
	var neutral := _lighting_preset == 1
	$Lighting/KeyLight.light_color = neutral_key_color if neutral else key_color
	$Lighting/KeyLight.light_energy = neutral_key_energy if neutral else key_energy
	$Lighting/RimLight.light_color = neutral_rim_color if neutral else rim_color
	$Lighting/RimLight.light_energy = neutral_rim_energy if neutral else rim_energy
	$Lighting/OverheadLight.light_energy = overhead_energy
	if is_instance_valid(lighting_label):
		lighting_label.text = "LIGHTING  %s" % ("NEUTRAL CHECK" if neutral else "CYAN / MAGENTA")
