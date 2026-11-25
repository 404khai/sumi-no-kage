## Small helpers for the ink-on-paper UI style.
class_name InkUI
extends RefCounted

const INK := Color(0.06, 0.055, 0.06)
const PAPER := Color(0.92, 0.905, 0.865)
const SHU := Color(0.62, 0.11, 0.08)


static func font(serif := true) -> Font:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", "Georgia", "serif"]) \
		if serif else PackedStringArray(["Hiragino Sans", "Helvetica Neue", "sans-serif"])
	return f


static func label(text: String, size := 22, color := INK, serif := true) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font(serif))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func button(text: String, size := 26) -> Button:
	var b := Button.new()
	b.text = text
	b.flat = true
	b.focus_mode = Control.FOCUS_ALL
	b.add_theme_font_override("font", font())
	b.add_theme_font_size_override("font_size", size)
	for s in ["font_color", "font_focus_color"]:
		b.add_theme_color_override(s, INK)
	b.add_theme_color_override("font_hover_color", SHU)
	b.add_theme_color_override("font_pressed_color", SHU)
	b.add_theme_color_override("font_focus_color", SHU)
	return b


static func bar(width: float, height: float, fill: Color) -> Array:
	var bg := ColorRect.new()
	bg.color = Color(INK, 0.18)
	bg.custom_minimum_size = Vector2(width, height)
	var fg := ColorRect.new()
	fg.color = fill
	fg.size = Vector2(width, height)
	bg.add_child(fg)
	return [bg, fg]
