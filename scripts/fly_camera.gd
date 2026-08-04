class_name ShowcaseFlyCamera
extends Node3D

@export_category("Fly Camera")
@export var enabled := false
@export_range(0.1, 30.0, 0.1) var move_speed := 4.5
@export_range(1.0, 10.0, 0.1) var fast_multiplier := 3.0
@export_range(0.01, 1.0, 0.01) var look_sensitivity := 0.12
@export var capture_mouse_on_right_click := true

@onready var camera: Camera3D = $Camera3D

var _looking := false
var _default_transform: Transform3D

func _ready() -> void:
	_default_transform = transform
	set_process(enabled)

func _process(delta: float) -> void:
	if not enabled:
		return
	var input_2d := Input.get_vector("fly_left", "fly_right", "fly_forward", "fly_back")
	var vertical := Input.get_axis("fly_down", "fly_up")
	var direction := Vector3(input_2d.x, vertical, input_2d.y)
	if direction.length_squared() > 1.0:
		direction = direction.normalized()
	var speed := move_speed * (fast_multiplier if Input.is_action_pressed("fly_fast") else 1.0)
	global_position += global_basis * direction * speed * delta

func _unhandled_input(event: InputEvent) -> void:
	if not enabled:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		_looking = event.pressed
		if capture_mouse_on_right_click:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if _looking else Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseMotion and _looking:
		rotation.y -= deg_to_rad(event.relative.x * look_sensitivity)
		rotation.x = clampf(rotation.x - deg_to_rad(event.relative.y * look_sensitivity), deg_to_rad(-85.0), deg_to_rad(85.0))

func set_active(value: bool) -> void:
	enabled = value
	camera.current = value
	set_process(value)
	if not value:
		_looking = false
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func reset_pose() -> void:
	transform = _default_transform

