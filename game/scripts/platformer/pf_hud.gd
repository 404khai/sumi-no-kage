## HUD + hero select + title cards, all drawn in one Control so the look stays
## hand-made: brush-diamond health pips, the class kanji stamped in its colour,
## ink-drop counter, and a centred card when you enter a zone or clear a stage.
class_name PFHud
extends Control

var hero: Dictionary = PFHeroes.SWORDSMAN
var hp := 6
var max_hp := 6
var orbs := 0
var orbs_total := 0
var zone := 0
var boss_name := ""
var boss_ratio := 0.0
var selecting := true
var select_index := 0
var _card_title := ""
var _card_sub := ""
var _card_t := 0.0
var _hint_t := 9.0
var _time := 0.0
var _previews: Array[PFRig] = []
var _font: Font
var _sans: Font


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_font = InkUI.font(true)
	_sans = InkUI.font(false)
	for i in 3:
		var r := PFRig.new()
		r.set_hero(PFHeroes.ROSTER[i])
		r.scale = Vector2(2.6, 2.6)
		add_child(r)
		_previews.append(r)
	_layout_previews()


func _layout_previews() -> void:
	var s := get_viewport_rect().size
	for i in 3:
		_previews[i].position = Vector2(s.x * 0.5 + (i - 1) * 360.0, s.y * 0.5 + 150.0)
		_previews[i].visible = selecting


func card(title: String, sub: String, t := 3.2) -> void:
	_card_title = title
	_card_sub = sub
	_card_t = t


func _process(delta: float) -> void:
	_time += delta
	_card_t = maxf(0.0, _card_t - delta)
	if not selecting:
		_hint_t = maxf(0.0, _hint_t - delta)
	_layout_previews()
	for i in 3:
		var r := _previews[i]
		var on := i == select_index
		r.state = "run" if on else "idle"
		r.speed_ratio = 0.35 if on else 0.0
		r.modulate = Color.WHITE if on else Color(0.62, 0.6, 0.62)
	queue_redraw()


func _draw() -> void:
	var s := get_viewport_rect().size
	if selecting:
		_draw_select(s)
		return
	# a torn paper strip behind the HUD so it reads over black rock
	if zone == 0:
		draw_colored_polygon(PackedVector2Array([Vector2(14, 14), Vector2(310, 10), Vector2(296, 98), Vector2(18, 102)]),
			Color(PFHeroes.PAPER, 0.88))
		draw_colored_polygon(PackedVector2Array([Vector2(s.x - 176, 14), Vector2(s.x - 20, 18), Vector2(s.x - 26, 80),
			Vector2(s.x - 170, 76)]), Color(PFHeroes.PAPER, 0.88))
	if boss_name != "":
		var bw := 640.0
		var bx := (s.x - bw) * 0.5
		var by := 150.0
		draw_rect(Rect2(bx - 16, by - 40, bw + 32, 70), Color(PFHeroes.INK, 0.8))
		draw_string(_font, Vector2(bx, by - 12), boss_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, PFHeroes.PAPER)
		draw_rect(Rect2(bx, by, bw, 12), Color(PFHeroes.PAPER, 0.2))
		draw_rect(Rect2(bx, by, bw * boss_ratio, 12), PFHeroes.SHU)
		# brush-stroke ends on the bar
		draw_circle(Vector2(bx + bw * boss_ratio, by + 6), 6.0, PFHeroes.SHU)
	# hero stamp
	var stamp := Rect2(28, 24, 64, 64)
	draw_rect(stamp.grow(3), PFHeroes.INK)
	draw_rect(stamp, hero.body)
	draw_string(_font, stamp.position + Vector2(8, 52), hero.kanji, HORIZONTAL_ALIGNMENT_LEFT, -1, 46, PFHeroes.INK)
	draw_string(_font, Vector2(108, 48), hero.name.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, _ui_ink())
	for i in max_hp:
		var c := Vector2(118 + i * 26, 72)
		var pts := PackedVector2Array([c + Vector2(0, -10), c + Vector2(9, 0), c + Vector2(0, 10), c + Vector2(-9, 0)])
		draw_colored_polygon(pts, PFHeroes.INK)
		if i < hp:
			var inner := PackedVector2Array([c + Vector2(0, -6), c + Vector2(5, 0), c + Vector2(0, 6), c + Vector2(-5, 0)])
			draw_colored_polygon(inner, PFHeroes.SHU if zone == 0 else Color(1.0, 0.25, 0.65))
	# ink-drop counter
	var oc := Vector2(s.x - 150, 52)
	draw_circle(oc, 13.0, PFHeroes.INK)
	draw_colored_polygon(PackedVector2Array([oc + Vector2(-9, -6), oc + Vector2(0, -24), oc + Vector2(9, -6)]), PFHeroes.INK)
	draw_circle(oc + Vector2(-4, -3), 3.0, hero.glow)
	draw_string(_font, oc + Vector2(24, 12), "%d / %d" % [orbs, orbs_total], HORIZONTAL_ALIGNMENT_LEFT, -1, 26, _ui_ink())
	if _hint_t > 0.0:
		var a := clampf(_hint_t, 0.0, 1.0)
		draw_string(_sans, Vector2(28, s.y - 28),
			"A/D move · Space jump (hold = higher, wall-jump) · Shift dash · J / LMB attack · K / RMB special · W/S aim · Q or 1–3 swap hero · Esc menu",
			HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(_ui_ink(), 0.8 * a))
	if _card_t > 0.0:
		var a := clampf(_card_t, 0.0, 1.0) * clampf((3.2 - _card_t) * 3.0, 0.0, 1.0)
		var y := s.y * 0.3
		draw_rect(Rect2(0, y - 70, s.x, 120), Color(PFHeroes.INK, 0.75 * a))
		draw_line(Vector2(s.x * 0.5 - 300, y + 14), Vector2(s.x * 0.5 + 300, y + 14), Color(hero.glow, a), 2.0)
		draw_string(_font, Vector2(0, y), _card_title, HORIZONTAL_ALIGNMENT_CENTER, s.x, 52, Color(PFHeroes.PAPER, a))
		draw_string(_sans, Vector2(0, y + 26 + 10), _card_sub, HORIZONTAL_ALIGNMENT_CENTER, s.x, 18, Color(PFHeroes.PAPER, 0.8 * a))


func _ui_ink() -> Color:
	return PFHeroes.INK if zone == 0 else PFHeroes.PAPER


func _draw_select(s: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, s), Color(PFHeroes.PAPER, 0.86))
	draw_string(_font, Vector2(0, 120), "墨の影  ·  影渡り", HORIZONTAL_ALIGNMENT_CENTER, s.x, 64, PFHeroes.INK)
	draw_string(_sans, Vector2(0, 162), "SUMI NO KAGE — PLATFORMER PROTOTYPE · choose who crosses", HORIZONTAL_ALIGNMENT_CENTER,
		s.x, 18, Color(PFHeroes.INK, 0.7))
	for i in 3:
		var h: Dictionary = PFHeroes.ROSTER[i]
		var cx := s.x * 0.5 + (i - 1) * 360.0
		var on := i == select_index
		var box := Rect2(cx - 150, s.y * 0.5 - 230, 300, 480)
		# a slanted colour block behind each hero, like the reference panels
		var sl := 40.0
		var panel := PackedVector2Array([box.position + Vector2(sl, 0), box.position + Vector2(box.size.x, 0),
			box.end - Vector2(sl, 0), Vector2(box.position.x, box.end.y)])
		draw_colored_polygon(panel, Color(h.body, 0.9 if on else 0.25))
		if on:
			var o := PackedVector2Array()
			for p in panel:
				o.append(p)
			o.append(panel[0])
			draw_polyline(o, PFHeroes.INK, 5.0)
			draw_polyline(o, h.glow, 2.0)
		draw_string(_font, Vector2(cx - 150, box.position.y + 74), h.kanji, HORIZONTAL_ALIGNMENT_CENTER, 300, 64,
			Color(PFHeroes.INK, 0.9 if on else 0.4))
		draw_string(_font, Vector2(cx - 150, box.end.y + 44), h.name.to_upper(), HORIZONTAL_ALIGNMENT_CENTER, 300, 28,
			PFHeroes.INK)
		if on:
			draw_string(_sans, Vector2(cx - 210, box.end.y + 76), h.blurb, HORIZONTAL_ALIGNMENT_CENTER, 420, 15,
				Color(PFHeroes.INK, 0.75))
	draw_string(_sans, Vector2(0, s.y - 40), "← / → or 1–3 to choose   ·   Space / Enter to begin   ·   you can swap heroes any time with Q",
		HORIZONTAL_ALIGNMENT_CENTER, s.x, 18, Color(PFHeroes.INK, 0.8))
