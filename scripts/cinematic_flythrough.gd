class_name ShowcaseCinematicFlythrough
extends Node3D

@export_category("Cinematic Fly-through")
@export_range(2.0, 60.0, 0.5, "suffix:s") var duration_seconds := 12.0
@export var loop_playback := true
@export var start_position := Vector3(-7.2, 1.7, 7.8)
@export var control_position_a := Vector3(-3.8, 4.8, 5.0)
@export var control_position_b := Vector3(3.9, 3.7, 4.7)
@export var end_position := Vector3(7.2, 2.0, 7.4)
@export_range(20.0, 100.0, 1.0, "suffix:deg") var start_fov := 52.0
@export_range(20.0, 100.0, 1.0, "suffix:deg") var middle_fov := 42.0

@onready var studio: ShowcaseStudio = $ShowcaseStudio
@onready var fly_rig: ShowcaseFlyCamera = $ShowcaseStudio/Cameras/FlyCameraRig
@onready var fly_camera: Camera3D = $ShowcaseStudio/Cameras/FlyCameraRig/Camera3D
@onready var asset_slot: ShowcaseAssetSlot = $ShowcaseStudio/Stage/Turntable/AssetSlot

var _elapsed := 0.0
var _look_target := Vector3(0.0, 1.4, 0.0)

func _ready() -> void:
	# Keep the fly camera current while this scene owns its transform.
	fly_rig.set_process(false)
	fly_rig.set_process_unhandled_input(false)
	studio.overlay.visible = false
	if "--clean-capture" in OS.get_cmdline_user_args():
		loop_playback = false
	asset_slot.asset_fitted.connect(_on_asset_fitted)
	_look_target = asset_slot.to_global(Vector3(0.0, 1.25, 0.0))
	_apply_pose(0.0)

func _process(delta: float) -> void:
	_elapsed += delta
	var progress := _elapsed / maxf(duration_seconds, 0.001)
	if loop_playback:
		progress = fmod(progress, 1.0)
	else:
		progress = minf(progress, 1.0)
	_apply_pose(progress)

func _on_asset_fitted(bounds: AABB) -> void:
	_look_target = asset_slot.to_global(bounds.position + bounds.size * 0.5)

func _apply_pose(progress: float) -> void:
	# Smooth acceleration at both ends keeps the shot edit-friendly.
	var eased := 0.5 - 0.5 * cos(clampf(progress, 0.0, 1.0) * PI)
	fly_rig.global_position = start_position.bezier_interpolate(
		control_position_a,
		control_position_b,
		end_position,
		eased
	)
	fly_rig.look_at(_look_target, Vector3.UP)
	var focus_curve := sin(eased * PI)
	fly_camera.fov = lerpf(start_fov, middle_fov, focus_curve)
