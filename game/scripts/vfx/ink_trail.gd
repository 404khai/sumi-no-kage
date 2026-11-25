## Brush-stroke weapon trail. Samples two points (blade base/tip) every frame
## and rebuilds a small ribbon; the stroke shader dries it out with age.
## Cost: one draw call, <= 2 * max_points vertices.
class_name InkTrail
extends MeshInstance3D

const STROKE_MATERIAL := preload("res://materials/vfx/M_Vfx_InkStroke.tres")

@export var base_node: Node3D
@export var tip_node: Node3D
@export var lifetime := 0.3
@export var emitting := true
@export var min_step := 0.015
@export var max_points := 48
## Widen/narrow the ribbon around the blade (1 = blade length).
@export var width_scale := 1.0
## Catmull-Rom sub-samples per recorded segment: keeps arcs round at low framerates.
@export var smoothing := 4

var _pts: Array = []   # [{b: Vector3, t: Vector3, age: float}]
var _imesh := ImmediateMesh.new()


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	mesh = _imesh
	if material_override == null:
		material_override = STROKE_MATERIAL
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	extra_cull_margin = 16.0


func _process(delta: float) -> void:
	for p in _pts:
		p.age += delta
	while _pts.size() > 0 and _pts[-1].age > lifetime:
		_pts.pop_back()
	if emitting and base_node and tip_node:
		var b := base_node.global_position
		var t := tip_node.global_position
		var mid := (b + t) * 0.5
		var half := (t - b) * 0.5 * width_scale
		b = mid - half
		t = mid + half
		if _pts.is_empty() or (_pts[0].t.distance_to(t) > min_step):
			_pts.push_front({"b": b, "t": t, "age": 0.0})
			if _pts.size() > max_points:
				_pts.pop_back()
		else:
			_pts[0].b = b
			_pts[0].t = t
	_rebuild()


func clear() -> void:
	_pts.clear()
	_imesh.clear_surfaces()


func _rebuild() -> void:
	_imesh.clear_surfaces()
	var n := _pts.size()
	if n < 2:
		return
	_imesh.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	var total := (n - 1) * smoothing + 1
	var k := 0
	for i in n - 1:
		var p0 = _pts[maxi(i - 1, 0)]
		var p1 = _pts[i]
		var p2 = _pts[i + 1]
		var p3 = _pts[mini(i + 2, n - 1)]
		var steps := smoothing if i < n - 2 else smoothing + 1
		for s in steps:
			var f := float(s) / float(smoothing)
			var b := _cr(p0.b, p1.b, p2.b, p3.b, f)
			var t := _cr(p0.t, p1.t, p2.t, p3.t, f)
			var age := lerpf(p1.age, p2.age, f)
			var life := clampf(1.0 - age / lifetime, 0.0, 1.0)
			var u := float(k) / float(total - 1)
			_imesh.surface_set_color(Color(1, 1, 1, life))
			_imesh.surface_set_uv(Vector2(u, 0.0))
			_imesh.surface_add_vertex(b)
			_imesh.surface_set_color(Color(1, 1, 1, life))
			_imesh.surface_set_uv(Vector2(u, 1.0))
			_imesh.surface_add_vertex(t)
			k += 1
	_imesh.surface_end()


static func _cr(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)
