## Pickups, checkpoints and the goal gate, drawn in world space behind the hero.
extends Node2D

var level: Node


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	if level == null:
		return
	var t := Time.get_ticks_msec() / 1000.0
	var glow: Color = level.hero.hero.glow
	for o in level.orbs:
		if o.taken:
			continue
		var p: Vector2 = o.pos + Vector2(0, sin(t * 3.0 + o.pos.x) * 4.0)
		# an ink drop with a coloured core: the colour the heroes brought
		draw_circle(p, 13.0, Color(glow, 0.18))
		draw_circle(p, 8.0, PFHeroes.INK)
		draw_colored_polygon(PackedVector2Array([p + Vector2(-6, -4), p + Vector2(0, -17), p + Vector2(6, -4)]), PFHeroes.INK)
		draw_circle(p + Vector2(-2, -1), 3.0, glow)
	for c in level.checkpoints:
		var p: Vector2 = c.pos
		if c.zone == 0:
			# a small vermilion banner on a pole: unfurls when lit
			draw_line(p, p + Vector2(0, -96), PFHeroes.INK, 5.0)
			var w := 34.0 if c.lit else 8.0
			var wave := sin(t * 5.0) * 3.0
			draw_colored_polygon(PackedVector2Array([p + Vector2(2, -94), p + Vector2(2 + w, -90 + wave),
				p + Vector2(2 + w * 0.9, -70 + wave), p + Vector2(2, -62)]), PFHeroes.SHU if c.lit else Color(PFHeroes.INK, 0.6))
		else:
			var col := Color(0.3, 0.95, 1.0) if c.lit else Color(0.4, 0.3, 0.6)
			draw_rect(Rect2(p + Vector2(-6, -90), Vector2(12, 90)), Color(0.1, 0.08, 0.2))
			draw_rect(Rect2(p + Vector2(-10, -104), Vector2(20, 14)), col)
			if c.lit:
				draw_circle(p + Vector2(0, -97), 22.0 + sin(t * 6.0) * 3.0, Color(col, 0.2))
	var g: Vector2 = level.goal_pos
	# goal: a torii of light at the end of the neon zone
	var gc := Color(1.0, 0.85, 0.4)
	for sx in [-50.0, 50.0]:
		draw_line(g + Vector2(sx, 0), g + Vector2(sx * 0.92, -170), Color(gc, 0.3), 14.0)
		draw_line(g + Vector2(sx, 0), g + Vector2(sx * 0.92, -170), gc, 4.0)
	draw_line(g + Vector2(-86, -184), g + Vector2(86, -184), gc, 6.0)
	draw_line(g + Vector2(-64, -140), g + Vector2(64, -140), gc, 3.0)
