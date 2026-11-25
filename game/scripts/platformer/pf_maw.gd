## Final boss: Nurekuchi 濡れ口, the Drowned Maw, a vast mouth living in the ink
## pool at the bottom of the mine. The loop: it sinks, a ripple stalks your x
## along the pool (tell), it bursts up in a bite, then it hangs open with its
## eye exposed. That is the window to hit it. Below half health it spits ink
## when it surfaces, stalks faster, and calls wisps once.
class_name PFMaw
extends StaticBody2D

signal defeated
signal summon(at: Vector2)

const NAME := "濡れ口  NUREKUCHI, THE DROWNED MAW"
const BITE_H := 250.0

var hero: PFHero
var fx: PFFx
var max_hp := 40
var hp := 40
var radius := 62.0
var active := false
var pool := Rect2()        # world-space pool surface (x range, y = surface)
var _state := "under"
var _state_t := 1.0
var _x := 0.0
var _rise := 0.0           # 0 = hidden, 1 = full bite height
var _flash := 0.0
var _t := 0.0
var _summoned := false
var _shape: CollisionShape2D


func _ready() -> void:
	add_to_group("pf_enemy")
	collision_layer = PFShot.ENEMY
	_shape = CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = radius
	_shape.shape = c
	add_child(_shape)
	_x = pool.get_center().x
	reset()


func reset() -> void:
	hp = max_hp
	active = false
	_state = "under"
	_state_t = 1.2
	_rise = 0.0
	_summoned = false


func exposed() -> bool:
	return _state in ["bite", "open"]


func phase2() -> bool:
	return hp <= max_hp / 2


func hit_center() -> Vector2:
	return Vector2(_x, pool.position.y - BITE_H * _rise + 70.0)


func _physics_process(delta: float) -> void:
	_t += delta
	_flash = maxf(0.0, _flash - delta * 5.0)
	global_position = hit_center()
	_shape.disabled = not exposed()
	if not active:
		queue_redraw()
		return
	_state_t -= delta
	match _state:
		"under":
			_rise = move_toward(_rise, 0.0, delta * 3.0)
			if _state_t <= 0.0:
				_go("stalk", 0.6 if phase2() else 0.95)
		"stalk":
			var target := clampf(hero.global_position.x, pool.position.x + 50.0, pool.end.x - 50.0)
			_x = move_toward(_x, target, delta * (520.0 if phase2() else 380.0))
			if _state_t <= 0.0:
				_go("bite", 0.32)
				if fx:
					fx.splat(Vector2(_x, pool.position.y), PFHeroes.INK, 30, 640.0, 6.0)
					fx.kick(10.0)
				if phase2():
					_spit()
				if phase2() and not _summoned:
					_summoned = true
					summon.emit(Vector2(pool.position.x + 120.0, pool.position.y - 300.0))
					summon.emit(Vector2(pool.end.x - 120.0, pool.position.y - 300.0))
		"bite":
			_rise = move_toward(_rise, 1.0, delta * 5.0)
			var top := pool.position.y - BITE_H * _rise
			var hp_pos := hero.global_position
			if absf(hp_pos.x - _x) < 78.0 and hp_pos.y > top - 20.0 and hp_pos.y < pool.position.y + 20.0:
				hero.hurt(2, Vector2(signf(hp_pos.x - _x), -1.0), self)
			if _state_t <= 0.0:
				_go("open", 1.9 if not phase2() else 1.5)
		"open":
			_rise = move_toward(_rise, 0.48, delta * 1.2)
			if _state_t <= 0.0:
				_go("dive", 0.4)
		"dive":
			_rise = move_toward(_rise, 0.0, delta * 3.0)
			if _state_t <= 0.0:
				_go("under", 0.9 if phase2() else 1.3)
	queue_redraw()


func _go(s: String, t: float) -> void:
	_state = s
	_state_t = t


func _spit() -> void:
	for i in 3:
		var s := PFShot.new()
		s.vel = Vector2((i - 1) * 260.0, -760.0)
		s.gravity = 1200.0
		s.kind = "bolt"
		s.color = PFHeroes.SHU
		s.mask = PFShot.HERO
		s.fx = fx
		s.life = 3.0
		get_parent().add_child(s)
		s.global_position = Vector2(_x, pool.position.y - 120.0)


func hurt(dmg: int, dir: Vector2, _src: Object = null) -> void:
	if not active or not exposed() or hp <= 0:
		return
	hp -= dmg
	_flash = 1.0
	if fx:
		fx.splat(hit_center() + Vector2(0, -40), PFHeroes.INK, 10, 300.0, 4.5)
	if hp <= 0:
		if fx:
			for i in 6:
				fx.splat(hit_center() + Vector2(randf_range(-60, 60), randf_range(-80, 40)), PFHeroes.INK, 30, 700.0, 8.0)
			fx.splat(hit_center(), PFHeroes.SHU, 30, 500.0, 6.0)
			fx.kick(24.0)
		defeated.emit()
		queue_free()


func _draw() -> void:
	var ink := PFHeroes.INK
	var surf := pool.position.y - global_position.y   # local y of the pool surface
	# stalking ripple: the tell
	if _state == "stalk" or _state == "under":
		var k := 1.0 if _state == "stalk" else 0.3
		for i in 3:
			var w := 40.0 + i * 26.0 + sin(_t * 8.0 + i) * 6.0
			draw_arc(Vector2(0, surf), w, PI, TAU, 20, Color(ink, 0.6 * k), 3.0)
		if _state == "stalk":
			draw_line(Vector2(-6, surf - 16), Vector2(6, surf - 16), PFHeroes.SHU, 3.0)
	if _rise <= 0.02:
		return
	var head_h := BITE_H * _rise + 40.0
	var top := surf - head_h
	var white := Color(1, 1, 1, _flash)
	var open := 0.75 if _state == "open" else (0.35 if _state == "bite" else 0.15)
	var gape := 70.0 * open
	# body column: a thick ink trunk out of the pool
	var body := PackedVector2Array([Vector2(-80, surf + 10), Vector2(-66, top + 70), Vector2(66, top + 70),
		Vector2(80, surf + 10)])
	draw_colored_polygon(body, ink)
	# upper jaw (a hooked beak-like dome) and lower jaw, split by the gape
	var upper := PackedVector2Array([Vector2(-78, top + 80), Vector2(-60, top + 10), Vector2(-10, top - 18),
		Vector2(40, top - 6), Vector2(84, top + 40), Vector2(92, top + 80 - gape * 0.2)])
	var lower := PackedVector2Array([Vector2(-74, top + 84 + gape), Vector2(90, top + 84 + gape * 0.7),
		Vector2(72, top + 150 + gape), Vector2(-70, top + 150 + gape)])
	# mouth interior (vermilion gums) behind the jaws
	draw_colored_polygon(PackedVector2Array([Vector2(-70, top + 70), Vector2(88, top + 70), Vector2(88, top + 92 + gape),
		Vector2(-70, top + 92 + gape)]), Color(0.45, 0.06, 0.05))
	for i in 7:
		var x := -60.0 + i * 22.0
		draw_colored_polygon(PackedVector2Array([Vector2(x - 8, top + 76), Vector2(x + 8, top + 76),
			Vector2(x + 1, top + 76 + 22 + gape * 0.15)]), PFHeroes.PAPER)
		draw_colored_polygon(PackedVector2Array([Vector2(x - 6, top + 88 + gape), Vector2(x + 7, top + 88 + gape),
			Vector2(x + 2, top + 68 + gape * 0.85)]), PFHeroes.PAPER)
	draw_colored_polygon(upper, ink.lerp(Color.WHITE, _flash * 0.5))
	draw_colored_polygon(lower, ink.lerp(Color.WHITE, _flash * 0.5))
	# ridge spines + dry-brush sheen
	for i in 5:
		var p := Vector2(-50 + i * 24, top - 8 + absf(i - 2) * 6.0)
		draw_colored_polygon(PackedVector2Array([p + Vector2(-7, 6), p + Vector2(2, -22 - i % 2 * 8), p + Vector2(8, 6)]), ink)
	draw_polyline(PackedVector2Array([Vector2(-50, top + 14), Vector2(-10, top - 6), Vector2(30, top + 2)]),
		Color(PFHeroes.PAPER, 0.18), 3.0)
	# the eye: shut when hidden, wide and glowing when open (hit me)
	var eye := Vector2(30, top + 30)
	if exposed():
		draw_circle(eye, 17.0, PFHeroes.PAPER)
		draw_circle(eye + Vector2(3, 2), 8.0, PFHeroes.SHU)
		draw_circle(eye + Vector2(3, 2), 3.0, ink)
		if _state == "open":
			draw_arc(eye, 26.0 + sin(_t * 10.0) * 3.0, 0, TAU, 24, Color(PFHeroes.SHU, 0.7), 2.5)
	else:
		draw_line(eye + Vector2(-14, 0), eye + Vector2(14, 2), PFHeroes.PAPER, 2.0)
	# ink running off it back into the pool
	for i in 5:
		var x := -70.0 + i * 34.0
		var len := 20.0 + fmod(_t * 60.0 + i * 37.0, 80.0)
		draw_line(Vector2(x, top + 150 + gape), Vector2(x, top + 150 + gape + len), Color(ink, 0.8), 5.0)
	if _flash > 0.0:
		draw_circle(Vector2(0, top + 80), 90.0, Color(white, _flash * 0.25))
