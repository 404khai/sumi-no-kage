## Procedural 2D puppet: a tiny FK skeleton drawn as flat colour blocks with an
## ink outline and an offset rim sliver (the look of the reference sheets),
## plus verlet cloth for capes and sash tails. Faces +x; the owner flips scale.x.
## Angles are measured from "hanging straight down", positive = swung forward.
class_name PFRig
extends Node2D

const OUTLINE := 2.6
const THIGH := 19.0
const SHIN := 19.0
const UPPER := 15.0
const FORE := 14.0
const TORSO := 26.0

var hero: Dictionary = PFHeroes.SWORDSMAN
var state := "idle"         # idle run jump fall wall dash hurt
var action := ""            # slash shoot draw ""
var action_t := 0.0         # 0..1 progress of the current action
var combo := 0              # alternates slash direction
var aim := 0.0              # radians, 0 = forward, -PI/2 = up (local, unflipped)
var draw_amount := 0.0      # archer bow draw 0..1
var grounded := true
var speed_ratio := 0.0
var flash := 0.0            # white hit flash
var muzzle := 0.0           # gunslinger muzzle flash
var muzzle_hand := 0

var _pose := {}
var _phase := 0.0
var _time := 0.0
var _cloth: Array = []      # Array of {pts, prev, len, width0, width1, anchor_key, color}
var _j := {}                # solved joints (local)


func set_hero(h: Dictionary) -> void:
	hero = h
	_cloth.clear()
	_pose = _target_pose()


func _process(delta: float) -> void:
	_time += delta
	_phase += delta * lerpf(4.0, 13.0, speed_ratio) * (1.0 if state == "run" else 0.0)
	flash = maxf(0.0, flash - delta * 5.0)
	muzzle = maxf(0.0, muzzle - delta * 14.0)
	var target := _target_pose()
	var k := 1.0 - exp(-delta * (30.0 if action != "" else 16.0))
	if _pose.is_empty():
		_pose = target
	for key in target:
		_pose[key] = lerpf(_pose.get(key, 0.0), target[key], k)
	_solve()
	_step_cloth(delta)
	queue_redraw()


# ---------------------------------------------------------------- posing

func _target_pose() -> Dictionary:
	var p := {"lean": 0.06, "head": 0.0, "sh_f": 0.35, "el_f": 0.7, "sh_b": -0.2, "el_b": 0.5,
		"hip_f": 0.18, "kn_f": -0.22, "hip_b": -0.14, "kn_b": -0.12, "bob": 0.0, "weapon": 0.0}
	var breath := sin(_time * 2.4)
	match state:
		"idle":
			p.bob = breath * 0.8
			p.lean += breath * 0.015
		"run":
			var s := sin(_phase)
			var c := cos(_phase)
			p.lean = 0.22 * speed_ratio + 0.05
			p.hip_f = 0.75 * s
			p.hip_b = -0.75 * s
			p.kn_f = -0.25 - 1.1 * maxf(0.0, -c)
			p.kn_b = -0.25 - 1.1 * maxf(0.0, c)
			p.sh_f = -0.6 * s + 0.35
			p.sh_b = 0.6 * s - 0.2
			p.el_f = 0.9
			p.el_b = 0.9
			p.bob = -absf(s) * 3.0
		"jump":
			p.lean = 0.12
			p.hip_f = 1.1
			p.kn_f = -1.5
			p.hip_b = -0.15
			p.kn_b = -0.9
			p.sh_f = 2.2
			p.el_f = 0.5
			p.sh_b = -1.0
			p.el_b = 0.6
		"fall":
			p.lean = 0.0
			p.hip_f = 0.45
			p.kn_f = -0.5
			p.hip_b = -0.3
			p.kn_b = -0.3
			p.sh_f = 1.9
			p.el_f = 0.9
			p.sh_b = 2.4
			p.el_b = 0.6
		"wall":
			p.lean = -0.2
			p.hip_f = 1.0
			p.kn_f = -1.4
			p.hip_b = 0.4
			p.kn_b = -1.2
			p.sh_f = 2.6
			p.el_f = 0.3
			p.sh_b = -0.9
		"dash":
			p.lean = 0.85
			p.hip_f = 0.6
			p.kn_f = -1.2
			p.hip_b = -0.9
			p.kn_b = -0.4
			p.sh_f = 1.0
			p.el_f = 0.2
			p.sh_b = -1.4
			p.el_b = 0.2
			p.head = -0.6
		"hurt":
			p.lean = -0.45
			p.sh_f = 2.4
			p.sh_b = 2.0
			p.hip_f = 0.6
			p.kn_f = -0.8
	if action != "":
		_apply_action(p)
	return p


func _apply_action(p: Dictionary) -> void:
	var a := PI * 0.5 - aim   # aim -> "angle from down"
	match action:
		"slash":
			var t := ease(action_t, 0.35)
			var from := a + 2.3
			var to := a - 1.5
			if combo % 2 == 1:
				var tmp := from
				from = to
				to = tmp
			p.sh_f = lerpf(from, to, t)
			p.el_f = 0.15
			p.weapon = lerpf(-0.6, 0.4, t) * (1.0 if combo % 2 == 0 else -1.0)
			p.lean = 0.25 + 0.15 * sin(t * PI)
			p.sh_b = lerpf(-1.2, 0.6, t)
		"windup":   # foes telegraph: weapon drawn back, body coiled
			p.sh_f = -1.6 if hero.id == "oni" else 0.2
			p.el_f = 0.6
			p.sh_b = -0.6
			p.lean = -0.2
			p.hip_f = 0.5
			p.kn_f = -0.7
			p.weapon = 0.0
		"thrust":
			p.sh_f = PI * 0.5
			p.el_f = 0.0
			p.sh_b = PI * 0.45
			p.el_b = 0.2
			p.lean = 0.45
			p.hip_f = 0.8
			p.kn_f = -0.5
			p.hip_b = -0.6
		"slam":
			var t := ease(action_t, 0.3)
			p.sh_f = lerpf(-1.6, 1.3, t)
			p.sh_b = lerpf(-1.4, 1.2, t)
			p.el_f = 0.1
			p.lean = lerpf(-0.2, 0.55, t)
			p.hip_f = 0.7
			p.kn_f = -0.9
		"shoot":
			p.sh_f = a
			p.el_f = 0.0
			p.sh_b = a + 0.08
			p.el_b = 0.0
			p.lean = 0.05 + (0.1 if absf(aim) < 0.3 else 0.0)
		"draw":
			p.sh_f = a
			p.el_f = 0.0
			p.sh_b = a + 0.25
			p.el_b = -lerpf(0.4, 2.7, draw_amount)
			p.lean = 0.0
			p.head = clampf(-aim * 0.3, -0.4, 0.4) * -1.0


func _dir(a: float) -> Vector2:
	return Vector2(sin(a), cos(a))


func _solve() -> void:
	var p := _pose
	var hip := Vector2(0, -THIGH - SHIN + p.bob)
	var legs := {}
	for side in ["f", "b"]:
		var h: Vector2 = hip + Vector2(2.5 if side == "f" else -2.5, 0)
		var ta: float = p["hip_" + side]
		var k: Vector2 = h + _dir(ta) * THIGH
		var f: Vector2 = k + _dir(ta + p["kn_" + side]) * SHIN
		legs[side] = [h, k, f]
	# plant the lowest foot on the ground line when grounded
	var low := maxf(legs.f[2].y, legs.b[2].y)
	var shift := Vector2(0, -low) if grounded else Vector2.ZERO
	if not grounded:
		shift.y = -(low - 0.0) * 0.35
	var lean: float = p.lean
	hip += shift
	var sh: Vector2 = hip + Vector2(sin(lean), -cos(lean)) * TORSO
	var head: Vector2 = sh + Vector2(sin(lean + p.head), -cos(lean + p.head)) * 12.0
	_j = {"hip": hip, "sh": sh, "head": head}
	for side in ["f", "b"]:
		_j["hip_" + side] = legs[side][0] + shift
		_j["knee_" + side] = legs[side][1] + shift
		_j["foot_" + side] = legs[side][2] + shift
		var s0: Vector2 = sh + Vector2(1.5 if side == "f" else -2.0, 1.0)
		var e: Vector2 = s0 + _dir(p["sh_" + side]) * UPPER
		var fa: float = p["sh_" + side] + p["el_" + side]
		var hnd: Vector2 = e + _dir(fa) * FORE
		_j["sho_" + side] = s0
		_j["elb_" + side] = e
		_j["hand_" + side] = hnd
		_j["fore_" + side] = fa


# ---------------------------------------------------------------- cloth

func _cloth_spec() -> Array:
	match hero.id:
		"swordsman":
			return [{"anchor": "hip", "off": Vector2(-6, -2), "n": 5, "len": 7.0, "w0": 4.0, "w1": 1.5,
				"color": hero.body_dark}]
		"gunslinger":
			return [{"anchor": "head", "off": Vector2(-4, -6), "n": 3, "len": 6.0, "w0": 1.6, "w1": 1.0,
				"color": PFHeroes.INK}]
		"goon":   # sashimono banner pole flag
			return [{"anchor": "sh", "off": Vector2(-7, -22), "n": 4, "len": 5.0, "w0": 7.0, "w1": 6.0,
				"color": PFHeroes.SHU}]
		"oni":
			return [{"anchor": "hip", "off": Vector2(-7, -2), "n": 4, "len": 6.0, "w0": 9.0, "w1": 5.0,
				"color": Color(0.3, 0.27, 0.25)}]
		_:
			return [{"anchor": "sh", "off": Vector2(-4, 2), "n": 7, "len": 9.0, "w0": 20.0, "w1": 30.0,
				"color": hero.body}]


func _step_cloth(delta: float) -> void:
	var spec := _cloth_spec()
	if _cloth.size() != spec.size():
		_cloth.clear()
		for s in spec:
			var pts: Array[Vector2] = []
			var a: Vector2 = to_global(_j[s.anchor] + s.off)
			for i in s.n:
				pts.append(a + Vector2(0, i * s.len))
			_cloth.append({"spec": s, "pts": pts, "prev": pts.duplicate()})
	var flip := signf(global_scale.x) if global_scale.x != 0 else 1.0
	var wind := Vector2(-flip * 260.0 - 0.0, 0) * (0.3 + speed_ratio) + Vector2(sin(_time * 3.1) * 50.0, 0)
	for c in _cloth:
		var s: Dictionary = c.spec
		var pts: Array[Vector2] = c.pts
		var prev: Array = c.prev
		pts[0] = to_global(_j[s.anchor] + s.off)
		prev[0] = pts[0]
		for i in range(1, pts.size()):
			var v: Vector2 = (pts[i] - prev[i]) * 0.94
			prev[i] = pts[i]
			pts[i] += v + (Vector2(0, 900.0) + wind) * delta * delta
		for _it in 3:
			for i in range(1, pts.size()):
				var d: Vector2 = pts[i] - pts[i - 1]
				var l := d.length()
				if l > 0.001:
					pts[i] = pts[i - 1] + d / l * minf(l, s.len)


# ---------------------------------------------------------------- drawing

func _draw() -> void:
	if _j.is_empty():
		return
	var h := hero
	var dark: Color = h.body_dark
	var ink := PFHeroes.INK
	var limb: Color = ink.lightened(0.07)
	# back cloth first
	for c in _cloth:
		_draw_cloth(c)
	match h.id:
		"swordsman": _draw_swordsman(h, limb, dark)
		"gunslinger": _draw_gunslinger(h, limb, dark)
		"goon": _draw_goon(h, limb, dark)
		"oni": _draw_oni(h, limb, dark)
		_: _draw_archer(h, limb, dark)
	if flash > 0.0:
		var w := Color(1, 1, 1, flash * 0.85)
		draw_circle(_j.hip + Vector2(0, -12), 34.0 * flash, Color(w, flash * 0.25))


func _draw_swordsman(h: Dictionary, limb: Color, dark: Color) -> void:
	# back limbs
	_limb(_j.sho_b, _j.elb_b, 5.0, 4.0, limb)
	_limb(_j.elb_b, _j.hand_b, 4.0, 3.5, limb)
	_limb(_j.hip_b, _j.knee_b, 6.0, 5.0, limb)
	_limb(_j.knee_b, _j.foot_b, 5.0, 4.5, h.armor.darkened(0.3))
	_foot(_j.foot_b, h.armor.darkened(0.3))
	_limb(_j.hip_f, _j.knee_f, 6.0, 5.0, limb)
	_limb(_j.knee_f, _j.foot_f, 5.0, 4.5, h.armor)
	_foot(_j.foot_f, h.armor)
	# hakama: one flared skirt over both legs
	var mid_f: Vector2 = _j.knee_f.lerp(_j.foot_f, 0.55)
	var mid_b: Vector2 = _j.knee_b.lerp(_j.foot_b, 0.55)
	var hk := PackedVector2Array([_j.hip + Vector2(-9, -3), _j.hip + Vector2(9, -3), _j.knee_f + Vector2(8, 0),
		mid_f + Vector2(9, 0), mid_f + Vector2(-5, 2), mid_b + Vector2(-9, 0), _j.knee_b + Vector2(-8, 0)])
	_poly(hk, h.body)
	draw_colored_polygon(PackedVector2Array([_j.hip + Vector2(-1, 2), _j.hip + Vector2(3, 2),
		mid_f.lerp(mid_b, 0.5) + Vector2(2, 0), mid_f.lerp(mid_b, 0.5) + Vector2(-4, 0)]), dark)
	# torso (gi) + sash
	_torso(h.body, 11.0, 9.0)
	_limb(_j.hip + Vector2(0, -3), _j.hip + Vector2(0, -8), 11.0, 11.0, PFHeroes.INK.lightened(0.12), false)
	draw_line(_j.sh + Vector2(-6, 0), _j.hip + Vector2(6, -6), PFHeroes.INK, 2.0)
	# head: tall visor block with a glowing square eye
	_head_box(h.head, 8.0, 11.0)
	var eye: Vector2 = _j.head + Vector2(3.5, -2).rotated(_pose.lean)
	draw_rect(Rect2(eye - Vector2(2.6, 2.6), Vector2(5.2, 5.2)), Color(h.glow, 0.35))
	draw_rect(Rect2(eye - Vector2(1.6, 1.6), Vector2(3.2, 3.2)), h.glow)
	# front arm with layered pauldron
	_limb(_j.sho_f, _j.elb_f, 5.0, 4.0, limb)
	_limb(_j.elb_f, _j.hand_f, 4.0, 4.0, limb)
	var pd: Vector2 = _j.sho_f
	var arm_dir: Vector2 = (_j.elb_f - _j.sho_f).normalized()
	for i in 3:
		var c: Vector2 = pd + arm_dir * (i * 3.2)
		var n := arm_dir.orthogonal()
		_poly(PackedVector2Array([c + n * 8.0 - arm_dir * 3.0, c - n * 8.0 - arm_dir * 3.0,
			c - n * 7.0 + arm_dir * 3.5, c + n * 7.0 + arm_dir * 3.5]), h.armor.lightened(0.08 * i))
	draw_circle(_j.hand_f, 3.6, PFHeroes.INK)
	# the blade: jagged, glowing
	_sword(h)


func _sword(h: Dictionary) -> void:
	var base: Vector2 = _j.hand_f
	var ang: float = _j.fore_f + _pose.weapon
	var d := _dir(ang)
	if action == "":
		d = _dir(ang + 1.2)   # rest the blade low and forward
	var n := d.orthogonal()
	var L := 62.0 if action == "slash" else 54.0
	draw_line(base - d * 7.0, base + d * 2.0, PFHeroes.INK, 4.0)
	var pts := PackedVector2Array([base + n * 2.0, base - n * 2.0])
	var steps := 6
	for i in range(1, steps + 1):
		var t := float(i) / steps
		var w := lerpf(2.6, 0.4, t)
		pts.append(base + d * (L * t) - n * w)
	var top := PackedVector2Array()
	for i in range(steps, 0, -1):
		var t := float(i) / steps
		var w := lerpf(2.6, 0.4, t)
		top.append(base + d * (L * t - 4.0) + n * (w + (7.0 if i % 2 == 0 else 0.0)))
		top.append(base + d * (L * t - 7.0) + n * w)
	pts.append_array(top)
	var glow := Color(h.glow, 0.18)
	draw_line(base, base + d * L, glow, 12.0)
	draw_line(base, base + d * L, Color(h.glow, 0.25), 6.0)
	_draw_safe_poly(pts, h.glow)
	draw_line(base + d * 4.0, base + d * (L - 4.0), Color(1, 1, 1, 0.75), 1.2)


func _draw_gunslinger(h: Dictionary, limb: Color, dark: Color) -> void:
	_limb(_j.sho_b, _j.elb_b, 5.0, 4.5, limb)
	_limb(_j.elb_b, _j.hand_b, 6.0, 6.0, h.body_dark)
	_pistol(_j.hand_b, _j.fore_b, h, 1)
	_limb(_j.hip_b, _j.knee_b, 6.5, 5.0, limb)
	_limb(_j.knee_b, _j.foot_b, 7.0, 5.5, h.body_dark)
	_foot(_j.foot_b, PFHeroes.INK)
	_limb(_j.hip_f, _j.knee_f, 6.5, 5.0, limb)
	_limb(_j.knee_f, _j.foot_f, 7.5, 6.0, h.body)
	_foot(_j.foot_f, PFHeroes.INK)
	# black suit torso, then a chunky orange chest plate
	_torso(limb, 10.0, 7.0)
	var up: Vector2 = (_j.sh - _j.hip).normalized()
	var side: Vector2 = -up.orthogonal()
	var c: Vector2 = _j.sh - up * 6.0
	_poly(PackedVector2Array([c + side * 10.0 + up * 4.0, c - side * 9.0 + up * 4.0, c - side * 7.0 - up * 9.0,
		c + side * 8.0 - up * 9.0]), h.body)
	for i in 2:
		draw_line(c + side * (2.0 + i * 3.0) - up * 1.0, c + side * (5.0 + i * 3.0) + up * 2.0, h.body_dark, 1.6)
	# pauldrons
	_poly(_ngon(_j.sho_b + up * 1.0, 8.0, 6, 0.3), h.body_dark)
	# helmet: pale faceted dome
	_poly(_ngon(_j.head, 9.5, 7, _pose.lean), h.head)
	draw_colored_polygon(PackedVector2Array([_j.head + Vector2(-3, -7), _j.head + Vector2(3, -8), _j.head + Vector2(1, -3)]),
		Color(1, 1, 1, 0.55))
	_limb(_j.sho_f, _j.elb_f, 5.0, 4.5, limb)
	_poly(_ngon(_j.sho_f + up * 1.0, 9.0, 6, 0.1), h.body)
	draw_line(_j.sho_f + up * 4.0 + side * 2.0, _j.sho_f + up * 1.0 + side * 6.0, h.body_dark, 1.6)
	_limb(_j.elb_f, _j.hand_f, 6.5, 6.5, h.body)
	_pistol(_j.hand_f, _j.fore_f, h, 0)


func _pistol(at: Vector2, fore: float, h: Dictionary, hand: int) -> void:
	var d := _dir(fore if action == "shoot" else fore + 1.3)
	var n := d.orthogonal()
	_poly(PackedVector2Array([at - d * 2.0 + n * 4.0, at + d * 13.0 + n * 4.0, at + d * 13.0 - n * 1.0,
		at - d * 2.0 - n * 1.0]), PFHeroes.INK.lightened(0.1))
	_limb(at, at - n * 6.0 + d * 1.0, 3.5, 3.0, h.body, false)
	draw_line(at + d * 2.0 + n * 2.5, at + d * 11.0 + n * 2.5, h.body, 1.5)
	if muzzle > 0.0 and muzzle_hand == hand:
		var tip := at + d * 15.0 + n * 1.5
		draw_circle(tip, 8.0 * muzzle, Color(h.glow, 0.5))
		draw_colored_polygon(PackedVector2Array([tip + n * 4.0, tip + d * 16.0 * muzzle, tip - n * 4.0]), Color.WHITE)


func _draw_archer(h: Dictionary, limb: Color, dark: Color) -> void:
	# backpack quiver with glowing arrow tips
	var up: Vector2 = (_j.sh - _j.hip).normalized()
	var side: Vector2 = -up.orthogonal()
	var bp: Vector2 = _j.sh.lerp(_j.hip, 0.35) - side * 9.0
	_poly(PackedVector2Array([bp - side * 7.0 + up * 12.0, bp + side * 5.0 + up * 13.0, bp + side * 6.0 - up * 12.0,
		bp - side * 6.0 - up * 11.0]), PFHeroes.INK.lightened(0.04))
	draw_line(bp - side * 5.0 - up * 2.0, bp + side * 3.0 - up * 2.0, Color(0.15, 0.25, 0.45), 2.0)
	for i in 3:
		var base: Vector2 = bp + up * 12.0 + side * (-3.0 + i * 3.0)
		draw_line(base, base + up * 9.0 + side * (i - 1) * 1.5, h.glow, 1.6)
		draw_circle(base + up * 9.0 + side * (i - 1) * 1.5, 1.6, Color(0.6, 0.3, 1.0))
	_limb(_j.hip_b, _j.knee_b, 4.5, 3.5, limb)
	_limb(_j.knee_b, _j.foot_b, 3.5, 2.0, limb)
	_limb(_j.hip_f, _j.knee_f, 5.0, 3.5, h.body_dark)
	_limb(_j.knee_f, _j.foot_f, 3.5, 2.0, limb)
	_foot(_j.foot_f, limb, 9.0)
	_foot(_j.foot_b, limb, 9.0)
	# vermilion lining under a draped purple cloak
	_poly(PackedVector2Array([_j.hip + Vector2(-6, -4), _j.hip + Vector2(7, -2), _j.knee_f + Vector2(2, -2),
		_j.knee_b.lerp(_j.knee_f, 0.5) + Vector2(-6, 0)]), Color(0.7, 0.2, 0.12))
	_torso(dark, 9.0, 8.0)
	# hood
	var hd: Vector2 = _j.head
	_poly(PackedVector2Array([hd + Vector2(-11, 6), hd + Vector2(-8, -9), hd + Vector2(1, -13), hd + Vector2(9, -2),
		hd + Vector2(8, 7)]), h.body)
	draw_colored_polygon(PackedVector2Array([hd + Vector2(1, -5), hd + Vector2(8, -1), hd + Vector2(7, 6),
		hd + Vector2(-1, 5)]), h.head)
	draw_line(hd + Vector2(4, -1), hd + Vector2(7, -1), h.glow, 1.4)
	# front cloak drape over the shoulder
	_poly(PackedVector2Array([_j.sh + Vector2(-9, -3), _j.sh + Vector2(7, -1), _j.sh.lerp(_j.hip, 0.7) + Vector2(5, 0),
		_j.sh.lerp(_j.hip, 0.9) + Vector2(-12, 0)]), h.body)
	_limb(_j.sho_b, _j.elb_b, 3.5, 3.0, limb)
	_limb(_j.elb_b, _j.hand_b, 3.0, 3.0, limb)
	_bow(h)
	_limb(_j.sho_f, _j.elb_f, 3.8, 3.2, limb)
	_limb(_j.elb_f, _j.hand_f, 3.2, 3.2, limb)
	draw_circle(_j.hand_f, 3.0, Color(0.15, 0.25, 0.45))


func _bow(h: Dictionary) -> void:
	var g: Vector2 = _j.hand_f
	var d := _dir(_j.fore_f) if action == "draw" else _dir(PI * 0.5 + 0.15)
	var n := -d.orthogonal()   # along the bow limbs
	var top := g + n * 30.0 - d * 6.0
	var bot := g - n * 30.0 - d * 6.0
	var c := Color(h.glow, 0.2)
	var pts := PackedVector2Array([top, top + d * 7.0 - n * 3.0, g + n * 13.0 + d * 4.0, g, g - n * 13.0 + d * 4.0,
		bot + d * 7.0 + n * 3.0, bot])
	draw_polyline(pts, c, 7.0)
	draw_polyline(pts, PFHeroes.INK, 4.4)
	draw_polyline(pts, h.glow, 2.6)
	var nock: Vector2 = _j.hand_b if action == "draw" else g - d * 6.0
	draw_polyline(PackedVector2Array([top, nock, bot]), Color(h.glow, 0.85), 1.0)
	if action == "draw":
		var tip: Vector2 = nock + d * (44.0 + 6.0 * draw_amount)
		draw_line(nock, tip, Color(1, 1, 1, 0.9), 1.6)
		draw_colored_polygon(PackedVector2Array([tip + n * 3.0, tip + d * 7.0, tip - n * 3.0]), h.glow)
		if draw_amount >= 0.99:
			draw_circle(tip, 5.0 + sin(_time * 30.0) * 1.5, Color(h.glow, 0.45))


func _draw_goon(h: Dictionary, limb: Color, dark: Color) -> void:
	_limb(_j.sho_b, _j.elb_b, 4.5, 4.0, dark)
	_limb(_j.elb_b, _j.hand_b, 4.0, 3.5, dark)
	_limb(_j.hip_b, _j.knee_b, 5.5, 4.5, dark)
	_limb(_j.knee_b, _j.foot_b, 4.5, 3.5, dark)
	_foot(_j.foot_b, dark)
	_limb(_j.hip_f, _j.knee_f, 5.5, 4.5, limb)
	_limb(_j.knee_f, _j.foot_f, 4.5, 3.5, limb)
	_foot(_j.foot_f, limb)
	# sashimono pole
	var up: Vector2 = (_j.sh - _j.hip).normalized()
	draw_line(_j.sh + Vector2(-7, 2), _j.sh + Vector2(-7, 2) + up * 24.0, PFHeroes.INK, 2.0)
	# lamellar do + kusazuri skirt
	_poly(PackedVector2Array([_j.hip + Vector2(-9, -2), _j.hip + Vector2(9, -2), _j.hip.lerp(_j.knee_f, 0.5) + Vector2(8, 0),
		_j.hip.lerp(_j.knee_b, 0.5) + Vector2(-9, 0)]), h.armor)
	_torso(h.body, 12.0, 10.0)
	for i in 3:
		var y: Vector2 = _j.hip.lerp(_j.sh, 0.25 + i * 0.22)
		draw_line(y + Vector2(-5, 0), y + Vector2(5, 0), Color(h.rim, 0.55), 1.4)
	# jingasa: a wide flat cone, eyes a vermilion slit beneath
	var hd: Vector2 = _j.head
	draw_line(hd + Vector2(1, 2), hd + Vector2(6, 2), h.glow, 2.0)
	_poly(PackedVector2Array([hd + Vector2(-16, -1), hd + Vector2(0, -12), hd + Vector2(17, -1), hd + Vector2(0, -3)]),
		h.armor.darkened(0.2))
	if h.get("weapon", "yari") == "yumi":
		_bow(h)
	else:
		_yari(h)
	_limb(_j.sho_f, _j.elb_f, 4.5, 4.0, limb)
	_limb(_j.elb_f, _j.hand_f, 4.0, 3.5, limb)
	draw_circle(_j.hand_f, 3.0, PFHeroes.INK)


func _yari(h: Dictionary) -> void:
	var d := _dir(_j.fore_f) if action in ["thrust", "windup"] else _dir(PI * 0.5 + 0.9)
	var a: Vector2 = _j.hand_f - d * 26.0
	var b: Vector2 = _j.hand_f + d * 44.0
	draw_line(a, b, PFHeroes.INK, 4.0)
	draw_line(a, b, Color(0.35, 0.22, 0.15), 2.0)
	var n := d.orthogonal()
	_poly(PackedVector2Array([b + n * 3.0, b + d * 16.0, b - n * 3.0]), Color(0.85, 0.85, 0.8))
	if action == "windup":
		draw_circle(b + d * 8.0, 6.0 + sin(_time * 40.0) * 2.0, Color(h.glow, 0.6))


func _draw_oni(h: Dictionary, limb: Color, dark: Color) -> void:
	_limb(_j.sho_b, _j.elb_b, 8.0, 7.0, dark)
	_limb(_j.elb_b, _j.hand_b, 7.0, 7.0, dark)
	_limb(_j.hip_b, _j.knee_b, 9.0, 7.5, dark)
	_limb(_j.knee_b, _j.foot_b, 7.5, 6.5, dark)
	_foot(_j.foot_b, dark, 13.0)
	_limb(_j.hip_f, _j.knee_f, 9.0, 7.5, limb)
	_limb(_j.knee_f, _j.foot_f, 7.5, 6.5, limb)
	_foot(_j.foot_f, limb, 13.0)
	# tiger-skin loincloth in vermilion-and-ink stripes
	var lo := PackedVector2Array([_j.hip + Vector2(-11, -4), _j.hip + Vector2(11, -4), _j.knee_f + Vector2(5, -4),
		_j.knee_b + Vector2(-6, -4)])
	_poly(lo, Color(0.55, 0.12, 0.08))
	for i in 3:
		var c: Vector2 = _j.hip.lerp(_j.knee_f.lerp(_j.knee_b, 0.5), 0.25 + i * 0.25)
		draw_line(c + Vector2(-6, -1), c + Vector2(4, 2), PFHeroes.INK, 2.0)
	# hulking torso and shoulders
	_limb(_j.hip, _j.sh, 16.0, 20.0, h.body)
	_poly(_ngon(_j.sho_b, 8.0, 6, 0.2), h.armor)
	# horned red mask
	var hd: Vector2 = _j.head + Vector2(1, 1)
	_poly(_ngon(hd, 9.0, 6, 0.4), h.head)
	_poly(PackedVector2Array([hd + Vector2(-6, -6), hd + Vector2(-11, -17), hd + Vector2(-2, -8)]), PFHeroes.PAPER)
	_poly(PackedVector2Array([hd + Vector2(3, -8), hd + Vector2(8, -19), hd + Vector2(7, -6)]), PFHeroes.PAPER)
	draw_line(hd + Vector2(1, -2), hd + Vector2(7, -1), Color(1, 0.9, 0.5), 2.0)
	draw_line(hd + Vector2(0, 4), hd + Vector2(7, 4), PFHeroes.PAPER, 1.6)
	# kanabo: iron-studded club
	var d := _dir(_j.fore_f) if action in ["slam", "windup"] else _dir(PI * 0.5 + 1.0)
	var n := d.orthogonal()
	var base: Vector2 = _j.hand_f - d * 6.0
	var tip: Vector2 = _j.hand_f + d * 40.0
	_poly(PackedVector2Array([base + n * 2.5, tip + n * 6.5, tip - n * 6.5, base - n * 2.5]), Color(0.2, 0.19, 0.19))
	for i in 4:
		var c: Vector2 = base.lerp(tip, 0.4 + i * 0.17)
		draw_circle(c + n * 5.0, 1.8, PFHeroes.PAPER)
		draw_circle(c - n * 5.0, 1.8, PFHeroes.PAPER)
	if action == "windup":
		draw_circle(tip, 10.0 + sin(_time * 40.0) * 3.0, Color(h.glow, 0.5))
	_limb(_j.sho_f, _j.elb_f, 8.0, 7.0, limb)
	_poly(_ngon(_j.sho_f, 9.0, 6, 0.5), h.armor)
	_limb(_j.elb_f, _j.hand_f, 7.0, 7.0, limb)
	draw_circle(_j.hand_f, 5.0, PFHeroes.INK)


func _draw_cloth(c: Dictionary) -> void:
	var s: Dictionary = c.spec
	var pts: Array[Vector2] = c.pts
	var loc: Array[Vector2] = []
	for p in pts:
		loc.append(to_local(p))
	for i in range(loc.size() - 1):
		var t0 := float(i) / (loc.size() - 1)
		var t1 := float(i + 1) / (loc.size() - 1)
		_limb(loc[i], loc[i + 1], lerpf(s.w0, s.w1, t0), lerpf(s.w0, s.w1, t1), s.color, i == 0)
	if hero.id == "archer":
		# ragged hem: a few torn strips
		var last: Vector2 = loc[loc.size() - 1]
		var prev: Vector2 = loc[loc.size() - 2]
		var dd := (last - prev).normalized()
		var nn := dd.orthogonal()
		for k in 3:
			var o := last + nn * (k - 1) * 8.0
			draw_line(o, o + dd * (6.0 + k * 3.0) + nn * 2.0, hero.body_dark, 3.0)


# ---------------------------------------------------------------- primitives

func _torso(col: Color, w_top: float, w_bot: float) -> void:
	_limb(_j.hip, _j.sh, w_bot, w_top, col)


func _head_box(col: Color, w: float, hgt: float) -> void:
	var r: float = _pose.lean + _pose.head
	var c: Vector2 = _j.head
	var pts := PackedVector2Array()
	for v in [Vector2(-w * 0.55, hgt * 0.55), Vector2(-w * 0.6, -hgt * 0.5), Vector2(w * 0.45, -hgt * 0.62),
			Vector2(w * 0.62, hgt * 0.4), Vector2(w * 0.1, hgt * 0.62)]:
		pts.append(c + (v as Vector2).rotated(r))
	_poly(pts, col)


func _foot(at: Vector2, col: Color, length := 11.0) -> void:
	_poly(PackedVector2Array([at + Vector2(-4, -4), at + Vector2(3, -4), at + Vector2(length - 2.0, 0),
		at + Vector2(-4, 0)]), col)


func _ngon(c: Vector2, r: float, n: int, rot: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in n:
		var a := rot + TAU * i / n
		pts.append(c + Vector2(cos(a), sin(a)) * r * (0.92 + 0.08 * ((i * 7) % 3)))
	return pts


func _limb(a: Vector2, b: Vector2, wa: float, wb: float, col: Color, rim := true) -> void:
	var d := b - a
	if d.length() < 0.01:
		return
	var n := d.normalized().orthogonal()
	var e := d.normalized() * 1.2
	_poly(PackedVector2Array([a + n * wa * 0.5 - e, b + n * wb * 0.5 + e, b - n * wb * 0.5 + e, a - n * wa * 0.5 - e]),
		col, rim)


func _poly(pts: PackedVector2Array, col: Color, rim := true) -> void:
	if pts.size() < 3:
		return
	for o in Geometry2D.offset_polygon(pts, OUTLINE, Geometry2D.JOIN_MITER):
		_fill(o, PFHeroes.INK)
	if rim:
		var off := Vector2(-2.2, 0.8)
		var shifted := PackedVector2Array()
		for p in pts:
			shifted.append(p + off)
		_fill(shifted, hero.rim)
	_fill(pts, col.lerp(Color.WHITE, flash * 0.8))


## draw_colored_polygon, but a degenerate or self-crossing shape (limbs folding
## through each other mid-swing) falls back to its hull instead of erroring.
func _fill(pts: PackedVector2Array, col: Color) -> void:
	if Geometry2D.triangulate_polygon(pts).is_empty():
		pts = Geometry2D.convex_hull(pts)
		if pts.size() > 1 and pts[0] == pts[pts.size() - 1]:
			pts.remove_at(pts.size() - 1)
		if pts.size() < 3 or Geometry2D.triangulate_polygon(pts).is_empty():
			return
	draw_colored_polygon(pts, col)


func _draw_safe_poly(pts: PackedVector2Array, col: Color) -> void:
	_fill(pts, col)
