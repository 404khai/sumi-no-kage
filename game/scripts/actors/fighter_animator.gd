## Animation graph for a fighter, built in code on top of the model's AnimationPlayer:
##
##   loco (BlendSpace2D, axes = local velocity in m/s: x right, y forward)
##     -> loco_rate (TimeScale: playback follows the real speed, feet don't skate)
##   act0..act2 (Animation -> TimeSeek -> TimeScale) -> acts (Transition, cross-fade)
##   mix (Blend2: loco <-> current action) -> output
##
## Actions rotate through three slots so a new attack always cross-fades from the
## one before it, even when the combo chains faster than the fade.
class_name FighterAnimator
extends AnimationTree

const SLOTS := 3

var _loco: AnimationNodeBlendSpace2D
var _acts: AnimationNodeTransition
var _slot_anims: Array[AnimationNodeAnimation] = []
var _slot := 0
var _act_weight := 0.0
var _act_target := 0.0
var _act_fade := 0.1
var _player: AnimationPlayer
var current_action := ""
var _native := {}               # direction -> native clip speed (m/s), from clip_events.json
var _max_fwd := 1.0


## loco: {"idle": clip, "walk_f"/"walk_b"/"walk_l"/"walk_r"/"run": clip} (missing keys fall back to run)
func setup(player: AnimationPlayer, loco: Dictionary) -> void:
	_player = player
	player.stop()
	anim_player = get_path_to(player)
	var bt := AnimationNodeBlendTree.new()
	_loco = AnimationNodeBlendSpace2D.new()
	_loco.min_space = Vector2(-8, -8)
	_loco.max_space = Vector2(8, 8)
	_loco.sync = true
	bt.add_node("loco", _loco)
	bt.add_node("loco_rate", AnimationNodeTimeScale.new())
	_acts = AnimationNodeTransition.new()
	_acts.input_count = SLOTS
	_acts.xfade_time = 0.1
	bt.add_node("acts", _acts)
	for i in SLOTS:
		var a := AnimationNodeAnimation.new()
		_slot_anims.append(a)
		bt.add_node("act%d" % i, a)
		bt.add_node("seek%d" % i, AnimationNodeTimeSeek.new())
		bt.add_node("rate%d" % i, AnimationNodeTimeScale.new())
		bt.connect_node("seek%d" % i, 0, "act%d" % i)
		bt.connect_node("rate%d" % i, 0, "seek%d" % i)
		bt.connect_node("acts", i, "rate%d" % i)
		_acts.set_input_name(i, "s%d" % i)
		_acts.set_input_reset(i, true)
	bt.add_node("mix", AnimationNodeBlend2.new())
	bt.connect_node("loco_rate", 0, "loco")
	bt.connect_node("mix", 0, "loco_rate")
	bt.connect_node("mix", 1, "acts")
	bt.connect_node("output", 0, "mix")
	tree_root = bt
	_build_loco(loco)
	active = true
	set("parameters/mix/blend_amount", 0.0)


func _build_loco(loco: Dictionary) -> void:
	var run := String(loco.get("run", ""))
	var idle := String(loco.get("idle", ""))
	_add_point(idle, Vector2.ZERO)
	var run_speed := _speed(run, 6.0)
	_max_fwd = run_speed
	_add_point(run, Vector2(0, run_speed))
	_native = {"f": run_speed, "b": run_speed, "s": run_speed}
	var dirs := {"walk_f": Vector2(0, 1), "walk_b": Vector2(0, -1), "walk_l": Vector2(-1, 0), "walk_r": Vector2(1, 0)}
	for key in dirs:
		var clip := String(loco.get(key, ""))
		if clip == "" or not _player.has_animation(clip):
			continue
		var v := _speed(clip, 2.0)
		_add_point(clip, dirs[key] * v)
		_native[{"walk_f": "f", "walk_b": "b", "walk_l": "s", "walk_r": "s"}[key]] = v
	if not loco.has("walk_b"):  # families without strafe clips: run covers every direction
		for d in [Vector2(0, -1), Vector2(-1, 0), Vector2(1, 0)]:
			_add_point(run, d * run_speed)


func _add_point(clip: String, at: Vector2) -> void:
	if clip == "" or not _player.has_animation(clip):
		return
	var n := AnimationNodeAnimation.new()
	n.animation = clip
	_loco.add_blend_point(n, at, -1, "%s_%d" % [clip, _loco.get_blend_point_count()])


func _speed(clip: String, fallback: float) -> float:
	return float(Game.clip_event(clip).get("speed", fallback))


## velocity in the model's frame (x right, y forward), m/s
func set_locomotion(local_vel: Vector2) -> void:
	var s := local_vel.length()
	if s < 0.05:
		set("parameters/loco/blend_position", Vector2.ZERO)
		set("parameters/loco_rate/scale", 1.0)
		return
	var d := local_vel / s
	# native walk speed in this direction; below it we play the walk slower instead
	# of blending toward idle, which would shorten the stride and skate
	var w: float = (_native["f"] if d.y >= 0.0 else _native["b"]) * d.y * d.y + _native["s"] * d.x * d.x
	var top := lerpf(w, _max_fwd, clampf(d.y, 0.0, 1.0) ** 4)
	var at := minf(s, top) if s >= w else minf(w, s * 4.0)
	set("parameters/loco/blend_position", d * at)
	set("parameters/loco_rate/scale", clampf(s / maxf(at, 0.01), 0.25, 1.8))


func play_action(clip: String, xfade := 0.08, speed := 1.0) -> void:
	if not _player.has_animation(clip):
		return
	_slot = (_slot + 1) % SLOTS
	_slot_anims[_slot].animation = clip
	set("parameters/seek%d/seek_request" % _slot, 0.0)
	set("parameters/rate%d/scale" % _slot, speed)
	# coming from locomotion: no stale slot to fade from, the mix fade does the work
	_acts.xfade_time = xfade if _act_weight > 0.05 else 0.0
	set("parameters/acts/transition_request", "s%d" % _slot)
	current_action = clip
	_act_target = 1.0
	_act_fade = maxf(xfade, 0.01)


func stop_action(xfade := 0.2) -> void:
	current_action = ""
	_act_target = 0.0
	_act_fade = maxf(xfade, 0.01)


func action_time() -> float:
	return float(get("parameters/act%d/time" % _slot)) if current_action != "" else 0.0


func _process(delta: float) -> void:
	_act_weight = move_toward(_act_weight, _act_target, delta / _act_fade)
	# ease the fade so blends start and land softly
	set("parameters/mix/blend_amount", smoothstep(0.0, 1.0, _act_weight))
