## Level machinery: swinging maces, chain lifts and seal gates. Each one is a
## small inner class so the level can spawn them straight from map markers.
class_name PFHazards
extends RefCounted


## A spiked ink ball on a chain, swinging from a ceiling anchor (map "M").
class Mace extends Node2D:
	var hero: PFHero
	var length := 190.0
	var amp := 1.15
	var speed := 1.7
	var phase := 0.0
	var _t := 0.0

	func ball() -> Vector2:
		var a := sin(_t * speed + phase) * amp
		return Vector2(sin(a), cos(a)) * length

	func _process(delta: float) -> void:
		_t += delta
		if hero and hero.hp > 0:
			var b := global_position + ball()
			if b.distance_to(hero.global_position + Vector2(0, -32)) < 40.0:
				hero.hurt(1, (hero.global_position - b).normalized(), self)
		queue_redraw()

	func _draw() -> void:
		var ink := PFHeroes.INK
		var b := ball()
		draw_rect(Rect2(-10, -6, 20, 10), ink)
		var links := int(length / 12.0)
		for i in links:
			var p := b * (float(i) / links)
			draw_arc(p, 4.0, 0, TAU, 8, Color(ink, 0.9), 2.0)
		var spikes := PackedVector2Array()
		for i in 16:
			var a := TAU * i / 16 + _t * 0.4
			spikes.append(b + Vector2(cos(a), sin(a)) * (30.0 if i % 2 == 0 else 19.0))
		draw_colored_polygon(spikes, ink)
		draw_circle(b, 17.0, Color(0.18, 0.17, 0.17))
		draw_circle(b + Vector2(-5, -5), 4.0, Color(PFHeroes.PAPER, 0.25))
		draw_line(b + Vector2(-8, 3), b + Vector2(6, 6), PFHeroes.SHU, 2.0)


## A plank hung on chains that rides up/down ("v") or side to side ("h").
class Lift extends AnimatableBody2D:
	var travel := Vector2(0, 144)
	var period := 4.0
	var width := 144.0
	var _origin := Vector2.ZERO
	var _t := 0.0

	func _ready() -> void:
		collision_layer = PFShot.WORLD
		sync_to_physics = true
		_origin = position
		var s := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(width, 14)
		s.shape = r
		s.position = Vector2(0, 7)
		s.one_way_collision = true
		add_child(s)

	func _physics_process(delta: float) -> void:
		_t += delta
		position = _origin + travel * (0.5 - 0.5 * cos(_t * TAU / period))
		queue_redraw()

	func _draw() -> void:
		var ink := PFHeroes.INK
		var h := width * 0.5
		# chains run up off-screen so the lift reads as hung from the dark
		for x in [-h + 10, h - 10]:
			var top := Vector2(x, -600)
			draw_line(top, Vector2(x, 0), Color(ink, 0.85), 2.0)
			for y in range(-600, 0, 14):
				draw_arc(Vector2(x, y), 3.0, 0, TAU, 6, Color(ink, 0.7), 1.5)
		draw_rect(Rect2(-h, 0, width, 12), Color(0.2, 0.19, 0.18))
		draw_line(Vector2(-h - 4, 1), Vector2(h + 4, 1), ink, 5.0)
		draw_line(Vector2(-h + 6, 12), Vector2(h - 6, 12), Color(ink, 0.6), 2.0)
		draw_rect(Rect2(-6, 2, 12, 8), PFHeroes.SHU)


## A shimenawa-bound gate of ink bars (map "X" closes behind you in a boss
## arena; "Y" is a lid that stays shut until the boss falls).
class Gate extends StaticBody2D:
	var rect := Rect2()
	var vertical := true
	var closed := false:
		set(v):
			closed = v
			if _shape:
				_shape.set_deferred("disabled", not v)
			queue_redraw()
	var _shape: CollisionShape2D
	var _anim := 0.0

	func _ready() -> void:
		collision_layer = PFShot.WORLD
		_shape = CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = rect.size
		_shape.shape = r
		_shape.position = rect.get_center()
		_shape.disabled = not closed
		add_child(_shape)

	func _process(delta: float) -> void:
		_anim = move_toward(_anim, 1.0 if closed else 0.0, delta * 4.0)
		queue_redraw()

	func _draw() -> void:
		if _anim <= 0.0:
			return
		var ink := PFHeroes.INK
		if vertical:
			var bottom := rect.position.y + rect.size.y * _anim
			for x in [rect.position.x + 10, rect.get_center().x, rect.end.x - 10]:
				draw_line(Vector2(x, rect.position.y), Vector2(x, bottom), ink, 9.0)
			draw_line(Vector2(rect.position.x - 6, rect.position.y + 20), Vector2(rect.end.x + 6, rect.position.y + 26),
				Color(0.85, 0.8, 0.65), 6.0)
			for i in 3:
				var p := Vector2(rect.position.x + 8 + i * 14, rect.position.y + 30)
				draw_colored_polygon(PackedVector2Array([p, p + Vector2(8, 0), p + Vector2(4, 22)]), PFHeroes.PAPER)
		else:
			var r := Rect2(rect.position, Vector2(rect.size.x, rect.size.y * _anim))
			for x in range(int(r.position.x) + 8, int(r.end.x), 22):
				draw_line(Vector2(x, r.position.y), Vector2(x, r.end.y), ink, 8.0)
			draw_line(r.position + Vector2(0, 6), Vector2(r.end.x, r.position.y + 6), Color(0.85, 0.8, 0.65), 5.0)
			# paper ofuda seal in the middle
			var c := r.get_center()
			draw_rect(Rect2(c + Vector2(-10, -16), Vector2(20, 34)), PFHeroes.PAPER)
			draw_line(c + Vector2(0, -10), c + Vector2(0, 12), PFHeroes.SHU, 3.0)
			draw_line(c + Vector2(-6, -2), c + Vector2(6, -2), PFHeroes.SHU, 2.0)
