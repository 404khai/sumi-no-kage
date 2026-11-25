## The player: tight platformer movement (coyote time, jump buffer, variable
## jump height, wall slide/jump, dash) shared by all three classes, plus each
## class's weapon. Swap class any time with 1/2/3 or Q.
class_name PFHero
extends CharacterBody2D

signal died
signal hp_changed(hp: int, max_hp: int)
signal swapped(hero: Dictionary)

const GRAVITY := 1900.0
const FALL_MAX := 980.0
const COYOTE := 0.1
const BUFFER := 0.12
const DASH_SPEED := 820.0
const DASH_TIME := 0.16

var hero: Dictionary = PFHeroes.SWORDSMAN
var hp := 6
var facing := 1.0
var level: Node   # PFLevel
var fx: PFFx
var input_enabled := true
var bot: Callable          # optional scripted input (captures): returns Dictionary of pressed actions

var rig: PFRig
var _coyote := 0.0
var _buffer := 0.0
var _air_jumps := 0
var _dashes := 0
var _dash_t := 0.0
var _dash_dir := Vector2.ZERO
var _wall_lock := 0.0
var _invuln := 0.0
var _hurt_t := 0.0
var _action_t := 0.0
var _action_len := 0.0
var _cooldown := 0.0
var _combo := 0
var _combo_window := 0.0
var _hit_this_swing: Array = []
var _draw := 0.0
var _hover := 0.0
var _hand := 0
var _held := {}
var _prev_held := {}


func _ready() -> void:
	collision_layer = PFShot.HERO
	collision_mask = PFShot.WORLD
	floor_snap_length = 6.0
	var shape := CollisionShape2D.new()
	var cap := CapsuleShape2D.new()
	cap.radius = 13.0
	cap.height = 66.0
	shape.shape = cap
	shape.position = Vector2(0, -33)
	add_child(shape)
	rig = PFRig.new()
	rig.scale = Vector2(0.95, 0.95)
	add_child(rig)
	set_hero(hero, false)


func set_hero(h: Dictionary, burst := true) -> void:
	var ratio := float(hp) / float(hero.hp)
	hero = h
	hp = maxi(1, roundi(ratio * h.hp)) if burst else h.hp
	rig.set_hero(h)
	_action_t = 0.0
	rig.action = ""
	if burst and fx:
		fx.splat(global_position + Vector2(0, -36), h.body, 22, 360.0, 5.0)
		fx.ring(global_position + Vector2(0, -36), h.glow, 70.0)
	hp_changed.emit(hp, h.hp)
	swapped.emit(h)


# ------------------------------------------------------------------ input

func _sample_input() -> void:
	_prev_held = _held
	if bot.is_valid():
		_held = bot.call()
		return
	_held = {}
	if not input_enabled:
		return
	for a in ["pf_left", "pf_right", "pf_up", "pf_down", "pf_jump", "pf_attack", "pf_special", "pf_dash"]:
		if Input.is_action_pressed(a):
			_held[a] = true


func _down(a: String) -> bool:
	return _held.has(a)


func _pressed(a: String) -> bool:
	return _held.has(a) and not _prev_held.has(a)


func _released(a: String) -> bool:
	return _prev_held.has(a) and not _held.has(a)


# ------------------------------------------------------------------ movement

func _physics_process(delta: float) -> void:
	_sample_input()
	_invuln = maxf(0.0, _invuln - delta)
	_hurt_t = maxf(0.0, _hurt_t - delta)
	_cooldown = maxf(0.0, _cooldown - delta)
	_combo_window = maxf(0.0, _combo_window - delta)
	_wall_lock = maxf(0.0, _wall_lock - delta)
	var x := float(_down("pf_right")) - float(_down("pf_left"))
	var on_floor := is_on_floor()
	if on_floor:
		_coyote = COYOTE
		_air_jumps = hero.air_jumps
		_dashes = hero.dashes
		_hover = 0.45
	else:
		_coyote -= delta
	_buffer = BUFFER if _pressed("pf_jump") else _buffer - delta

	if _dash_t > 0.0:
		_dash_t -= delta
		velocity = _dash_dir * DASH_SPEED
		if hero.id == "swordsman":
			_melee_hits(Vector2(0, -34), 46.0, 1, false)
		if _dash_t <= 0.0:
			velocity *= 0.45
	else:
		var accel := 3200.0 if on_floor else 2000.0
		if _hurt_t <= 0.0 and _wall_lock <= 0.0:
			velocity.x = move_toward(velocity.x, x * hero.speed, accel * delta)
		var g := GRAVITY * (0.55 if velocity.y < 0 and _down("pf_jump") else 1.0)
		var fall_max := FALL_MAX
		var wall := _wall_dir()
		if wall != 0 and not on_floor and velocity.y > 0 and x == wall:
			fall_max = 150.0
		if hero.glide and velocity.y > 0 and _down("pf_jump") and not on_floor:
			fall_max = 120.0
		velocity.y = minf(velocity.y + g * delta, fall_max)
		if _buffer > 0.0:
			if _coyote > 0.0:
				_jump(hero.jump)
			elif wall != 0:
				velocity = Vector2(-wall * hero.speed * 1.25, -hero.jump * 0.92)
				facing = -wall
				_wall_lock = 0.14
				_buffer = 0.0
				_puff(Vector2(wall * 12, -30))
			elif _air_jumps > 0:
				_air_jumps -= 1
				_jump(hero.jump * 0.88)
				if fx:
					fx.ring(global_position, hero.glow, 34.0, 0.25)
		if _pressed("pf_dash") and _dashes > 0:
			_dashes -= 1
			var dy := float(_down("pf_down")) - float(_down("pf_up"))
			_dash_dir = Vector2(x if x != 0 else facing, dy * 0.8).normalized()
			_dash_t = DASH_TIME
			_invuln = maxf(_invuln, DASH_TIME)
			_hit_this_swing.clear()
			if fx:
				fx.splat(global_position + Vector2(0, -30), PFHeroes.INK, 10, 200.0, 4.0)
	if x != 0 and _action_t <= 0.0 and _wall_lock <= 0.0:
		facing = signf(x)
	_weapon(delta)
	var was_air := not on_floor
	var vy := velocity.y
	move_and_slide()
	if was_air and is_on_floor() and vy > 500.0:
		_puff(Vector2.ZERO)
	_animate(x)


func _jump(v: float) -> void:
	velocity.y = -v
	_coyote = 0.0
	_buffer = 0.0
	_puff(Vector2.ZERO)


func _puff(off: Vector2) -> void:
	if fx:
		fx.splat(global_position + off, Color(PFHeroes.INK, 0.8), 6, 140.0, 3.0)


func _wall_dir() -> int:
	if is_on_floor():
		return 0
	for d in [1, -1]:
		if test_move(global_transform, Vector2(d * 3, 0)):
			return d
	return 0


# ------------------------------------------------------------------ weapons

func _aim() -> float:
	if _down("pf_up"):
		return -PI * 0.5
	if _down("pf_down") and not is_on_floor():
		return PI * 0.5
	return 0.0


func _weapon(delta: float) -> void:
	if _action_t > 0.0:
		_action_t = maxf(0.0, _action_t - delta)
		rig.action_t = 1.0 - _action_t / _action_len
		if rig.action == "slash":
			_slash_hits()
		if _action_t <= 0.0 and rig.action != "draw":
			rig.action = ""
	match hero.id:
		"swordsman":
			if _pressed("pf_attack") and _cooldown <= 0.0:
				_combo = (_combo + 1) % 3 if _combo_window > 0.0 else 0
				_combo_window = 0.45
				_start_action("slash", 0.2)
				_cooldown = 0.22 if _combo < 2 else 0.34
				rig.combo = _combo
				_hit_this_swing.clear()
				var aim := _aim()
				rig.aim = aim
				if fx:
					var at := global_position + Vector2(facing * 8, -38)
					fx.slash(at, aim, facing, hero.glow, 52.0 if _combo < 2 else 64.0, 2.6)
		"gunslinger":
			if _down("pf_attack") and _cooldown <= 0.0:
				_fire_pistol()
			elif not _down("pf_attack") and rig.action == "shoot" and _action_t <= 0.0:
				rig.action = ""
		"archer":
			if _down("pf_attack"):
				if rig.action != "draw":
					rig.action = "draw"
					_draw = 0.0
				_draw = minf(1.0, _draw + delta * 1.6)
				rig.draw_amount = _draw
				rig.aim = _aim() if _aim() != 0.0 else (-0.35 if _down("pf_up") else 0.0)
				rig.action_t = _draw
			elif rig.action == "draw":
				_loose_arrow()
				rig.action = ""
	if _pressed("pf_special"):
		_special()


func _start_action(a: String, length: float) -> void:
	rig.action = a
	_action_len = length
	_action_t = length
	rig.action_t = 0.0


func _slash_hits() -> void:
	var aim := rig.aim
	var off := Vector2(cos(aim) * facing, sin(aim)) * 30.0 + Vector2(0, -36)
	var hit := _melee_hits(off, 52.0 if _combo < 2 else 62.0, 2 if _combo == 2 else 1, true)
	if hit and aim > 1.0 and not is_on_floor():
		velocity.y = -hero.jump * 0.75    # pogo off whatever we struck below
		_dashes = hero.dashes


func _melee_hits(off: Vector2, radius: float, dmg: int, knock: bool) -> bool:
	var center := global_position + off
	var any := false
	for e in get_tree().get_nodes_in_group("pf_enemy"):
		if e in _hit_this_swing or not is_instance_valid(e):
			continue
		var c: Vector2 = e.hit_center() if e.has_method("hit_center") else e.global_position + Vector2(0, -20)
		if c.distance_to(center) < radius + e.radius:
			_hit_this_swing.append(e)
			e.hurt(dmg, Vector2(facing, -0.3).normalized() * (1.0 if knock else 0.4), self)
			any = true
			if fx:
				fx.kick(6.0)
	return any


func _fire_pistol() -> void:
	var aim := _aim()
	_start_action("shoot", 0.12)
	rig.aim = aim
	_cooldown = 0.11
	_hand = 1 - _hand
	rig.muzzle = 1.0
	rig.muzzle_hand = _hand
	var dir := Vector2(cos(aim) * facing, sin(aim)).rotated(randf_range(-0.04, 0.04))
	var origin := global_position + Vector2(facing * 26.0 * cos(aim), -40 + sin(aim) * 26.0 + _hand * 4.0)
	_spawn_shot(origin, dir * 1300.0, 1, "bullet", hero.glow, false, 0.0)
	if aim > 1.0 and not is_on_floor() and _hover > 0.0:
		velocity.y = minf(velocity.y, -160.0)   # recoil hover
		_hover -= 0.11
	elif aim == 0.0 and not is_on_floor():
		velocity.x -= facing * 30.0


func _loose_arrow() -> void:
	var full := _draw >= 0.99
	var aim := rig.aim
	var dir := Vector2(cos(aim) * facing, sin(aim))
	var spd := lerpf(700.0, 1500.0, _draw)
	_spawn_shot(global_position + Vector2(facing * 20, -42), dir * spd, 3 if full else 1, "arrow",
		hero.glow, full, 900.0 * (1.0 - _draw * 0.8))
	if full and fx:
		fx.ring(global_position + Vector2(facing * 30, -42), hero.glow, 40.0, 0.25)
	_draw = 0.0
	_cooldown = 0.15


func _special() -> void:
	# Q is class swap; "special" is a class move:
	match hero.id:
		"swordsman":   # rising slash
			if _cooldown <= 0.0:
				velocity.y = -hero.jump * 0.8
				rig.aim = -PI * 0.5
				_combo = 1
				rig.combo = 1
				_start_action("slash", 0.26)
				_hit_this_swing.clear()
				_cooldown = 0.5
				if fx:
					fx.slash(global_position + Vector2(0, -50), -PI * 0.5, facing, hero.glow, 60.0, 3.2)
		"gunslinger":   # fan of five shots
			if _cooldown <= 0.0:
				for i in 5:
					var a := (i - 2) * 0.14
					_spawn_shot(global_position + Vector2(facing * 24, -40), Vector2(facing, 0).rotated(a * facing) * 1200.0,
						1, "bullet", hero.glow, false, 0.0)
				velocity.x -= facing * 380.0
				_start_action("shoot", 0.25)
				rig.muzzle = 1.0
				_cooldown = 0.7
				if fx:
					fx.kick(8.0)
		"archer":   # volley: three arrows arcing up
			if _cooldown <= 0.0:
				for i in 3:
					var a := -0.5 - i * 0.18
					_spawn_shot(global_position + Vector2(facing * 16, -46), Vector2(cos(a) * facing, sin(a)) * 1000.0, 1,
						"arrow", hero.glow, false, 1300.0)
				_cooldown = 0.6


func _spawn_shot(at: Vector2, v: Vector2, dmg: int, kind: String, col: Color, pierce: bool, grav: float) -> void:
	var s := PFShot.new()
	s.vel = v
	s.damage = dmg
	s.kind = kind
	s.color = col
	s.pierce = pierce
	s.gravity = grav
	s.fx = fx
	s.mask = PFShot.ENEMY
	get_parent().add_child(s)
	s.global_position = at


# ------------------------------------------------------------------ damage

func hurt(dmg: int, dir: Vector2, _src: Object = null) -> void:
	if _invuln > 0.0 or hp <= 0:
		return
	hp -= dmg
	_invuln = 1.0
	_hurt_t = 0.22
	velocity = Vector2(signf(dir.x) if dir.x != 0 else -facing, -0.6).normalized() * 520.0
	rig.flash = 1.0
	if fx:
		fx.splat(global_position + Vector2(0, -36), hero.body, 16, 340.0, 4.5)
		fx.kick(10.0)
	hp_changed.emit(hp, hero.hp)
	if hp <= 0:
		died.emit()


func heal_full() -> void:
	hp = hero.hp
	hp_changed.emit(hp, hero.hp)


func _animate(x: float) -> void:
	rig.scale.x = absf(rig.scale.x) * facing
	rig.grounded = is_on_floor()
	rig.speed_ratio = clampf(absf(velocity.x) / hero.speed, 0.0, 1.0)
	if _hurt_t > 0.0:
		rig.state = "hurt"
	elif _dash_t > 0.0:
		rig.state = "dash"
	elif is_on_floor():
		rig.state = "run" if absf(velocity.x) > 30.0 and x != 0 else "idle"
	elif _wall_dir() != 0 and velocity.y > 0 and x == _wall_dir():
		rig.state = "wall"
	else:
		rig.state = "jump" if velocity.y < 0 else "fall"
	rig.visible = _invuln <= 0.0 or _dash_t > 0.0 or int(_invuln * 20.0) % 2 == 0
