## Enemies for both sides of the portal. Same three behaviours, two skins:
##   crawler  patrols a ledge, turns at walls and drops   (ink oni  / tread bot)
##   flyer    bobs toward the hero when it gets close     (ink wisp / drone)
##   turret   fixed, lobs bolts at the hero               (shrine bell / sentry)
##   goon     ashigaru with a yari: patrols, spots you, telegraphs, lunges
##   bowgoon  ashigaru archer: holds a ledge, draws (telegraph), looses
class_name PFEnemy
extends CharacterBody2D

var kind := "crawler"
var theme := "ink"       # ink | neon
var hp := 3
var radius := 18.0
var hero: PFHero
var fx: PFFx
var _dir := -1.0
var _flash := 0.0
var _t := 0.0
var _home := Vector2.ZERO
var _fire := 1.5
var _knock := Vector2.ZERO
var rig: PFRig
var center_off := 0.0     # height of the body centre above the feet
var _state := "patrol"
var _state_t := 0.0


func _ready() -> void:
	add_to_group("pf_enemy")
	collision_layer = PFShot.ENEMY
	collision_mask = PFShot.WORLD
	center_off = radius
	if kind in ["goon", "bowgoon"]:
		radius = 16.0
		center_off = 30.0
		rig = PFRig.new()
		rig.set_hero(PFHeroes.GOON if kind == "goon" else PFHeroes.GOON_ARCHER)
		rig.scale = Vector2(0.95, 0.95)
		add_child(rig)
	var shape := CollisionShape2D.new()
	if rig:
		var cap := CapsuleShape2D.new()
		cap.radius = 13.0
		cap.height = 62.0
		shape.shape = cap
		shape.position = Vector2(0, -31)
	else:
		var c := CircleShape2D.new()
		c.radius = radius
		shape.shape = c
		shape.position = Vector2(0, -radius)
	add_child(shape)
	_home = global_position
	_t = randf() * 10.0
	match kind:
		"flyer": hp = 2
		"turret": hp = 4
		_: hp = 3


func hit_center() -> Vector2:
	return global_position + Vector2(0, -center_off)


func _physics_process(delta: float) -> void:
	_t += delta
	_flash = maxf(0.0, _flash - delta * 6.0)
	_knock = _knock.move_toward(Vector2.ZERO, 2400.0 * delta)
	match kind:
		"crawler":
			velocity.y = minf(velocity.y + 1900.0 * delta, 900.0)
			velocity.x = _dir * 70.0 + _knock.x
			if is_on_wall() or (is_on_floor() and not _ground_ahead()):
				_dir = -_dir
			move_and_slide()
		"flyer":
			var target := _home + Vector2(sin(_t * 0.9) * 60.0, sin(_t * 1.7) * 18.0)
			if hero and hero.global_position.distance_to(global_position) < 380.0:
				target = hero.global_position + Vector2(0, -60)
			velocity = (target - global_position).limit_length(140.0) * 1.2 + _knock
			move_and_slide()
		"turret":
			_fire -= delta
			if hero and _fire <= 0.0 and hero.global_position.distance_to(global_position) < 620.0:
				_fire = 2.2
				_shoot()
		"goon":
			_goon(delta)
		"bowgoon":
			_bowgoon(delta)
	if rig:
		_animate_rig()
	elif hero and hero.hp > 0:
		var hc := hero.global_position + Vector2(0, -32)
		if hc.distance_to(global_position + Vector2(0, -radius)) < radius + 18.0:
			hero.hurt(1, (hero.global_position - global_position).normalized(), self)
	queue_redraw()


func _goon(delta: float) -> void:
	_state_t -= delta
	velocity.y = minf(velocity.y + 1900.0 * delta, 900.0)
	var to := hero.global_position - global_position if hero else Vector2(9999, 0)
	var sees := absf(to.x) < 300.0 and absf(to.y) < 80.0 and hero.hp > 0
	match _state:
		"patrol", "chase":
			if sees:
				_dir = signf(to.x) if to.x != 0 else _dir
				_state = "chase"
				if absf(to.x) < 120.0:
					_set_state("windup", 0.45)
			else:
				_state = "patrol"
			var spd := 120.0 if _state == "chase" else 55.0
			velocity.x = _dir * spd
			if is_on_floor() and not _ground_ahead():
				velocity.x = 0.0
				if _state == "patrol":
					_dir = -_dir
			if is_on_wall() and _state == "patrol":
				_dir = -_dir
		"windup":
			velocity.x = -_dir * 20.0
			if _state_t <= 0.0:
				_set_state("thrust", 0.22)
		"thrust":
			velocity.x = _dir * 460.0 if _ground_ahead() else 0.0
			var tip := global_position + Vector2(_dir * 58.0, -36)
			if hero.global_position.distance_to(tip + Vector2(0, 8)) < 46.0:
				hero.hurt(1, Vector2(_dir, -0.4), self)
			if _state_t <= 0.0:
				_set_state("recover", 0.6)
		"recover":
			velocity.x = move_toward(velocity.x, 0.0, 2400.0 * delta)
			if _state_t <= 0.0:
				_state = "chase"
	velocity.x += _knock.x
	move_and_slide()


func _bowgoon(delta: float) -> void:
	_state_t -= delta
	velocity.y = minf(velocity.y + 1900.0 * delta, 900.0)
	velocity.x = _knock.x
	move_and_slide()
	if not hero or hero.hp <= 0:
		return
	var to := hero.global_position + Vector2(0, -36) - (global_position + Vector2(0, -42))
	_dir = signf(to.x) if absf(to.x) > 4.0 else _dir
	match _state:
		"patrol":
			if to.length() < 620.0:
				_set_state("draw", 0.85)
		"draw":
			if _state_t <= 0.0:
				var s := PFShot.new()
				s.vel = to.normalized() * 820.0 + Vector2(0, -to.length() * 0.18)
				s.gravity = 420.0
				s.kind = "arrow"
				s.color = PFHeroes.SHU
				s.mask = PFShot.HERO
				s.fx = fx
				s.life = 2.5
				get_parent().add_child(s)
				s.global_position = global_position + Vector2(_dir * 18.0, -42)
				_set_state("recover", 1.4)
		"recover":
			if _state_t <= 0.0:
				_state = "patrol"


func _set_state(s: String, t: float) -> void:
	_state = s
	_state_t = t


func _animate_rig() -> void:
	rig.scale.x = absf(rig.scale.x) * _dir
	rig.grounded = is_on_floor()
	rig.flash = maxf(rig.flash, _flash)
	rig.speed_ratio = clampf(absf(velocity.x) / 160.0, 0.0, 1.0)
	rig.state = "run" if absf(velocity.x) > 20.0 and _state in ["patrol", "chase"] else "idle"
	rig.action = ""
	match _state:
		"windup": rig.action = "windup"
		"thrust": rig.action = "thrust"
		"draw":
			rig.action = "draw"
			rig.draw_amount = clampf(1.0 - _state_t / 0.85, 0.0, 1.0)
			if hero:
				var to := hero.global_position - global_position
				rig.aim = clampf(atan2(to.y, absf(to.x)), -1.0, 1.0)


func _ground_ahead() -> bool:
	var space := get_world_2d().direct_space_state
	var from := global_position + Vector2(_dir * (radius + 4.0), -4)
	var q := PhysicsRayQueryParameters2D.create(from, from + Vector2(0, 30), PFShot.WORLD)
	return not space.intersect_ray(q).is_empty()


func _shoot() -> void:
	var s := PFShot.new()
	var to := hero.global_position + Vector2(0, -40) - (global_position + Vector2(0, -radius * 2))
	s.vel = to.normalized() * 380.0 + Vector2(0, -120)
	s.gravity = 260.0
	s.kind = "bolt"
	s.color = PFHeroes.SHU if theme == "ink" else Color(1.0, 0.2, 0.6)
	s.mask = PFShot.HERO
	s.fx = fx
	s.life = 3.0
	get_parent().add_child(s)
	s.global_position = global_position + Vector2(0, -radius * 2)


func hurt(dmg: int, dir: Vector2, _src: Object = null) -> void:
	hp -= dmg
	_flash = 1.0
	_knock = dir * (380.0 if not rig else 260.0)
	if rig and _state == "windup":
		_set_state("recover", 0.35)   # a hit interrupts the telegraph
	if fx:
		fx.splat(global_position + Vector2(0, -radius), _blood(), 8, 260.0, 3.5)
	if hp <= 0:
		if fx:
			fx.splat(global_position + Vector2(0, -radius), _blood(), 26, 420.0, 5.0)
			fx.stain(global_position + Vector2(0, -2), _blood(), radius * 1.4)
			fx.ring(global_position + Vector2(0, -radius), _blood(), radius * 3.0)
			fx.kick(7.0)
		queue_free()


func _blood() -> Color:
	return PFHeroes.INK if theme == "ink" else Color(0.95, 0.15, 0.6)


func _draw() -> void:
	if rig:
		if _state == "windup" or _state == "draw":
			# the "!" tell: a vermilion brush tick over the head
			var p := Vector2(0, -86)
			draw_line(p, p + Vector2(0, -16), PFHeroes.SHU, 4.0)
			draw_circle(p + Vector2(0, 6), 2.5, PFHeroes.SHU)
		return
	var c := Vector2(0, -radius)
	var white := Color(1, 1, 1, _flash)
	if theme == "ink":
		_draw_ink(c)
	else:
		_draw_neon(c)
	if _flash > 0.0:
		draw_circle(c, radius * 1.1, Color(white, _flash * 0.6))


func _blob(c: Vector2, r: float, n: int, wobble: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in n:
		var a := TAU * i / n
		var k := 1.0 + sin(a * 3.0 + _t * 4.0) * wobble + sin(a * 5.0 - _t * 3.0) * wobble * 0.5
		pts.append(c + Vector2(cos(a), sin(a)) * r * k)
	return pts


func _draw_ink(c: Vector2) -> void:
	var ink := PFHeroes.INK
	match kind:
		"crawler":   # ink oni: a slumped blot with a vermilion mask
			draw_colored_polygon(_blob(c + Vector2(0, 3), radius * 1.15, 16, 0.08), ink)
			for i in 4:
				var lx := (i - 1.5) * 9.0 + sin(_t * 9.0 + i) * 3.0
				draw_line(Vector2(lx, -4), Vector2(lx + _dir * 4.0, 0), ink, 4.0)
			var m := c + Vector2(_dir * 6.0, -3)
			draw_colored_polygon(PackedVector2Array([m + Vector2(-8, -6), m + Vector2(8, -6), m + Vector2(6, 6),
				m + Vector2(-6, 6)]), PFHeroes.SHU)
			draw_line(m + Vector2(-5, -1), m + Vector2(-1, 1), ink, 2.0)
			draw_line(m + Vector2(5, -1), m + Vector2(1, 1), ink, 2.0)
			draw_line(m + Vector2(-6, -6), m + Vector2(-9, -14), PFHeroes.PAPER, 2.5)
			draw_line(m + Vector2(6, -6), m + Vector2(9, -14), PFHeroes.PAPER, 2.5)
		"flyer":   # wisp: a drifting ink drop with a trailing tail
			draw_colored_polygon(_blob(c, radius * 0.85, 14, 0.12), ink)
			for i in 3:
				var p := c + Vector2(-sin(_t * 3.0 + i) * 6.0, radius * 0.8 + i * 7.0)
				draw_circle(p, 5.0 - i * 1.4, Color(ink, 0.8 - i * 0.2))
			draw_circle(c + Vector2(-4, -2), 3.0, PFHeroes.PAPER)
			draw_circle(c + Vector2(5, -2), 3.0, PFHeroes.PAPER)
		_:   # temple bell turret
			var top := c + Vector2(0, -radius * 0.6)
			draw_colored_polygon(PackedVector2Array([top + Vector2(-10, -8), top + Vector2(10, -8),
				top + Vector2(radius, radius * 1.6), top + Vector2(-radius, radius * 1.6)]), ink)
			draw_line(top + Vector2(-radius - 3, radius * 1.6), top + Vector2(radius + 3, radius * 1.6), ink, 4.0)
			draw_circle(top + Vector2(0, radius * 0.7), 5.0, PFHeroes.SHU)
			draw_line(top + Vector2(-8, 4), top + Vector2(8, 4), Color(PFHeroes.PAPER, 0.4), 1.5)


func _draw_neon(c: Vector2) -> void:
	var body := Color(0.09, 0.07, 0.16)
	var hot := Color(1.0, 0.2, 0.6)
	var cool := Color(0.3, 0.95, 1.0)
	match kind:
		"crawler":
			var pts := PackedVector2Array([c + Vector2(-radius, 10), c + Vector2(-radius * 0.7, -12),
				c + Vector2(radius * 0.7, -14), c + Vector2(radius, 10)])
			draw_colored_polygon(pts, body)
			draw_polyline(pts, cool, 2.0)
			draw_rect(Rect2(c + Vector2(-radius, 10), Vector2(radius * 2.0, 8)), PFHeroes.INK)
			for i in 4:
				draw_circle(c + Vector2(-radius + 4 + i * radius * 0.6, 14), 3.0, Color(cool, 0.8))
			draw_rect(Rect2(c + Vector2(_dir * 6.0 - 5, -6), Vector2(10, 5)), hot)
		"flyer":
			var pts := PackedVector2Array([c + Vector2(0, -radius), c + Vector2(radius, 0), c + Vector2(0, radius * 0.7),
				c + Vector2(-radius, 0)])
			draw_colored_polygon(pts, body)
			draw_polyline(pts + PackedVector2Array([pts[0]]), hot, 2.0)
			draw_line(c + Vector2(-radius - 8, -4 + sin(_t * 30.0) * 2.0), c + Vector2(radius + 8, -4 - sin(_t * 30.0) * 2.0),
				Color(cool, 0.7), 2.0)
			draw_circle(c, 4.0 + sin(_t * 8.0), hot)
		_:
			draw_rect(Rect2(c + Vector2(-radius, -radius * 0.2), Vector2(radius * 2, radius * 1.2)), body)
			draw_rect(Rect2(c + Vector2(-radius, -radius * 0.2), Vector2(radius * 2, radius * 1.2)), cool, false, 2.0)
			var aim := 0.0
			if hero:
				aim = (hero.global_position - global_position).angle()
			draw_line(c, c + Vector2(cos(aim), sin(aim)) * radius * 1.4, hot, 5.0)
			draw_circle(c, 6.0, hot)
