## Mini-boss: the Oni Captain, who holds the mine passage. Big, slow, honest:
## every attack is telegraphed (club raised, glowing) and leaves a recovery
## window. Slams send ink shockwaves along the floor (jump them); every few
## attacks he leaps at you instead. Below half health he speeds up.
class_name PFOni
extends CharacterBody2D

signal defeated

const NAME := "鬼の頭  ONI CAPTAIN"

var hero: PFHero
var fx: PFFx
var max_hp := 24
var hp := 24
var radius := 34.0
var active := false
var rig: PFRig
var _dir := -1.0
var _state := "idle"
var _state_t := 0.0
var _attacks := 0
var _home := Vector2.ZERO
var _knock := 0.0


func _ready() -> void:
	add_to_group("pf_enemy")
	collision_layer = PFShot.ENEMY
	collision_mask = PFShot.WORLD
	var s := CollisionShape2D.new()
	var cap := CapsuleShape2D.new()
	cap.radius = 26.0
	cap.height = 120.0
	s.shape = cap
	s.position = Vector2(0, -60)
	add_child(s)
	rig = PFRig.new()
	rig.set_hero(PFHeroes.ONI)
	rig.scale = Vector2(1.9, 1.9)
	add_child(rig)
	_home = global_position


func reset() -> void:
	hp = max_hp
	active = false
	_state = "idle"
	global_position = _home
	velocity = Vector2.ZERO


func hit_center() -> Vector2:
	return global_position + Vector2(0, -64)


func phase2() -> bool:
	return hp <= max_hp / 2


func _physics_process(delta: float) -> void:
	_state_t -= delta
	_knock = move_toward(_knock, 0.0, 1600.0 * delta)
	velocity.y = minf(velocity.y + 1900.0 * delta, 1100.0)
	var to := hero.global_position - global_position if hero else Vector2.ZERO
	var spd := 1.3 if phase2() else 1.0
	match _state:
		"idle":
			velocity.x = 0.0
			if active:
				_go("walk", 0.6)
		"walk":
			_dir = signf(to.x) if absf(to.x) > 6.0 else _dir
			velocity.x = _dir * 95.0 * spd
			if _state_t <= 0.0 and absf(to.x) < 150.0:
				_go("windup", 0.6 / spd)
			elif _state_t <= -2.5 or (_attacks % 3 == 2 and _state_t <= 0.0):
				_go("leap", 0.0)
				velocity = Vector2(clampf(to.x * 1.3, -520, 520), -780)
				_attacks += 1
		"windup":
			velocity.x = 0.0
			if _state_t <= 0.0:
				_slam()
		"leap":
			if is_on_floor() and velocity.y >= 0.0:
				_slam()
		"slam":
			velocity.x = 0.0
			if _state_t <= 0.0:
				_go("recover", 0.85 / spd)
		"recover":
			velocity.x = 0.0
			if _state_t <= 0.0:
				_go("walk", 0.4)
	velocity.x += _knock
	move_and_slide()
	_animate()


func _go(s: String, t: float) -> void:
	_state = s
	_state_t = t


func _slam() -> void:
	_go("slam", 0.28)
	_attacks += 1
	var impact := global_position + Vector2(_dir * 90.0, 0)
	if hero.global_position.distance_to(impact + Vector2(0, -30)) < 95.0:
		hero.hurt(1, Vector2(_dir, -0.6), self)
	if fx:
		fx.splat(impact, PFHeroes.INK, 30, 520.0, 6.0)
		fx.ring(impact + Vector2(0, -10), PFHeroes.SHU, 110.0, 0.4)
		fx.stain(impact + Vector2(0, -2), PFHeroes.INK, 40.0)
		fx.kick(14.0)
	for d in ([-1.0, 1.0] if phase2() else [_dir]):
		var w := Wave.new()
		w.dir = d
		w.hero = hero
		get_parent().add_child(w)
		w.global_position = impact


func hurt(dmg: int, dir: Vector2, _src: Object = null) -> void:
	if not active or hp <= 0:
		return
	hp -= dmg
	rig.flash = 1.0
	_knock = signf(dir.x) * 60.0
	if fx:
		fx.splat(hit_center(), PFHeroes.INK, 8, 280.0, 4.0)
	if hp <= 0:
		if fx:
			for i in 4:
				fx.splat(hit_center() + Vector2(randf_range(-30, 30), randf_range(-40, 40)), PFHeroes.INK, 30, 600.0, 7.0)
			fx.splat(hit_center(), PFHeroes.SHU, 20, 400.0, 5.0)
			fx.stain(global_position, PFHeroes.INK, 90.0)
			fx.kick(20.0)
		defeated.emit()
		queue_free()


func _animate() -> void:
	rig.scale.x = absf(rig.scale.x) * _dir
	rig.grounded = is_on_floor()
	rig.speed_ratio = clampf(absf(velocity.x) / 160.0, 0.0, 1.0)
	rig.state = "run" if _state == "walk" else ("jump" if _state == "leap" else "idle")
	rig.action = ""
	match _state:
		"windup":
			rig.action = "windup"
		"slam":
			rig.action = "slam"
			rig.action_t = 1.0 - clampf(_state_t / 0.28, 0.0, 1.0)


## Ink shockwave that runs along the floor from a slam. Jump it.
class Wave extends Node2D:
	var dir := 1.0
	var hero: PFHero
	var life := 1.5
	var _hit := false

	func _process(delta: float) -> void:
		life -= delta
		position.x += dir * 430.0 * delta
		if life <= 0.0:
			queue_free()
			return
		if not _hit and hero and absf(hero.global_position.x - global_position.x) < 24.0 \
				and hero.global_position.y > global_position.y - 34.0 and absf(hero.global_position.y - global_position.y) < 60.0:
			_hit = true
			hero.hurt(1, Vector2(dir, -1), self)
		queue_redraw()

	func _draw() -> void:
		var k := clampf(life / 1.5, 0.0, 1.0)
		var h := 34.0 * k + 8.0
		var crest := PackedVector2Array([Vector2(-dir * 30, 0), Vector2(-dir * 6, -h * 0.7), Vector2(dir * 4, -h),
			Vector2(dir * 14, -h * 0.4), Vector2(dir * 18, 0)])
		draw_colored_polygon(crest, Color(PFHeroes.INK, 0.9))
		draw_line(Vector2(dir * 4, -h), Vector2(dir * 12, -h - 8), PFHeroes.SHU, 2.5)
		for i in 3:
			draw_circle(Vector2(-dir * (14 + i * 12), -4 - i * 3), 3.0 - i * 0.6, Color(PFHeroes.INK, 0.6))
