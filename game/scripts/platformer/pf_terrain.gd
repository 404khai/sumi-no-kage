## Builds collision from an ASCII zone map and paints it. Same geometry, two
## hands: "ink" brushes slabs like a sumi-e landscape (dry-brush tops, washed
## faces, vermilion torii); "neon" draws dark hull plates with lit edges.
class_name PFTerrain
extends Node2D

const TILE := 48.0

var theme := "ink"
var rects: Array[Rect2] = []      # solid, world space
var planks: Array[Rect2] = []     # one-way
var spikes: Array[Rect2] = []
var decor: Array = []             # [char, Vector2 bottom-centre]
var strips: Array = []            # [Rect2, depth] solid fill per row run, depth = tiles below the surface
var tops: Array[Rect2] = []       # exposed top edges (surface runs)
var sides: Array = []             # [Vector2 top, Vector2 bottom] exposed vertical edges
var ceilings: Array[Rect2] = []   # exposed undersides (stalactite drips)
var cave: Array[Rect2] = []       # open tiles that have rock somewhere above: the mine's back wall
var _grid: Array = []
var _seed := 0
var _glyph_font: Font = InkUI.font(true)
var cave_from_row := 9999        # rows at or below this are inside the mine even under open sky
var light_beams: Array = []       # [Vector2 top, Vector2 bottom, width] set by the level


func build(rows: Array, origin: Vector2) -> Dictionary:
	position = origin
	var w := 0
	for r in rows:
		w = maxi(w, (r as String).length())
	var grid: Array = []
	for r in rows:
		grid.append((r as String).rpad(w))
	var markers := {}
	var used := {}
	# greedy rect merge of solid tiles: grow right, then down while the run matches
	for y in grid.size():
		for x in w:
			if grid[y][x] != "#" or used.has(Vector2i(x, y)):
				continue
			var x2 := x
			while x2 + 1 < w and grid[y][x2 + 1] == "#" and not used.has(Vector2i(x2 + 1, y)):
				x2 += 1
			var y2 := y
			while y2 + 1 < grid.size():
				var ok := true
				for xx in range(x, x2 + 1):
					if grid[y2 + 1][xx] != "#" or used.has(Vector2i(xx, y2 + 1)):
						ok = false
						break
				if not ok:
					break
				y2 += 1
			for yy in range(y, y2 + 1):
				for xx in range(x, x2 + 1):
					used[Vector2i(xx, yy)] = true
			rects.append(Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, (y2 - y + 1) * TILE))
	for y in grid.size():
		var x := 0
		while x < w:
			var ch: String = grid[y][x]
			if ch == "=" or ch == "^":
				var x2 := x
				while x2 + 1 < w and grid[y][x2 + 1] == ch:
					x2 += 1
				if ch == "=":
					planks.append(Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, 12))
				else:
					spikes.append(Rect2(x * TILE, y * TILE + TILE * 0.45, (x2 - x + 1) * TILE, TILE * 0.55))
				x = x2 + 1
				continue
			if ch != " " and ch != "#":
				var at := Vector2((x + 0.5) * TILE, (y + 1) * TILE)
				if ch in "TLBNHC":
					decor.append([ch, at])
				else:
					if not markers.has(ch):
						markers[ch] = []
					markers[ch].append(at + origin)
			x += 1
	_edges(grid, w)
	_make_bodies()
	_seed = int(origin.x)
	queue_redraw()
	return {"markers": markers, "size": Vector2(w * TILE, grid.size() * TILE)}


func _edges(grid: Array, w: int) -> void:
	_grid = grid
	var solid := func(x: int, y: int) -> bool:
		return y >= 0 and y < grid.size() and x >= 0 and x < w and grid[y][x] == "#"
	# depth = tiles to the nearest open tile (multi-source BFS): rock is lit at
	# its skin and goes to solid ink inside, like the reference's black mass
	var depth := {}
	var queue: Array[Vector2i] = []
	for y in grid.size():
		for x in w:
			if not solid.call(x, y):
				depth[Vector2i(x, y)] = -1
				queue.append(Vector2i(x, y))
	var qi := 0
	while qi < queue.size():
		var c: Vector2i = queue[qi]
		qi += 1
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var n: Vector2i = c + d
			if n.x < 0 or n.y < 0 or n.x >= w or n.y >= grid.size() or depth.has(n):
				continue
			depth[n] = depth[c] + 1
			queue.append(n)
	for y in grid.size():
		for x in w:
			if not depth.has(Vector2i(x, y)):
				depth[Vector2i(x, y)] = 5
	# cave interior runs
	var roofed := {}
	for x in w:
		var seen := false
		for y in grid.size():
			if solid.call(x, y):
				seen = true
			elif seen or y >= cave_from_row:
				roofed[Vector2i(x, y)] = true
	for y in grid.size():
		var x := 0
		while x < w:
			if roofed.has(Vector2i(x, y)):
				var x2 := x
				while roofed.has(Vector2i(x2 + 1, y)):
					x2 += 1
				cave.append(Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, TILE))
				x = x2 + 1
			else:
				x += 1
		x = 0
		while x < w:
			if solid.call(x, y) and roofed.has(Vector2i(x, y + 1)):
				var x2 := x
				while solid.call(x2 + 1, y) and roofed.has(Vector2i(x2 + 1, y + 1)):
					x2 += 1
				ceilings.append(Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, TILE))
				x = x2 + 1
			else:
				x += 1
	for y in grid.size():
		var x := 0
		while x < w:
			if not solid.call(x, y):
				x += 1
				continue
			var d: int = mini(depth[Vector2i(x, y)], 5)
			var x2 := x
			while solid.call(x2 + 1, y) and mini(depth[Vector2i(x2 + 1, y)], 5) == d:
				x2 += 1
			strips.append([Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, TILE), d])
			x = x2 + 1
		x = 0
		while x < w:
			if solid.call(x, y) and not solid.call(x, y - 1):
				var x2 := x
				while solid.call(x2 + 1, y) and not solid.call(x2 + 1, y - 1):
					x2 += 1
				tops.append(Rect2(x * TILE, y * TILE, (x2 - x + 1) * TILE, TILE))
				x = x2 + 1
			else:
				x += 1
	for dir in [-1, 1]:
		for x in w:
			var y := 0
			while y < grid.size():
				if solid.call(x, y) and not solid.call(x + dir, y):
					var y2 := y
					while solid.call(x, y2 + 1) and not solid.call(x + dir, y2 + 1):
						y2 += 1
					var ex := (x + (1 if dir > 0 else 0)) * TILE
					sides.append([Vector2(ex, y * TILE), Vector2(ex, (y2 + 1) * TILE)])
					y = y2 + 1
				else:
					y += 1


func _make_bodies() -> void:
	var body := StaticBody2D.new()
	body.collision_layer = PFShot.WORLD
	add_child(body)
	for r in rects:
		var s := CollisionShape2D.new()
		var rs := RectangleShape2D.new()
		rs.size = r.size
		s.shape = rs
		s.position = r.get_center()
		body.add_child(s)
	for r in planks:
		var s := CollisionShape2D.new()
		var rs := RectangleShape2D.new()
		rs.size = r.size
		s.shape = rs
		s.position = r.get_center()
		s.one_way_collision = true
		body.add_child(s)


func spike_hit(p: Vector2) -> bool:
	var l := p - position
	for r in spikes:
		if r.grow(-6).has_point(l):
			return true
	return false


# ------------------------------------------------------------------ painting

func _draw() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = _seed
	if theme == "ink":
		_ink_cave(rng)
	for d in decor:
		if theme == "ink":
			_ink_decor(d[0], d[1], rng)
		else:
			_neon_decor(d[0], d[1], rng)
	if theme == "ink":
		_ink_ground(rng)
	else:
		_neon_ground(rng)
	for r in planks:
		if theme == "ink":
			_ink_plank(r, rng)
		else:
			_neon_plank(r)
	for r in spikes:
		_spikes(r, rng)


func _ink_cave(rng: RandomNumberGenerator) -> void:
	# the mine's back wall: a mid-grey wash, lighter toward shafts of daylight
	for r in cave:
		draw_rect(r, Color(0.43, 0.42, 0.41))
	for r in cave:
		if rng.randf() < 0.35:
			var x := r.position.x + rng.randf() * r.size.x
			draw_rect(Rect2(x, r.position.y, rng.randf_range(30, 120), TILE), Color(0.3, 0.29, 0.29, rng.randf_range(0.15, 0.4)))
		if rng.randf() < 0.12:
			# far scaffolding: faint posts and braces
			var x := r.position.x + rng.randf() * r.size.x
			draw_line(Vector2(x, r.position.y), Vector2(x, r.end.y), Color(PFHeroes.INK, 0.18), 6.0)
			draw_line(Vector2(x, r.position.y + 6), Vector2(x + 50, r.end.y - 6), Color(PFHeroes.INK, 0.12), 3.0)
	# daylight falling through the mine mouth and down the shafts
	for beam in light_beams:
		var a: Vector2 = beam[0]
		var b: Vector2 = beam[1]
		var w: float = beam[2]
		draw_colored_polygon(PackedVector2Array([a + Vector2(-w * 0.3, 0), a + Vector2(w * 0.3, 0), b + Vector2(w, 0),
			b + Vector2(-w, 0)]), Color(PFHeroes.PAPER, 0.16))
		draw_colored_polygon(PackedVector2Array([a + Vector2(-w * 0.12, 0), a + Vector2(w * 0.12, 0),
			b + Vector2(w * 0.45, 0), b + Vector2(-w * 0.45, 0)]), Color(PFHeroes.PAPER, 0.14))


func _chain_up(at: Vector2) -> void:
	var tx := int(at.x / TILE)
	var ty := int(at.y / TILE) - 1
	while ty > 0 and _grid[ty][tx] != "#":
		ty -= 1
	var top := (ty + 1) * TILE
	draw_line(Vector2(at.x, top), at + Vector2(0, 8), Color(PFHeroes.INK, 0.85), 2.0)
	for y in range(int(top), int(at.y), 14):
		draw_arc(Vector2(at.x, y), 3.5, 0, TAU, 6, Color(PFHeroes.INK, 0.75), 1.6)


func _ink_ground(rng: RandomNumberGenerator) -> void:
	var ink := PFHeroes.INK
	# rock is lit at its skin and soaks to solid ink inside
	for st in strips:
		var r: Rect2 = st[0]
		var k := float(st[1]) / 5.0
		draw_rect(r, Color(0.2, 0.195, 0.2).lerp(Color(0.035, 0.032, 0.036), clampf(k * 1.6, 0.0, 1.0)))
	for r in ceilings:
		# undersides: ragged ink lip with stalactite drips
		draw_line(Vector2(r.position.x, r.end.y), r.end, ink, 6.0)
		for i in int(r.size.x / 22.0):
			var x := r.position.x + rng.randf() * r.size.x
			var l := rng.randf_range(8, 46)
			draw_colored_polygon(PackedVector2Array([Vector2(x - 5, r.end.y), Vector2(x + 5, r.end.y), Vector2(x + 1, r.end.y + l)]),
				ink)
	for e in sides:
		var a: Vector2 = e[0]
		var b: Vector2 = e[1]
		draw_line(a, b, Color(ink, 0.8), 3.0)
		var drip := rng.randf_range(10, 34)
		draw_line(a + Vector2(0, 6), a + Vector2(0, 6 + drip), ink, 5.0)
		draw_circle(a + Vector2(0, 6 + drip), 3.0, ink)
	for r in tops:
		# soft shadow just under the lip, then a dry-brush stroke with paper flecks
		draw_rect(Rect2(r.position + Vector2(0, 4), Vector2(r.size.x, 14)), Color(ink, 0.35))
		var top := PackedVector2Array()
		var steps := maxi(3, int(r.size.x / 16.0))
		for i in steps + 1:
			top.append(Vector2(r.position.x + r.size.x * i / steps, r.position.y + rng.randf_range(-2.0, 3.0)))
		draw_polyline(top, ink, 9.0)
		for i in int(r.size.x / 9.0):
			var x := r.position.x + rng.randf() * r.size.x
			var y := r.position.y + rng.randf_range(-3.0, 5.0)
			draw_line(Vector2(x, y), Vector2(x + rng.randf_range(6, 18), y + rng.randf_range(-1, 1)),
				Color(PFHeroes.PAPER, rng.randf_range(0.05, 0.22)), 1.2)
		for i in int(r.size.x / 40.0):
			var gx := Vector2(r.position.x + rng.randf() * r.size.x, r.position.y - 2)
			for k in 3:
				draw_line(gx, gx + Vector2(rng.randf_range(-5, 5), -rng.randf_range(5, 11)), ink, 1.4)


func _ink_plank(r: Rect2, rng: RandomNumberGenerator) -> void:
	var ink := PFHeroes.INK
	draw_line(r.position + Vector2(-4, 4), Vector2(r.end.x + 4, r.position.y + 4 + rng.randf_range(-1, 1)), ink, 7.0)
	draw_line(r.position + Vector2(0, 11), Vector2(r.end.x, r.position.y + 11), Color(ink, 0.5), 2.0)
	var posts := maxi(2, int(r.size.x / 96.0) + 1)
	for i in posts:
		var x := r.position.x + 8.0 + (r.size.x - 16.0) * i / (posts - 1)
		draw_line(Vector2(x, r.position.y + 4), Vector2(x + rng.randf_range(-2, 2), r.position.y + 34), Color(ink, 0.8), 3.0)
		draw_line(Vector2(x - 4, r.position.y + 2), Vector2(x + 4, r.position.y + 8), PFHeroes.SHU, 2.0)


func _spikes(r: Rect2, rng: RandomNumberGenerator) -> void:
	var n := int(r.size.x / 12.0)
	var col := PFHeroes.INK if theme == "ink" else Color(1.0, 0.2, 0.6)
	for i in n:
		var x := r.position.x + (i + 0.5) * r.size.x / n
		var h := rng.randf_range(0.7, 1.0) * r.size.y
		draw_colored_polygon(PackedVector2Array([Vector2(x - 6, r.end.y), Vector2(x + rng.randf_range(-3, 3), r.end.y - h),
			Vector2(x + 6, r.end.y)]), col)
	if theme != "ink":
		draw_line(Vector2(r.position.x, r.end.y - 2), Vector2(r.end.x, r.end.y - 2), Color(1, 0.8, 0.2), 3.0)


func _ink_decor(ch: String, at: Vector2, rng: RandomNumberGenerator) -> void:
	var ink := PFHeroes.INK
	match ch:
		"T":   # torii
			var red := PFHeroes.SHU
			for sx in [-62.0, 62.0]:
				draw_line(at + Vector2(sx, 0), at + Vector2(sx * 0.92, -190), red, 13.0)
				draw_line(at + Vector2(sx - 6, 0), at + Vector2(sx * 0.92 - 6, -190), Color(ink, 0.35), 3.0)
				draw_rect(Rect2(at + Vector2(sx - 10, -14), Vector2(20, 14)), ink)
			draw_line(at + Vector2(-78, -150), at + Vector2(78, -150), red, 9.0)
			var beam := PackedVector2Array([at + Vector2(-104, -206), at + Vector2(0, -196), at + Vector2(104, -206),
				at + Vector2(96, -190), at + Vector2(-96, -190)])
			draw_colored_polygon(beam, ink)
			draw_line(at + Vector2(-86, -186), at + Vector2(86, -186), red, 8.0)
			draw_rect(Rect2(at + Vector2(-9, -186), Vector2(18, 34)), ink)
		"L":   # stone lantern
			draw_rect(Rect2(at + Vector2(-5, -40), Vector2(10, 40)), Color(ink, 0.85))
			draw_rect(Rect2(at + Vector2(-14, -46), Vector2(28, 7)), ink)
			draw_rect(Rect2(at + Vector2(-10, -64), Vector2(20, 18)), Color(0.24, 0.23, 0.23))
			draw_rect(Rect2(at + Vector2(-5, -60), Vector2(10, 10)), Color(1.0, 0.75, 0.4, 0.9))
			draw_colored_polygon(PackedVector2Array([at + Vector2(-20, -64), at + Vector2(0, -80), at + Vector2(20, -64)]), ink)
		"B":   # pine: brushed trunk and ink-cloud foliage
			var top := at + Vector2(rng.randf_range(-20, 20), -230)
			draw_polyline(PackedVector2Array([at, at + Vector2(-8, -80), at + Vector2(10, -150), top]), ink, 10.0)
			for i in 4:
				var c := top + Vector2(rng.randf_range(-70, 70), rng.randf_range(-10, 110))
				_wash(c, Vector2(rng.randf_range(50, 90), rng.randf_range(16, 26)), Color(ink, 0.8), rng)
				draw_line(c, c.lerp(top, 0.8), ink, 4.0)
		"C":
			_chain_up(at)
		"H":   # shrine hall silhouette
			draw_rect(Rect2(at + Vector2(-110, -120), Vector2(220, 120)), Color(0.2, 0.19, 0.19))
			for i in 5:
				draw_line(at + Vector2(-100 + i * 50, -118), at + Vector2(-100 + i * 50, 0), ink, 5.0)
			draw_colored_polygon(PackedVector2Array([at + Vector2(-170, -110), at + Vector2(-60, -190), at + Vector2(60, -190),
				at + Vector2(170, -110), at + Vector2(140, -120), at + Vector2(-140, -120)]), ink)
			draw_rect(Rect2(at + Vector2(-30, -90), Vector2(60, 30)), Color(PFHeroes.SHU, 0.9))


func _wash(c: Vector2, half: Vector2, col: Color, rng: RandomNumberGenerator) -> void:
	var pts := PackedVector2Array()
	for i in 14:
		var a := TAU * i / 14
		pts.append(c + Vector2(cos(a) * half.x, sin(a) * half.y) * rng.randf_range(0.8, 1.15))
	draw_colored_polygon(pts, col)


func _neon_ground(rng: RandomNumberGenerator) -> void:
	var cyan := Color(0.3, 0.95, 1.0)
	for st in strips:
		var r: Rect2 = st[0]
		var k := float(st[1]) / 5.0
		draw_rect(r, Color(0.08, 0.06, 0.15).lerp(Color(0.03, 0.02, 0.07), k))
		draw_line(r.position + Vector2(0, 24), r.position + Vector2(r.size.x, 24), Color(0.35, 0.3, 0.7, 0.1), 1.0)
		if rng.randf() < 0.35 and st[1] > 0:
			var x := r.position.x + rng.randf() * maxf(0.0, r.size.x - 24.0)
			draw_rect(Rect2(x, r.position.y + rng.randf_range(10, 34), rng.randf_range(8, 22), 3),
				Color(1.0, 0.2, 0.6, rng.randf_range(0.3, 0.8)))
	for e in sides:
		draw_line(e[0], e[1], Color(cyan, 0.4), 1.5)
	for r in tops:
		var a := r.position
		var b := Vector2(r.end.x, r.position.y)
		draw_line(a, b, Color(cyan, 0.25), 10.0)
		draw_line(a, b, cyan, 3.0)
		# ink still bleeds through the portal: dark drips from every surface
		for i in int(r.size.x / 90.0) + 1:
			var x := r.position.x + rng.randf() * r.size.x
			draw_line(Vector2(x, r.position.y + 3), Vector2(x, r.position.y + 3 + rng.randf_range(6, 26)),
				Color(PFHeroes.INK, 0.9), 4.0)


func _neon_plank(r: Rect2) -> void:
	var mag := Color(1.0, 0.25, 0.7)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 8)), Color(0.08, 0.06, 0.14))
	draw_line(r.position, Vector2(r.end.x, r.position.y), Color(mag, 0.3), 9.0)
	draw_line(r.position, Vector2(r.end.x, r.position.y), mag, 2.5)
	for x in range(int(r.position.x) + 12, int(r.end.x), 24):
		draw_line(Vector2(x, r.position.y + 8), Vector2(x - 6, r.position.y + 16), Color(mag, 0.4), 1.5)


func _neon_decor(ch: String, at: Vector2, rng: RandomNumberGenerator) -> void:
	match ch:
		"N":   # holo sign with a kanji
			var h := rng.randf_range(140, 220)
			draw_line(at, at + Vector2(0, -h), Color(0.15, 0.12, 0.25), 5.0)
			var box := Rect2(at + Vector2(-26, -h - 70), Vector2(52, 70))
			var col := [Color(1.0, 0.25, 0.7), Color(0.3, 0.95, 1.0), Color(1.0, 0.8, 0.2)][rng.randi() % 3] as Color
			draw_rect(box.grow(6), Color(col, 0.12))
			draw_rect(box, Color(0.05, 0.04, 0.1))
			draw_rect(box, col, false, 2.0)
			var glyph := ["門", "光", "影", "電"][rng.randi() % 4] as String
			draw_string(_glyph_font, box.position + Vector2(8, 52), glyph, HORIZONTAL_ALIGNMENT_LEFT, -1, 36, col)
		"L":   # beacon post
			draw_rect(Rect2(at + Vector2(-4, -70), Vector2(8, 70)), Color(0.12, 0.1, 0.2))
			draw_circle(at + Vector2(0, -74), 9.0, Color(0.3, 0.95, 1.0, 0.25))
			draw_circle(at + Vector2(0, -74), 4.0, Color(0.3, 0.95, 1.0))
		"T":   # torii rebuilt as a hologram: the shrine, remembered
			var c := Color(1.0, 0.3, 0.25, 0.55)
			for sx in [-62.0, 62.0]:
				draw_line(at + Vector2(sx, 0), at + Vector2(sx * 0.92, -190), c, 3.0)
			draw_line(at + Vector2(-104, -204), at + Vector2(104, -204), c, 3.0)
			draw_line(at + Vector2(-80, -150), at + Vector2(80, -150), c, 2.0)
			for y in range(-190, 0, 12):
				draw_line(at + Vector2(-70, y), at + Vector2(70, y), Color(c, 0.06), 1.0)
		_:
			pass
