## Shared body for the player and enemies: model + weapon mount, health,
## posture/stagger, attacks driven by data/movesets.json, hit resolution.
##
## Motion: FighterAnimator blends locomotion by real velocity (feet stay planted);
## attacks play baked clips whose timing (hits, link window, trails) and root
## motion come from data/clip_events.json, generated with the clips in Blender.
## Combo input is buffered and released at the clip's link frame, where every
## attack is authored to hand off into the next one.
class_name Fighter
extends CharacterBody3D

signal died(f: Fighter)
signal damaged(f: Fighter, amount: float)

enum State { MOVE, ATTACK, DODGE, BLOCK, HIT, STAGGER, DEAD }

const GRAVITY := 18.0
const RED_INK := preload("res://materials/vfx/M_Vfx_InkBlotRed.tres")
const ACCEL := 28.0                  # m/s^2 speeding up
const DECEL := 36.0                  # m/s^2 slowing down
const BUFFER_TIME := 0.45            # how long an early attack press is remembered
const COMBO_GRACE := 0.35            # after a recovery ends, a light press still continues the chain
const STAND_OFF := 1.3               # root motion stops this far from the target's centre

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
var animator: FighterAnimator
var mount: WeaponMount
var trails: Array[InkTrail] = []
var step_vfx: PhantomStepVFX
var look_target: Node3D               # head tracks this (lock-on / the player)
var attack_speed := 1.0               # enemies telegraph by swinging slower
var invulnerable := false
var combo := 0

var _attack: Dictionary = {}
var _ev: Dictionary = {}              # clip events of the current attack
var _hits: Array = []                 # remaining hit times (clip seconds)
var _attack_t := 0.0                  # clip seconds into the current attack
var _attack_len := 0.0
var _link_t := 0.0
var _root_prev := 0.0
var _root_scale := 1.0
var _lunge_left := 0.0                # families without root curves
var _buffer := ""
var _buffer_t := 0.0
var _buffer_target: Fighter
var _grace := 0.0
var _last_kind := ""
var _move_intent := Vector3.ZERO
var _state_t := 0.0
var _block_t := 0.0                    # time the block has been held (parry window)
var _lean := 0.0
var _look: LookAtModifier3D
var _look_point: Node3D


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
	_setup_secondary()
	equip(w)


## Runtime IK/physics on top of the clips: cloth springs and head look-at.
func _setup_secondary() -> void:
	var chains := {}
	for i in skeleton.get_bone_count():
		var n := skeleton.get_bone_name(i)
		if n.begins_with("Tie") or n.begins_with("Sash") or n.begins_with("Cape"):
			var key := n.get_slice("_", 0)
			chains[key] = (chains.get(key, []) as Array) + [n]
	var springs := SpringBoneSimulator3D.new()
	springs.setting_count = chains.size()
	var i := 0
	for key in chains:
		var bones: Array = chains[key]
		bones.sort()
		springs.set_root_bone_name(i, bones[0])
		springs.set_end_bone_name(i, bones[-1])
		springs.set_extend_end_bone(i, true)
		springs.set_end_bone_length(i, 0.08)
		# capes are long and heavy: stiff, damped and weighted so fast turns can't fling
		# them over the head; hair stays loose, obi tails in between
		var heavy: bool = String(key).begins_with("Cape")
		springs.set_stiffness(i, 2.4 if heavy else (1.2 if String(key).begins_with("Sash") else 0.8))
		springs.set_drag(i, 0.75 if heavy else 0.5)
		springs.set_gravity(i, 1.4 if heavy else 0.6)
		springs.set_radius(i, 0.03)
		i += 1
	skeleton.add_child(springs)
	_look_point = Node3D.new()
	_look_point.top_level = true
	add_child(_look_point)
	_look = LookAtModifier3D.new()
	_look.bone_name = "Head"
	_look.forward_axis = SkeletonModifier3D.BONE_AXIS_PLUS_Z
	_look.primary_rotation_axis = Vector3.AXIS_Y
	_look.use_angle_limitation = true
	_look.primary_limit_angle = deg_to_rad(140)
	_look.secondary_limit_angle = deg_to_rad(60)
	_look.duration = 0.25
	_look.influence = 0.0
	skeleton.add_child(_look)
	_look.target_node = _look.get_path_to(_look_point)


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
	if animator:
		animator.queue_free()
	animator = FighterAnimator.new()
	anim.get_parent().add_child(animator)
	var loco: Dictionary = (moves.get("loco", {}) as Dictionary).duplicate()
	loco["idle"] = moves["stance"]
	loco["run"] = moves["run"]
	animator.setup(anim, loco)
	if state != State.MOVE and state != State.DEAD:
		state = State.MOVE


func play(clip: String, blend := 0.12, speed := 1.0) -> void:
	if clip == moves["stance"] or clip == moves["run"]:
		animator.stop_action(maxf(blend, 0.15))   # locomotion graph takes over
	else:
		animator.play_action(clip, blend, speed)


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


func first_hit_time() -> float:
	return float(_hits[0]) if _hits.size() > 0 else float(_ev.get("hits", [_attack.get("hit", 0.3)])[0])


# ------------------------------------------------------------------ attacks
func start_attack(kind: String, target: Fighter = null) -> bool:
	if state == State.DEAD or state == State.HIT or state == State.STAGGER or state == State.DODGE:
		return false
	if state == State.ATTACK:
		# remembered and released at the link frame: the combo never drops a press
		_buffer = kind
		_buffer_t = BUFFER_TIME
		_buffer_target = target
		return true
	return _begin(kind, target, _grace > 0.0)


func _begin(kind: String, target: Fighter, chained: bool) -> bool:
	var data: Dictionary
	if kind == "light":
		var chain: Array = moves["light"]
		combo = (combo + 1) % chain.size() if chained and _last_kind == "light" else 0
		data = (chain[combo] as Dictionary).duplicate()
	elif kind == "heavy" and chained and _last_kind == "light" and combo >= 1 and moves.has("heavy_branch"):
		data = (moves["heavy_branch"] as Dictionary).duplicate()   # combo branch off L2+
		combo = 0
	else:
		if not moves.has(kind):
			return false
		data = (moves[kind] as Dictionary).duplicate()
		combo = 0
	var clip := String(data["anim"])
	data["_kind"] = kind
	data["_target"] = target
	_attack = data
	_ev = Game.clip_event(clip)
	_hits = (_ev.get("hits", [data.get("hit", 0.3)]) as Array).duplicate()
	_link_t = float(_ev.get("link", data.get("cancel", 0.5)))
	_attack_len = float(_ev["length"]) if _ev.has("length") else \
		(anim.get_animation(clip).length if anim.has_animation(clip) else 0.8)
	_attack_t = 0.0
	_root_prev = 0.0
	_lunge_left = float(data.get("lunge", 0.0))
	_last_kind = kind
	_buffer = ""
	_grace = 0.0
	state = State.ATTACK
	if target:
		face(target.global_position - global_position, 1.0, 100.0)
	elif _move_intent.length() > 0.3:
		face(_move_intent, 1.0, 100.0)    # redirect the next cut toward the stick
	_root_scale = _fit_root(target)
	play(clip, 0.1 if chained else 0.07, attack_speed)
	_update_trails()
	if Game.autoplay and team == 0:
		print("[combo] %s%s" % [clip, " (chained)" if chained else ""])
	return true


## Scale the clip's travel so the cut lands at the target instead of past or short of it.
func _fit_root(target: Fighter) -> float:
	var root: Array = _ev.get("root", [])
	if root.is_empty() or target == null:
		return 1.0
	var hit_i := clampi(int(round(first_hit_time() * 30.0)), 0, root.size() - 1)
	var travel := float(root[hit_i])
	if travel < 0.05:
		return 1.0
	var to := target.global_position - global_position
	to.y = 0
	return clampf((to.length() - STAND_OFF) / travel, 0.3, 1.3)


func _root_at(t: float) -> float:
	var root: Array = _ev["root"]
	var x := clampf(t * 30.0, 0.0, root.size() - 1.0)
	var i := int(x)
	var j := mini(i + 1, root.size() - 1)
	return lerpf(float(root[i]), float(root[j]), x - i)


func _tick_attack(delta: float) -> void:
	var dt := delta * attack_speed
	_attack_t += dt
	if _ev.has("root"):
		var d := _root_at(_attack_t)
		var step := (d - _root_prev) * _root_scale
		_root_prev = d
		velocity.x = forward().x * step / delta
		velocity.z = forward().z * step / delta
	elif _lunge_left > 0.0 and _attack_t < first_hit_time() + 0.05:
		var step := minf(_lunge_left, float(_attack["lunge"]) * dt / maxf(first_hit_time(), 0.1))
		_lunge_left -= step
		velocity.x = forward().x * step / delta
		velocity.z = forward().z * step / delta
	else:
		velocity.x = move_toward(velocity.x, 0, 30 * delta)
		velocity.z = move_toward(velocity.z, 0, 30 * delta)
	# small steering until the blade connects
	if _hits.size() > 0 and _attack_t < float(_hits[0]):
		var tgt: Fighter = _attack.get("_target")
		if tgt and is_instance_valid(tgt):
			face(tgt.global_position - global_position, delta, 10.0)
		elif _move_intent.length() > 0.3:
			face(_move_intent, delta, 6.0)
	while _hits.size() > 0 and _attack_t >= float(_hits[0]):
		_hits.pop_front()
		_resolve_hit()
	_update_trails()
	_buffer_t -= delta
	if _buffer_t <= 0.0:
		_buffer = ""
	if _attack_t >= _link_t:
		if _buffer != "":
			var kind := _buffer
			_buffer = ""
			_begin(kind, _buffer_target if _buffer_target and is_instance_valid(_buffer_target) else null, true)
			return
		if _move_intent.length() > 0.3:      # walk out of the recovery
			_end_attack(0.22)
			return
	if _attack_t >= _attack_len:
		_end_attack(0.2)


func _end_attack(blend: float) -> void:
	state = State.MOVE
	_grace = COMBO_GRACE
	for t in trails:
		t.emitting = false
	play(moves["stance"], blend)


func _update_trails() -> void:
	var windows: Dictionary = _ev.get("trails", {})
	if windows.is_empty():
		var on := state == State.ATTACK and _attack_t < first_hit_time() + 0.15
		for t in trails:
			if on and not t.emitting:
				t.clear()
			t.emitting = on
		return
	# hands[0] is the main (right) socket, hands[1] the off (left) one
	for i in trails.size():
		var w: Array = windows.get("R" if i == 0 else "L", [])
		var on := state == State.ATTACK and w.size() == 2 and _attack_t >= float(w[0]) and _attack_t <= float(w[1])
		if on and not trails[i].emitting:
			trails[i].clear()
		trails[i].emitting = on


func _resolve_hit() -> void:
	var reach := float(_attack["reach"])
	var half_arc := deg_to_rad(float(_attack["arc"]) * 0.5)
	var finisher: bool = _attack["_kind"] == "finisher"
	var hits := maxi(1, (_ev.get("hits", [0]) as Array).size())
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
		f.receive_hit(self, float(_attack["damage"]) / hits, float(_attack["stagger"]) / hits, finisher)


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
	_buffer = ""
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
	if not (state == State.MOVE or state == State.BLOCK or (state == State.ATTACK and _attack_t > first_hit_time())):
		return false
	if dir.length() < 0.1:
		dir = -forward()
	state = State.DODGE
	_state_t = 0.0
	_buffer = ""
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
	if state == State.ATTACK:
		_end_attack(0.1)
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
	_grace = maxf(0.0, _grace - delta)
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
	_update_presentation(delta)


func _update_presentation(delta: float) -> void:
	var v := Vector3(velocity.x, 0, velocity.z)
	if state == State.MOVE:
		var bz := model.global_basis.z
		var bx := model.global_basis.x
		# model space: +Z forward, +X is the character's left
		animator.set_locomotion(Vector2(-v.dot(bx), v.dot(bz)))
	else:
		_lean = lerpf(_lean, 0.0, clampf(8 * delta, 0, 1))
	model.rotation.z = _lean
	# head tracks the target while fighting; eases off in big actions
	var want := 0.0
	if look_target and is_instance_valid(look_target) and state != State.DEAD and state != State.DODGE:
		_look_point.global_position = look_target.global_position + Vector3(0, 1.5, 0)
		want = 0.25 if state == State.ATTACK else 0.85
	_look.influence = move_toward(_look.influence, want, delta * 3.0)


func set_block(on: bool) -> void:
	if on and state == State.MOVE:
		state = State.BLOCK
		_block_t = 0.0
		play(moves["block"], 0.08)
	elif not on and state == State.BLOCK:
		state = State.MOVE
		play(moves["stance"], 0.12)


## dir: desired direction (length <= 1, analog magnitude respected).
## face_target: strafe while facing it (lock-on); walk: hold the walk pace.
func locomotion(dir: Vector3, delta: float, speed_scale := 1.0, face_target: Node3D = null, walk := false) -> void:
	_move_intent = dir
	if state != State.MOVE:
		return
	var top := float(moves["run_speed"]) * weapon.move_speed_scale * speed_scale
	if walk or face_target:
		top = minf(top, float(moves.get("walk_speed", 2.4)) * speed_scale)
	var want := dir.limit_length(1.0) * top
	var cur := Vector3(velocity.x, 0, velocity.z)
	var rate := ACCEL if want.length() > cur.length() else DECEL
	cur = cur.move_toward(want, rate * delta)
	velocity.x = cur.x
	velocity.z = cur.z
	var yaw0 := model.rotation.y
	if face_target:
		face(face_target.global_position - global_position, delta, 12.0)
	elif dir.length() > 0.1:
		# turn quicker when slow, wider arcs at a sprint
		face(dir, delta, lerpf(16.0, 9.0, clampf(cur.length() / 7.0, 0, 1)))
	var yaw_rate := wrapf(model.rotation.y - yaw0, -PI, PI) / maxf(delta, 0.001)
	var lean_to := clampf(-yaw_rate * 0.045 * clampf(cur.length() / 6.0, 0, 1), -0.18, 0.18)
	_lean = lerpf(_lean, lean_to, clampf(8 * delta, 0, 1))
