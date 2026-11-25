## Enemy AI: idle -> notice -> chase -> telegraphed attack -> recover.
## Swings are slowed (attack_speed) so the player can read, block or parry them.
class_name Enemy
extends Fighter

@export var aggro_range := 16.0
@export var aggression := 1.0
var player: Fighter
var _cooldown := 1.5
var _notice := false
var _strafe := 1.0


func _ready() -> void:
	team = 1
	max_health = 90.0
	health = max_health
	attack_speed = 0.72
	add_to_group("fighters")
	add_to_group("enemies")
	_strafe = 1.0 if randf() > 0.5 else -1.0
	died.connect(_on_died)


func _physics_process(delta: float) -> void:
	if player == null:
		var ps := get_tree().get_nodes_in_group("player")
		player = ps[0] if ps.size() > 0 else null
	if state != State.DEAD and player and player.state != State.DEAD:
		_think(delta)
	elif state == State.MOVE:
		locomotion(Vector3.ZERO, delta)
	super(delta)


func _think(delta: float) -> void:
	_cooldown -= delta * aggression
	var to := player.global_position - global_position
	to.y = 0
	var d := to.length()
	look_target = player if _notice else null
	if not _notice:
		_notice = d < aggro_range
		locomotion(Vector3.ZERO, delta)
		return
	var reach := float((moves["light"] as Array)[0]["reach"])
	if state == State.MOVE:
		if d > reach * 0.85:
			locomotion(to.normalized(), delta, 0.75)
		elif _cooldown <= 0.0:
			_cooldown = randf_range(1.4, 2.6)
			start_attack("heavy" if randf() < 0.25 else "light", player)
		else:
			# circle the player while waiting for an opening
			var side := to.normalized().cross(Vector3.UP) * _strafe
			locomotion(side * 0.6, delta, 0.6, player)
	elif state == State.ATTACK and _attack_t < first_hit_time() * 0.6:
		face(to, delta, 4.0)


func _on_died(_f: Fighter) -> void:
	await get_tree().create_timer(2.0).timeout
	var tw := create_tween()
	tw.tween_method(step_vfx.set_dissolve, 0.0, 1.0, 1.2)
	tw.tween_callback(queue_free)
