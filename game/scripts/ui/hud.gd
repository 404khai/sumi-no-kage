## In-game HUD: health and posture brush bars, weapon, foes remaining,
## finisher prompt, pause menu, victory / defeat screens.
class_name Hud
extends CanvasLayer

var player: Player
var _hp_fill: ColorRect
var _post_fill: ColorRect
var _weapon: Label
var _foes: Label
var _prompt: Label
var _center: VBoxContainer
var _pause: VBoxContainer
var _help: Label
const BAR_W := 320.0


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var tl := VBoxContainer.new()
	tl.position = Vector2(36, 30)
	root.add_child(tl)
	tl.add_child(InkUI.label(Game.character.display_name, 26))
	var hp := InkUI.bar(BAR_W, 12, InkUI.INK)
	_hp_fill = hp[1]
	tl.add_child(hp[0])
	var po := InkUI.bar(BAR_W * 0.6, 5, InkUI.SHU)
	_post_fill = po[1]
	tl.add_child(po[0])
	_weapon = InkUI.label("", 18)
	tl.add_child(_weapon)
	_foes = InkUI.label("", 20)
	_foes.anchor_left = 1.0
	_foes.anchor_right = 1.0
	_foes.position = Vector2(-260, 34)
	root.add_child(_foes)
	_prompt = InkUI.label("F — 止め  Finisher", 26, InkUI.SHU)
	_prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.position += Vector2(-120, -140)
	_prompt.visible = false
	root.add_child(_prompt)
	_help = InkUI.label("WASD move · Mouse look · LMB light · RMB heavy · Shift block (tap = parry) · Space dodge\n"
		+ "E Phantom Step · F finisher · Tab lock-on · 1–6 weapons · Esc pause", 15, Color(InkUI.INK, 0.75), false)
	_help.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_help.position = Vector2(36, -64)
	root.add_child(_help)
	_center = VBoxContainer.new()
	_center.set_anchors_preset(Control.PRESET_CENTER)
	_center.alignment = BoxContainer.ALIGNMENT_CENTER
	_center.visible = false
	root.add_child(_center)
	_pause = VBoxContainer.new()
	_pause.set_anchors_preset(Control.PRESET_CENTER)
	_pause.visible = false
	root.add_child(_pause)
	_pause.add_child(InkUI.label("一時停止  Paused", 40))
	var r := InkUI.button("Resume")
	r.pressed.connect(toggle_pause)
	_pause.add_child(r)
	var m := InkUI.button("Main Menu")
	m.pressed.connect(Game.to_menu)
	_pause.add_child(m)
	var q := InkUI.button("Quit")
	q.pressed.connect(func(): get_tree().quit())
	_pause.add_child(q)


func _process(_d: float) -> void:
	if player == null:
		return
	_hp_fill.size.x = BAR_W * clampf(player.health / player.max_health, 0, 1)
	_post_fill.size.x = BAR_W * 0.6 * clampf(player.posture, 0, 1)
	_weapon.text = "%s  ·  %s" % [player.weapon.display_name, player.weapon.move_family]
	var alive := 0
	var finisher := false
	for n in get_tree().get_nodes_in_group("enemies"):
		var e := n as Fighter
		if e.state != Fighter.State.DEAD:
			alive += 1
			if e.state == Fighter.State.STAGGER and e.global_position.distance_to(player.global_position) < 3.2:
				finisher = true
	_foes.text = "残 %d  foes remain" % alive
	_prompt.visible = finisher


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") and not _center.visible:
		toggle_pause()


func toggle_pause() -> void:
	var p := not get_tree().paused
	get_tree().paused = p
	_pause.visible = p
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if p else Input.MOUSE_MODE_CAPTURED


func end_screen(victory: bool) -> void:
	_center.visible = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	for c in _center.get_children():
		c.queue_free()
	_center.add_child(InkUI.label("勝利  Victory" if victory else "敗北  Defeated", 56,
		InkUI.INK if victory else InkUI.SHU))
	var again := InkUI.button("Fight again")
	again.pressed.connect(Game.start_game)
	_center.add_child(again)
	var menu := InkUI.button("Main Menu")
	menu.pressed.connect(Game.to_menu)
	_center.add_child(menu)
	again.grab_focus()
