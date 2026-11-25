## Bullets, arrows and enemy ink bolts. Ray-swept each frame against the world
## (layer 1) and whatever bodies `mask` names, so fast shots never tunnel.
class_name PFShot
extends Node2D

const WORLD := 1
const HERO := 2
const ENEMY := 4

var vel := Vector2.ZERO
var gravity := 0.0
var damage := 1
var mask := ENEMY
var pierce := false
var kind := "bullet"     # bullet arrow bolt
var color := Color.WHITE
var life := 1.4
var fx: PFFx
var _hit: Array[RID] = []
var _trail: Array[Vector2] = []


func _physics_process(delta: float) -> void:
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	vel.y += gravity * delta
	var from := global_position
	var to := from + vel * delta
	var space := get_world_2d().direct_space_state
	while true:
		var q := PhysicsRayQueryParameters2D.create(from, to, WORLD | mask, _hit)
		var r := space.intersect_ray(q)
		if r.is_empty():
			break
		var col: Object = r.collider
		if col.has_method("hurt"):
			col.hurt(damage, vel.normalized(), self)
			if fx:
				fx.splat(r.position, color, 6, 220.0, 3.0)
			if pierce:
				_hit.append(r.rid)
				continue
		else:
			if fx:
				fx.splat(r.position, color, 5, 160.0, 2.5)
				if kind != "bullet":
					fx.stain(r.position, Color(color, 0.5), 7.0)
		queue_free()
		return
	global_position = to
	rotation = vel.angle()
	_trail.push_front(global_position)
	if _trail.size() > 7:
		_trail.pop_back()
	queue_redraw()


func _draw() -> void:
	var back := PackedVector2Array()
	for p in _trail:
		back.append((p - global_position).rotated(-rotation))
	match kind:
		"bullet":
			if back.size() > 1:
				draw_line(Vector2.ZERO, back[back.size() - 1], Color(color, 0.35), 5.0)
			draw_line(Vector2(-10, 0), Vector2(5, 0), PFHeroes.INK, 6.0)
			draw_line(Vector2(-8, 0), Vector2(6, 0), color, 3.0)
			draw_circle(Vector2(5, 0), 2.0, Color.WHITE)
		"arrow":
			if back.size() > 1:
				draw_polyline(back, Color(color, 0.4), 3.0 if pierce else 1.5)
			draw_line(Vector2(-26, 0), Vector2(4, 0), PFHeroes.INK, 3.5)
			draw_line(Vector2(-24, 0), Vector2(2, 0), Color.WHITE, 1.4)
			draw_colored_polygon(PackedVector2Array([Vector2(10, 0), Vector2(0, -4), Vector2(0, 4)]), color)
			draw_line(Vector2(-26, 0), Vector2(-20, -4), color, 1.6)
			draw_line(Vector2(-26, 0), Vector2(-20, 4), color, 1.6)
			if pierce:
				draw_circle(Vector2(6, 0), 7.0, Color(color, 0.35))
		_:
			draw_circle(Vector2.ZERO, 8.0, PFHeroes.INK)
			draw_circle(Vector2.ZERO, 5.0, color)
			if back.size() > 1:
				draw_polyline(back, Color(PFHeroes.INK, 0.6), 6.0)
