## One-shot ink splatter (hits, Phantom Step departure/arrival).
## Particles are GPU-driven; the blot shader dries each splat with noise.
class_name InkBurst
extends GPUParticles3D

const BLOT_MATERIAL := preload("res://materials/vfx/M_Vfx_InkBlot.tres")
const BLOT_RED_MATERIAL := preload("res://materials/vfx/M_Vfx_InkBlotRed.tres")

static var _process_mat: ParticleProcessMaterial


static func spawn(parent: Node, at: Vector3, count := 28, red := false, scale_mul := 1.0) -> InkBurst:
	var b := InkBurst.new()
	b.amount = count
	b.red = red
	b.scale_mul = scale_mul
	parent.add_child(b)
	b.global_position = at
	b.restart()
	return b


var red := false
var scale_mul := 1.0


func _init() -> void:
	one_shot = true
	explosiveness = 0.92
	lifetime = 0.9
	local_coords = false
	emitting = false
	fixed_fps = 0
	visibility_aabb = AABB(Vector3(-4, -2, -4), Vector3(8, 6, 8))
	finished.connect(queue_free)


func _ready() -> void:
	if _process_mat == null:
		_process_mat = ParticleProcessMaterial.new()
		_process_mat.direction = Vector3(0, 1, 0)
		_process_mat.spread = 75.0
		_process_mat.initial_velocity_min = 1.5
		_process_mat.initial_velocity_max = 5.0
		_process_mat.gravity = Vector3(0, -7.0, 0)
		_process_mat.damping_min = 1.0
		_process_mat.damping_max = 3.0
		_process_mat.scale_min = 0.12
		_process_mat.scale_max = 0.45
		_process_mat.angle_min = -180.0
		_process_mat.angle_max = 180.0
		var ramp := Gradient.new()
		ramp.set_color(0, Color(1, 1, 1, 1))
		ramp.set_color(1, Color(1, 1, 1, 0))
		var gt := GradientTexture1D.new()
		gt.gradient = ramp
		_process_mat.color_ramp = gt
		var sc := Curve.new()
		sc.add_point(Vector2(0, 0.4))
		sc.add_point(Vector2(0.25, 1.0))
		sc.add_point(Vector2(1, 1.15))
		var sct := CurveTexture.new()
		sct.curve = sc
		_process_mat.scale_curve = sct
	process_material = _process_mat
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE * scale_mul
	quad.material = BLOT_RED_MATERIAL if red else BLOT_MATERIAL
	draw_pass_1 = quad
	emitting = true
