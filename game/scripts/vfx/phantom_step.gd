## Phantom Step presentation: the body dissolves into ink, a brush streak marks
## the path, and the body re-forms at the destination. Gameplay (direction,
## distance, i-frames) lives in the combat layer; this only plays the effect.
class_name PhantomStepVFX
extends Node

signal finished

@export var body: Node3D               ## the character root that moves
@export var dissolve_time := 0.12
@export var travel_time := 0.08
@export var reform_time := 0.22

var _geometry: Array[GeometryInstance3D] = []
var _streak_node: Node3D
var _streak: InkTrail


func _ready() -> void:
	_collect(body)
	_streak_node = Node3D.new()
	add_child(_streak_node)
	var b := Node3D.new()
	var t := Node3D.new()
	_streak_node.add_child(b)
	_streak_node.add_child(t)
	b.position = Vector3(0, 0.35, 0)
	t.position = Vector3(0, 1.55, 0)
	_streak = InkTrail.new()
	_streak.base_node = b
	_streak.tip_node = t
	_streak.lifetime = 0.55
	_streak.emitting = false
	add_child(_streak)


func _collect(n: Node) -> void:
	if n is GeometryInstance3D:
		_geometry.append(n)
	for c in n.get_children():
		_collect(c)


func set_dissolve(v: float) -> void:
	for g in _geometry:
		if is_instance_valid(g):
			g.set_instance_shader_parameter("dissolve", v)


func step(to: Vector3) -> void:
	var from := body.global_position
	_streak_node.global_position = from
	_streak.clear()
	_streak.emitting = true
	InkBurst.spawn(get_tree().current_scene, from + Vector3(0, 0.9, 0), 30)
	var tw := create_tween()
	tw.tween_method(set_dissolve, 0.0, 1.0, dissolve_time)
	tw.tween_callback(func(): _streak_node.global_position = from)
	tw.tween_property(_streak_node, "global_position", to, travel_time)
	tw.parallel().tween_property(body, "global_position", to, travel_time)
	tw.tween_callback(func():
		_streak.emitting = false
		InkBurst.spawn(get_tree().current_scene, to + Vector3(0, 0.9, 0), 22, false, 0.8))
	tw.tween_method(set_dissolve, 1.0, 0.0, reform_time)
	tw.tween_callback(func(): finished.emit())
