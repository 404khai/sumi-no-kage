## Parallax scenery for one zone: three repeating layers painted procedurally.
## ink  = washed mountain ranges, mist and pines on paper (sky shader does the sun)
## neon = megastructure ring, tower skyline, near towers with light strips
class_name PFBackdrop
extends Node2D

const WIDTH := 2600.0

var theme := "ink"
var horizon := 560.0


func setup(t: String, horizon_y: float) -> void:
	theme = t
	horizon = horizon_y
	var scales := [0.08, 0.22, 0.45] if t == "ink" else [0.06, 0.2, 0.42]
	for i in 3:
		var p := Parallax2D.new()
		p.scroll_scale = Vector2(scales[i], 1.0)
		p.repeat_size = Vector2(WIDTH, 0)
		p.repeat_times = 4
		p.ignore_camera_scroll = false
		var layer := _Layer.new()
		layer.theme = t
		layer.index = i
		layer.horizon = horizon
		p.add_child(layer)
		add_child(p)


class _Layer extends Node2D:
	var theme := "ink"
	var index := 0
	var horizon := 560.0

	func _draw() -> void:
		var rng := RandomNumberGenerator.new()
		rng.seed = 7 + index * 31 + (100 if theme != "ink" else 0)
		if theme == "ink":
			_ink(rng)
		else:
			_neon(rng)

	func _ridge(rng: RandomNumberGenerator, base: float, amp: float, step: float, jag: float) -> PackedVector2Array:
		var pts := PackedVector2Array()
		var x := 0.0
		var y := base
		var peak_phase := rng.randf() * TAU
		while x <= WIDTH:
			var big := sin(x / WIDTH * TAU * 2.0 + peak_phase) * 0.5 + 0.5
			y = base - amp * (0.3 + 0.7 * big) - rng.randf() * jag
			pts.append(Vector2(x, y))
			x += step
		pts[pts.size() - 1] = Vector2(WIDTH, pts[0].y)
		return pts

	func _ink(rng: RandomNumberGenerator) -> void:
		var ink := PFHeroes.INK
		match index:
			0:
				for k in 2:
					var top := _ridge(rng, horizon - 40.0 - k * 50.0, 320.0 - k * 80.0, 60.0, 30.0)
					# graded wash: several bands fading toward the mist at the foot
					for b in 6:
						var poly := PackedVector2Array()
						for p in top:
							poly.append(p + Vector2(0, b * 26.0))
						poly.append(Vector2(WIDTH, horizon + 200))
						poly.append(Vector2(0, horizon + 200))
						draw_colored_polygon(poly, Color(ink, 0.05 + 0.02 * k))
			1:
				var top := _ridge(rng, horizon + 10.0, 220.0, 40.0, 40.0)
				var poly := top.duplicate()
				poly.append(Vector2(WIDTH, horizon + 300))
				poly.append(Vector2(0, horizon + 300))
				draw_colored_polygon(poly, Color(0.55, 0.54, 0.53, 0.55))
				draw_polyline(top, Color(ink, 0.55), 4.0)
				# pagoda on a ridge
				var px := WIDTH * 0.62
				var py := horizon - 160.0
				for t in 5:
					var w := 70.0 - t * 11.0
					var y := py - t * 34.0
					draw_rect(Rect2(px - w * 0.35, y - 26, w * 0.7, 26), Color(ink, 0.55))
					draw_colored_polygon(PackedVector2Array([Vector2(px - w, y - 22), Vector2(px, y - 40),
						Vector2(px + w, y - 22), Vector2(px + w * 0.8, y - 18), Vector2(px - w * 0.8, y - 18)]), Color(ink, 0.7))
				draw_line(Vector2(px, py - 170), Vector2(px, py - 220), Color(ink, 0.7), 3.0)
			2:
				# mist band and soft near pines
				draw_rect(Rect2(0, horizon - 40, WIDTH, 120), Color(PFHeroes.PAPER, 0.5))
				for i in 9:
					var x := rng.randf() * WIDTH
					var h := rng.randf_range(160, 300)
					var base := Vector2(x, horizon + 60)
					draw_line(base, base + Vector2(rng.randf_range(-15, 15), -h), Color(ink, 0.35), 6.0)
					for k in 4:
						var c := base + Vector2(rng.randf_range(-50, 50), -h + k * 34.0)
						var pts := PackedVector2Array()
						for a in 12:
							var ang := TAU * a / 12
							pts.append(c + Vector2(cos(ang) * rng.randf_range(40, 70), sin(ang) * rng.randf_range(10, 18)))
						draw_colored_polygon(pts, Color(ink, 0.28))

	func _neon(rng: RandomNumberGenerator) -> void:
		var hot := Color(1.0, 0.2, 0.6)
		var cool := Color(0.3, 0.95, 1.0)
		var gold := Color(1.0, 0.8, 0.3)
		match index:
			0:
				# a halo megastructure hanging over the city
				var c := Vector2(WIDTH * 0.5, horizon - 260)
				draw_arc(c, 380, PI * 1.05, PI * 1.95, 64, Color(cool, 0.18), 26.0)
				draw_arc(c, 380, PI * 1.05, PI * 1.95, 64, Color(cool, 0.7), 3.0)
				draw_arc(c, 330, PI * 1.1, PI * 1.9, 64, Color(hot, 0.35), 2.0)
				for i in 24:
					var a := PI * 1.05 + PI * 0.9 * i / 23.0
					draw_line(c + Vector2(cos(a), sin(a)) * 365, c + Vector2(cos(a), sin(a)) * 395, Color(cool, 0.4), 2.0)
			1:
				var x := 0.0
				while x < WIDTH:
					var w := rng.randf_range(50, 120)
					var h := rng.randf_range(160, 420)
					var r := Rect2(x, horizon + 80 - h, w, h + 200)
					draw_rect(r, Color(0.13, 0.08, 0.26))
					for wy in range(int(r.position.y) + 10, int(horizon + 60), 14):
						for wx in range(int(x) + 6, int(x + w) - 6, 10):
							if rng.randf() < 0.22:
								draw_rect(Rect2(wx, wy, 4, 5), Color([hot, cool, gold][rng.randi() % 3], 0.55))
					x += w + rng.randf_range(4, 30)
			2:
				var x := 0.0
				while x < WIDTH:
					var w := rng.randf_range(90, 170)
					var h := rng.randf_range(260, 520)
					var r := Rect2(x, horizon + 140 - h, w, h + 200)
					draw_rect(r, Color(0.05, 0.035, 0.1))
					var strip := [hot, cool][rng.randi() % 2] as Color
					draw_line(Vector2(x + 6, r.position.y + 20), Vector2(x + 6, horizon + 120), Color(strip, 0.7), 2.0)
					draw_line(r.position, Vector2(r.end.x, r.position.y), Color(strip, 0.5), 2.0)
					if rng.randf() < 0.5:
						draw_line(Vector2(x + w * 0.5, r.position.y), Vector2(x + w * 0.5, r.position.y - 60), Color(0.1, 0.08, 0.2), 3.0)
						draw_circle(Vector2(x + w * 0.5, r.position.y - 60), 3.0, hot)
					x += w + rng.randf_range(60, 200)
