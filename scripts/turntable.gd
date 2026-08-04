class_name ShowcaseTurntable
extends Node3D

signal playback_changed(paused: bool)
signal speed_changed(degrees_per_second: float)

@export_category("Turntable")
@export_range(0.0, 180.0, 0.5, "suffix:deg/s") var speed_degrees := 18.0
@export var clockwise := true
@export var paused := false
@export var reset_angle_degrees := 0.0

func _process(delta: float) -> void:
	if paused or is_zero_approx(speed_degrees):
		return
	var direction := -1.0 if clockwise else 1.0
	rotate_y(deg_to_rad(speed_degrees) * direction * delta)

func toggle_pause() -> void:
	set_paused(not paused)

func set_paused(value: bool) -> void:
	paused = value
	playback_changed.emit(paused)

func reverse() -> void:
	clockwise = not clockwise
	speed_changed.emit(get_signed_speed())

func adjust_speed(delta_degrees: float) -> void:
	speed_degrees = clampf(speed_degrees + delta_degrees, 0.0, 180.0)
	speed_changed.emit(get_signed_speed())

func reset_rotation() -> void:
	rotation.y = deg_to_rad(reset_angle_degrees)

func get_signed_speed() -> float:
	return -speed_degrees if clockwise else speed_degrees

