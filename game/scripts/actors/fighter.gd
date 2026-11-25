## Shared body for the player and enemies: model + weapon mount, health,
## posture/stagger, attacks driven by data/movesets.json, hit resolution.
class_name Fighter
extends CharacterBody3D

signal died(f: Fighter)
signal damaged(f: Fighter, amount: float)

enum State { MOVE, ATTACK, DODGE, BLOCK, HIT, STAGGER, DEAD }

const GRAVITY := 18.0
const RED_INK := preload("res://materials/vfx/M_Vfx_InkBlotRed.tres")

@export var max_health := 100.0
@export var team := 0                 # 0 player, 1 enemies
var health := 100.0
var posture := 0.0                    # reaches 1 -> stagger (finisher window)
var state := State.MOVE
var character: CharacterDefinition
var weapon: WeaponDefinition
var moves: Dictionary
var model: Node3D
var skeleton: Skeleton3D
var anim: AnimationPlayer
var mount: WeaponMount
var trails: Array[InkTrail] = []
var step_vfx: PhantomStepVFX
var attack_speed := 1.0               # enemies telegraph by swinging slower
var invulnerable := false

var _attack: Dictionary = {}
var _attack_t := 0.0
var _attack_hit_done := false
var _attack_len := 0.0
var _lunge_left := 0.0
var _state_t := 0.0
var _block_t := 0.0                    # time the block has been held (parry window)
var combo := 0


func setup(def: CharacterDefinition, w: WeaponDefinition) -> void:
	character = def
	health = max_health
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.38
	cap.height = 1.8
	col.shape = cap
	col.position.y = 0.9
	add_child(col)
	model = def.scene.instantiate()
	add_child(model)
	skeleton = model.find_children("*", "Skeleton3D", true, false)[0]
	anim = model.find_children("*", "AnimationPlayer", true, false)[0]
	mount = WeaponMount.new()
	mount.skeleton = skeleton
	model.add_child(mount)
	step_vfx = PhantomStepVFX.new()
	step_vfx.body = self
	add_child(step_vfx)
	equip(w)


func equip(w: WeaponDefinition) -> void:
	weapon = w
	moves = Game.moveset(w)
	for t in trails:
		t.queue_free()
	trails.clear()
	mount.equip(w, true)
	for i in mount.hands.size():
		var pts := mount.blade_points(i)
		if pts[0] == null or pts[1] == null:
			continue
		var tr := InkTrail.new()
		tr.base_node = pts[0]
		tr.tip_node = pts[1]
		tr.lifetime = w.trail_lifetime
		tr.width_scale = 2.2 if w.dual_wield else 1.1
		tr.emitting = false
		get_parent().add_child.call_deferred(tr)
		trails.append(tr)
	step_vfx._geometry.clear()
	step_vfx._collect(self)
	if state == State.MOVE:
		play(moves["stance"])


func play(clip: String, blend := 0.12, speed := 1.0) -> void:
	if anim.has_animation(clip):
		anim.play(clip, blend, speed)


func forward() -> Vector3:
	return model.global_basis.z.normalized()


func face(dir: Vector3, delta: float, rate := 14.0) -> void:
	dir.y = 0
	if dir.length() < 0.01:
		return
	var target := atan2(dir.x, dir.z)
	model.rotation.y = lerp_angle(model.rotation.y, target, clampf(rate * delta, 0, 1))


func can_act() -> bool:
	return state == State.MOVE or state == State.BLOCK


# ------------------------------------------------------------------ attacks
func start_attack(kind: String, target: Fighter = null) -> bool:
	if state == State.DEAD or state == State.HIT or state == State.STAGGER or state == State.DODGE:
		return false
	var data: Dictionary
	if kind == "light":
		var chain: Array = moves["light"]
		if state == State.ATTACK and _attack.get("_kind") == "light" and _attack_t >= float(_attack["hit"]):
			combo = (combo + 1) % chain.size()
		elif state == State.ATTACK:
			return false
		else:
			combo = 0
		data = chain[combo].duplicate()
	else:
		if state == State.ATTACK and _attack_t < float(_attack.get("cancel", 0.0)):
			return false
		data = (moves[kind] as Dictionary).duplicate()
	data["_kind"] = kind
	data["_target"] = target
	_attack = data
	_attack_t = 0.0
	_attack_hit_done = false
	_lunge_left = float(data["lunge"])
	var a := anim.get_animation(String(data["anim"])) if anim.has_animation(String(data["anim"])) else null
	_attack_len = (a.length if a else 0.8) / attack_speed
	state = State.ATTACK
	play(String(data["anim"]), 0.06, attack_speed)
	if target:
		face(target.global_position - global_position, 1.0, 100.0)
	for t in trails:
		t.clear()
		t.emitting = true
	return true


func _tick_attack(delta: float) -> void:
	_attack_t += delta
	var hit_t := float(_attack["hit"]) / attack_speed
	if _lunge_left > 0.0 and _attack_t < hit_t + 0.05:
		var step := minf(_lunge_left, float(_attack["lunge"]) * delta / maxf(hit_t, 0.1))
		_lunge_left -= step
		velocity.x = forward().x * step / delta
		velocity.z = forward().z * step / delta
	else:
		velocity.x = move_toward(velocity.x, 0, 30 * delta)
		velocity.z = move_toward(velocity.z, 0, 30 * delta)
	if not _attack_hit_done and _attack_t >= hit_t:
		_attack_hit_done = true
		_resolve_hit()
	if _attack_t >= hit_t + 0.15:
		for t in trails:
			t.emitting = false
	if _attack_t >= _attack_len:
		state = State.MOVE
		play(moves["stance"], 0.2)


func _resolve_hit() -> void:
	var reach := float(_attack["reach"])
	var half_arc := deg_to_rad(float(_attack["arc"]) * 0.5)
	var finisher: bool = _attack["_kind"] == "finisher"
	for n in get_tree().get_nodes_in_group("fighters"):
		var f := n as Fighter
		if f == self or f.team == team or f.state == State.DEAD:
			continue
		var to := f.global_position - global_position
		to.y = 0
		if to.length() > reach + 0.4:
			continue
		if half_arc < PI and forward().angle_to(to.normalized()) > half_arc:
			continue
		if finisher and f.state != State.STAGGER:
			continue
		f.receive_hit(self, float(_attack["damage"]), float(_attack["stagger"]), finisher)


func receive_hit(from: Fighter, damage: float, stagger: float, finisher := false) -> void:
	if state == State.DEAD or invulnerable:
		return
	var at := global_position + Vector3(0, 1.2, 0)
	if state == State.BLOCK and not finisher:
		var facing := forward().dot((from.global_position - global_position).normalized()) > 0.2
		if facing:
			if _block_t < 0.25:                      # parry: attacker is opened up
				from.stagger(2.2)
				InkBurst.spawn(get_tree().current_scene, at, 16, false, 0.6)
				return
			damage *= 0.2
			posture += stagger * 0.5
			InkBurst.spawn(get_tree().current_scene, at, 8, false, 0.4)
	health -= damage
	damaged.emit(self, damage)
	InkBurst.spawn(get_tree().current_scene, at, 24 if finisher else 14, true, 0.7 if finisher else 0.5)
	if health <= 0.0:
		die()
		return
	posture += stagger
	if posture >= 1.0:
		stagger(2.5)
	elif state != State.BLOCK and state != State.ATTACK:
		state = State.HIT
		_state_t = 0.0
		play("Act_Hit", 0.05)
	velocity += (global_position - from.global_position).normalized() * 3.0


func stagger(duration: float) -> void:
	if state == State.DEAD:
		return
	posture = 0.0
	state = State.STAGGER
	_state_t = -duration
	for t in trails:
		t.emitting = false
	play("Act_Stagger", 0.05)


func die() -> void:
	state = State.DEAD
	health = 0.0
	for t in trails:
		t.emitting = false
	play("Act_Death", 0.08)
	collision_layer = 0
	died.emit(self)


func dodge(dir: Vector3) -> bool:
	if not (state == State.MOVE or state == State.BLOCK or (state == State.ATTACK and _attack_t > float(_attack["hit"]))):
		return false
	if dir.length() < 0.1:
		dir = -forward()
	state = State.DODGE
	_state_t = 0.0
	invulnerable = true
	face(dir, 1.0, 100.0)
	velocity = dir.normalized() * 11.0
	play("Act_Dodge", 0.05, 1.3)
	for t in trails:
		t.emitting = false
	return true


func phantom_step(dir: Vector3) -> bool:
	if not can_act() and state != State.ATTACK:
		return false
	if dir.length() < 0.1:
		dir = forward()
	dir = dir.normalized()
	var dist := weapon.phantom_step_distance
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3(0, 1, 0),
		global_position + Vector3(0, 1, 0) + dir * dist)
	q.exclude = [get_rid()]
	var hit := space.intersect_ray(q)
	if hit:
		dist = maxf(0.0, global_position.distance_to(hit.position) - 0.7)
	var dest := global_position + dir * dist
	state = State.MOVE
	invulnerable = true
	step_vfx.step(dest)
	get_tree().create_timer(0.45).timeout.connect(func(): invulnerable = false)
	return true


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = maxf(velocity.y, -1.0)
	match state:
		State.ATTACK:
			_tick_attack(delta)
		State.DODGE:
			_state_t += delta
			velocity.x = move_toward(velocity.x, 0, 22 * delta)
			velocity.z = move_toward(velocity.z, 0, 22 * delta)
			if _state_t > 0.22:
				invulnerable = false
			if _state_t > 0.5:
				state = State.MOVE
				play(moves["stance"], 0.15)
		State.HIT:
			_state_t += delta
			velocity.x = move_toward(velocity.x, 0, 20 * delta)
			velocity.z = move_toward(velocity.z, 0, 20 * delta)
			if _state_t > 0.4:
				state = State.MOVE
				play(moves["stance"], 0.15)
		State.STAGGER:
			_state_t += delta
			velocity.x = move_toward(velocity.x, 0, 20 * delta)
			velocity.z = move_toward(velocity.z, 0, 20 * delta)
			if _state_t >= 0.0:
				state = State.MOVE
				play(moves["stance"], 0.2)
		State.BLOCK:
			_block_t += delta
			velocity.x = move_toward(velocity.x, 0, 30 * delta)
			velocity.z = move_toward(velocity.z, 0, 30 * delta)
		State.DEAD:
			velocity.x = 0
			velocity.z = 0
	posture = maxf(0.0, posture - 0.15 * delta)
	move_and_slide()


func set_block(on: bool) -> void:
	if on and state == State.MOVE:
		state = State.BLOCK
		_block_t = 0.0
		play(moves["block"], 0.08)
	elif not on and state == State.BLOCK:
		state = State.MOVE
		play(moves["stance"], 0.12)


func locomotion(dir: Vector3, delta: float, speed_scale := 1.0) -> void:
	if state != State.MOVE:
		return
	var speed := float(moves["run_speed"]) * weapon.move_speed_scale * speed_scale
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	if dir.length() > 0.1:
		face(dir, delta)
		if anim.current_animation != moves["run"]:
			play(moves["run"], 0.15, 1.2)
	elif anim.current_animation != moves["stance"]:
		play(moves["stance"], 0.2)
