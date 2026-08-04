class_name ShowcaseOrbitCamera
extends Node3D

@export_category("Orbit Camera")
@export var enabled := true
@export_range(1.0, 30.0, 0.1) var distance := 7.2
@export_range(1.0, 30.0, 0.1) var min_distance := 2.0
@export_range(1.0, 40.0, 0.1) var max_distance := 15.0
@export_range(-85.0, 85.0, 0.5) var pitch_degrees := -12.0
@export var yaw_degrees := 24.0
@export var target_height := 1.45
@export_range(0.01, 1.0, 0.01) var drag_sensitivity := 0.18
@export_range(0.05, 2.0, 0.05) var zoom_step := 0.65

@onready var camera: Camera3D = $Pitch/Camera3D

var _default_distance: float
var _default_pitch: float
var _default_yaw: float
var _dragging := false

func _ready() -> void:
	_default_distance = distance
	_default_pitch = pitch_degrees
	_default_yaw = yaw_degrees
	_apply_pose()

func _unhandled_input(event: InputEvent) -> void:
	if not enabled:
		return
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT or event.button_index == MOUSE_BUTTON_MIDDLE:
			_dragging = event.pressed
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(min_distance, distance - zoom_step)
			_apply_pose()
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(max_distance, distance + zoom_step)
			_apply_pose()
	elif event is InputEventMouseMotion and _dragging:
		yaw_degrees -= event.relative.x * drag_sensitivity
		pitch_degrees = clampf(pitch_degrees - event.relative.y * drag_sensitivity, -80.0, 70.0)
		_apply_pose()

func set_active(value: bool) -> void:
	enabled = value
	camera.current = value
	if not value:
		_dragging = false

func reset_pose() -> void:
	distance = _default_distance
	pitch_degrees = _default_pitch
	yaw_degrees = _default_yaw
	_apply_pose()

func apply_shot_preset(index: int) -> void:
	distance = _default_distance
	match index:
		1:
			yaw_degrees = 0.0
			pitch_degrees = -8.0
		2:
			yaw_degrees = 35.0
			pitch_degrees = -13.0
		3:
			yaw_degrees = 90.0
			pitch_degrees = -5.0
		4:
			yaw_degrees = -35.0
			pitch_degrees = -58.0
		5:
			yaw_degrees = 24.0
			pitch_degrees = -8.0
			distance = clampf(_default_distance * 0.72, min_distance, max_distance)
		6:
			yaw_degrees = 180.0
			pitch_degrees = -8.0
		7:
			yaw_degrees = 24.0
			pitch_degrees = -6.0
			distance = clampf(_default_distance * 1.4, min_distance, max_distance)
	_apply_pose()

func frame_bounds(bounds: AABB) -> void:
	if bounds.size.length_squared() <= 0.000001:
		return
	target_height = bounds.position.y + bounds.size.y * 0.5
	var radius := maxf(bounds.size.x, maxf(bounds.size.y, bounds.size.z)) * 0.5
	var half_fov := deg_to_rad(camera.fov * 0.5)
	distance = clampf((radius / tan(half_fov)) * 1.45, min_distance, max_distance)
	_default_distance = distance
	_apply_pose()

func _apply_pose() -> void:
	position.y = target_height
	rotation.y = deg_to_rad(yaw_degrees)
	$Pitch.rotation.x = deg_to_rad(pitch_degrees)
	$Pitch/Camera3D.position.z = distance
