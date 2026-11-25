## One immediate-mode drawer for every short-lived effect in the platformer:
## ink droplets, coloured ink splats, brush-stroke slash arcs, shock rings and
## stains that stay on the world where something died. Cheap and data-only.
class_name PFFx
extends Node2D

var _drops: Array = []   # {p, v, life, max, r, c}
var _arcs: Array = []    # {p, a0, a1, r, w, life, max, c}
var _rings: Array = []   # {p, r, life, max, c}
var _stains: Array = []  # {p, pts, c, life}
var shake := 0.0


func splat(at: Vector2, col: Color, n := 14, spd := 320.0, size := 4.0) -> void:
	for i in n:
		var a := randf() * TAU
		var v := Vector2(cos(a), sin(a)) * spd * randf_range(0.3, 1.0) + Vector2(0, -spd * 0.4)
		var life := randf_range(0.35, 0.8)
		_drops.append({"p": at, "v": v, "life": life, "max": life, "r": size * randf_range(0.5, 1.4), "c": col})


func stain(at: Vector2, col: Color, radius := 18.0) -> void:
	var pts := PackedVector2Array()
	var n := 11
	for i in n:
		var a := TAU * i / n + randf() * 0.3
		pts.append(at + Vector2(cos(a), sin(a) * 0.55) * radius * randf_range(0.55, 1.25))
	_stains.append({"p": at, "pts": pts, "c": col, "life": 9.0})
	if _stains.size() > 60:
		_stains.pop_front()


func slash(at: Vector2, aim: float, flip: float, col: Color, radius := 58.0, sweep := 2.4) -> void:
	var a := aim if flip > 0 else PI - aim
	_arcs.append({"p": at, "a0": a - sweep * 0.5, "a1": a + sweep * 0.5, "r": radius, "w": 16.0, "life": 0.22,
		"max": 0.22, "c": col})


func ring(at: Vector2, col: Color, radius := 60.0, life := 0.35) -> void:
	_rings.append({"p": at, "r": radius, "life": life, "max": life, "c": col})


func kick(amount: float) -> void:
	shake = maxf(shake, amount)


func _process(delta: float) -> void:
	shake = maxf(0.0, shake - delta * 30.0)
	for d in _drops:
		d.v.y += 1300.0 * delta
		d.v *= 0.985
		d.p += d.v * delta
		d.life -= delta
	_drops = _drops.filter(func(d): return d.life > 0.0)
	for a in _arcs:
		a.life -= delta
	_arcs = _arcs.filter(func(a): return a.life > 0.0)
	for r in _rings:
		r.life -= delta
	_rings = _rings.filter(func(r): return r.life > 0.0)
	for s in _stains:
		s.life -= delta
	_stains = _stains.filter(func(s): return s.life > 0.0)
	queue_redraw()


func _draw() -> void:
	for s in _stains:
		var c: Color = s.c
		draw_colored_polygon(s.pts, Color(c, 0.55 * clampf(s.life / 2.0, 0.0, 1.0)))
	for a in _arcs:
		var t: float = 1.0 - a.life / a.max
		var c: Color = a.c
		var n := 14
		var outer := PackedVector2Array()
		var inner := PackedVector2Array()
		var head: float = lerpf(a.a0, a.a1, minf(1.0, t * 2.2))
		var tail: float = lerpf(a.a0, a.a1, maxf(0.0, t * 1.6 - 0.4))
		for i in n + 1:
			var k := float(i) / n
			var ang := lerpf(tail, head, k)
			var w: float = a.w * sin(k * PI) * (1.0 - t * 0.6)
			var dir := Vector2(cos(ang), sin(ang))
			outer.append(a.p + dir * (a.r + w * 0.5))
			inner.append(a.p + dir * (a.r - w * 0.5))
		inner.reverse()
		var poly := outer + inner
		if not Geometry2D.triangulate_polygon(poly).is_empty():
			draw_colored_polygon(poly, Color(c, 0.9 * (1.0 - t)))
			draw_polyline(outer, Color(1, 1, 1, 0.8 * (1.0 - t)), 1.5)
			# dry-brush streaks off the stroke
			for i in 4:
				var ang := lerpf(tail, head, 0.2 + i * 0.2)
				var dir := Vector2(cos(ang), sin(ang))
				draw_line(a.p + dir * (a.r - a.w * 0.6), a.p + dir * (a.r - a.w * 1.1 - i * 3.0),
					Color(PFHeroes.INK, 0.6 * (1.0 - t)), 2.0)
	for r in _rings:
		var t: float = 1.0 - r.life / r.max
		draw_arc(r.p, r.r * ease(t, 0.4), 0, TAU, 32, Color(r.c, 1.0 - t), 5.0 * (1.0 - t) + 1.0)
	for d in _drops:
		var k: float = d.life / d.max
		var v: Vector2 = d.v
		var stretch := clampf(v.length() / 400.0, 1.0, 2.6)
		var dir := v.normalized() if v.length() > 1 else Vector2.DOWN
		var p: Vector2 = d.p
		draw_line(p - dir * d.r * stretch, p + dir * d.r * stretch * 0.4, Color(d.c, k), d.r * 2.0 * k + 0.5)
		draw_circle(p, d.r * k, Color(d.c, k))
