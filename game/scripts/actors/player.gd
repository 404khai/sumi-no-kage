## Player: camera-relative movement, combos, dodge, block/parry, Phantom Step,
## finishers, lock-on and weapon switching. With Game.autoplay a simple bot
## drives the same inputs (used by automated playtests and captures).
class_name Player
extends Fighter

var cam_pivot: Node3D
var spring: SpringArm3D
var camera: Camera3D
var lock_target: Fighter
var _yaw := PI
var _pitch := -0.32
var _bot_t := 0.0
var _step_cd := 0.0
var _shake := 0.0


func _ready() -> void:
	team = 0
	add_to_group("fighters")
	add_to_group("player")
	cam_pivot = Node3D.new()
	cam_pivot.top_level = true
	add_child(cam_pivot)
	spring = SpringArm3D.new()
	spring.spring_length = 4.2
	spring.margin = 0.3
	spring.add_excluded_object(get_rid())
	cam_pivot.add_child(spring)
	camera = Camera3D.new()
	camera.fov = 58
	camera.far = 600
	spring.add_child(camera)
	camera.current = true
	damaged.connect(func(_f, amount): _shake = minf(0.35, amount * 0.01))
	if not Game.autoplay:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_yaw -= event.relative.x * Game.mouse_sensitivity
		_pitch = clampf(_pitch - event.relative.y * Game.mouse_sensitivity, -1.1, 0.45)
	for i in Game.WEAPONS.size():
		if event.is_action_pressed("weapon_%d" % (i + 1)) and can_act():
			equip(Game.WEAPONS[i])
			Game.weapon = weapon
	if event.is_action_pressed("lock_on"):
		lock_target = null if lock_target else _nearest_enemy(18.0)


func _process(delta: float) -> void:
	# camera follows the body; lock-on steers yaw toward the target
	if lock_target and (lock_target.state == State.DEAD or not is_instance_valid(lock_target)):
		lock_target = null
	if lock_target:
		var to := lock_target.global_position - global_position
		_yaw = lerp_angle(_yaw, atan2(-to.x, -to.z), clampf(6 * delta, 0, 1))
	cam_pivot.global_position = global_position + Vector3(0, 1.55, 0)
	cam_pivot.rotation = Vector3(_pitch, _yaw, 0)
	spring.position = Vector3(0.55, 0, 0)
	_shake = maxf(0.0, _shake - delta)
	camera.h_offset = randf_range(-1, 1) * _shake * 0.3
	camera.v_offset = randf_range(-1, 1) * _shake * 0.3


func _physics_process(delta: float) -> void:
	_step_cd = maxf(0.0, _step_cd - delta)
	if state != State.DEAD:
		if Game.autoplay:
			_bot(delta)
		else:
			_human(delta)
	super(delta)


func _input_dir() -> Vector3:
	var v := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var basis := Basis(Vector3.UP, _yaw)
	return (basis * Vector3(v.x, 0, v.y)).limit_length(1.0)


func _human(delta: float) -> void:
	var dir := _input_dir()
	set_block(Input.is_action_pressed("block"))
	if Input.is_action_just_pressed("dodge"):
		dodge(dir)
	elif Input.is_action_just_pressed("phantom_step") and _step_cd <= 0.0:
		if phantom_step(dir):
			_step_cd = 1.2
	elif Input.is_action_just_pressed("finisher"):
		try_finisher()
	elif Input.is_action_just_pressed("attack_light"):
		if not try_finisher(true):
			start_attack("light", _soft_target())
	elif Input.is_action_just_pressed("attack_heavy"):
		start_attack("heavy", _soft_target())
	# lock-on: strafe around the target in guard; otherwise run, or walk with Ctrl/Alt or a half-tilted stick
	locomotion(dir, delta, 1.0, lock_target, Input.is_action_pressed("walk") or (dir.length() > 0.05 and dir.length() < 0.55))
	look_target = lock_target if lock_target else _nearest_enemy(6.0)
	if state == State.BLOCK and lock_target:
		face(lock_target.global_position - global_position, delta)


func try_finisher(silent := false) -> bool:
	for n in get_tree().get_nodes_in_group("enemies"):
		var e := n as Fighter
		if e.state == State.STAGGER and e.global_position.distance_to(global_position) < 3.2:
			return start_attack("finisher", e)
	return false if silent else false


func _soft_target() -> Fighter:
	if lock_target:
		return lock_target
	var t := _nearest_enemy(4.0)
	return t


func _nearest_enemy(radius: float) -> Fighter:
	var best: Fighter = null
	var bd := radius
	for n in get_tree().get_nodes_in_group("enemies"):
		var e := n as Fighter
		if e.state == State.DEAD:
			continue
		var d := e.global_position.distance_to(global_position)
		if d < bd:
			bd = d
			best = e
	return best


# ---------------------------------------------------------- autoplay (tests)
func _bot(delta: float) -> void:
	_bot_t += delta
	var target := _nearest_enemy(80.0)
	if target == null:
		locomotion(Vector3.ZERO, delta)
		return
	var to := target.global_position - global_position
	to.y = 0
	var reach := float((moves["light"] as Array)[0]["reach"])
	# read telegraphs like a player would: dodge out of a foe's wind-up
	for n in get_tree().get_nodes_in_group("enemies"):
		var e := n as Fighter
		if e.state == State.ATTACK and e.global_position.distance_to(global_position) < 3.2 \
				and e._attack_t > e.first_hit_time() * 0.45 and e._attack_t < e.first_hit_time() * 0.8:
			if dodge((global_position - e.global_position).normalized().rotated(Vector3.UP, 0.9)):
				return
	if target.state == State.STAGGER and to.length() < 3.0:
		try_finisher()
	elif to.length() > reach * 0.9:
		if to.length() > 7.0 and _step_cd <= 0.0 and phantom_step(to.normalized()):
			_step_cd = 2.0
		locomotion(to.normalized(), delta)
	elif state == State.MOVE or state == State.ATTACK:
		if combo == 2 and state == State.ATTACK and fmod(_bot_t, 6.0) < 3.0:
			start_attack("heavy", target)   # exercise the combo branch (L3 -> rising cut)
		elif fmod(_bot_t, 3.0) < 0.05 and state == State.MOVE:
			start_attack("heavy", target)
		else:
			start_attack("light", target)
	_yaw = lerp_angle(_yaw, atan2(-to.x, -to.z), clampf(2 * delta, 0, 1))
