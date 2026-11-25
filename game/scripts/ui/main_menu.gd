## Main menu: ink title, character + weapon select with a live 3D preview
## (any character can wield any weapon), controls, play/quit.
extends Node3D

var _preview: Node3D
var _mount: WeaponMount
var _char_label: Label
var _weap_label: Label
var _desc: Label
var _help: Control
var _pivot: Node3D


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	InkWorld.build(self, false, true)
	var floor := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(60, 60)
	floor.mesh = pm
	floor.material_override = load("res://materials/M_Env_Ground.tres")
	add_child(floor)
	_pivot = Node3D.new()
	add_child(_pivot)
	var cam := Camera3D.new()
	cam.fov = 34
	add_child(cam)
	cam.position = Vector3(-1.3, 1.35, 4.6)
	cam.look_at(Vector3(-0.65, 1.0, 0))
	_build_ui()
	_refresh()
	if "--menu-shot" in OS.get_cmdline_user_args():
		await get_tree().create_timer(1.2).timeout
		await RenderingServer.frame_post_draw
		var p := ProjectSettings.globalize_path("res://") + "../build/playtest/menu.png"
		DirAccess.make_dir_recursive_absolute(p.get_base_dir())
		get_viewport().get_texture().get_image().save_png(p)
		print("[menu] ", p)
		get_tree().quit()


func _process(delta: float) -> void:
	_pivot.rotation.y += delta * 0.35


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(root)
	var col := VBoxContainer.new()
	col.position = Vector2(90, 90)
	col.add_theme_constant_override("separation", 14)
	root.add_child(col)
	col.add_child(InkUI.label("墨の影", 96))
	col.add_child(InkUI.label("SUMI NO KAGE", 26, Color(InkUI.INK, 0.8)))
	col.add_child(_spacer(24))
	_char_label = _selector(col, "Character", func(d): _cycle_char(d))
	_weap_label = _selector(col, "Weapon", func(d): _cycle_weapon(d))
	_desc = InkUI.label("", 16, Color(InkUI.INK, 0.7), false)
	col.add_child(_desc)
	col.add_child(_spacer(20))
	var play := InkUI.button("戦う  Play", 34)
	play.pressed.connect(Game.start_game)
	col.add_child(play)
	var ctrl := InkUI.button("Controls", 24)
	ctrl.pressed.connect(func(): _help.visible = not _help.visible)
	col.add_child(ctrl)
	var quit := InkUI.button("Quit", 24)
	quit.pressed.connect(func(): get_tree().quit())
	col.add_child(quit)
	play.grab_focus()
	_help = InkUI.label("Move  WASD / left stick        Look  mouse\nLight attack  LMB   (chain 2–3 hits)\n"
		+ "Heavy attack  RMB\nBlock  hold Shift   —   tap just before a hit to PARRY\nDodge  Space   (invulnerable while rolling)\n"
		+ "Phantom Step  E   (teleport in the move direction)\nFinisher  F / LMB on a staggered foe\n"
		+ "Lock-on  Tab      Switch weapon  1–6      Pause  Esc", 18, InkUI.INK, false)
	_help.position = Vector2(90, 690)
	_help.visible = false
	root.add_child(_help)
	var red := ColorRect.new()  # the hanko seal
	red.color = InkUI.SHU
	red.size = Vector2(34, 34)
	red.position = Vector2(400, 112)
	root.add_child(red)


func _spacer(h: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	return c


func _selector(parent: Control, title: String, cb: Callable) -> Label:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	parent.add_child(row)
	var t := InkUI.label(title, 18, Color(InkUI.INK, 0.6), false)
	t.custom_minimum_size = Vector2(110, 0)
	row.add_child(t)
	var l := InkUI.button("‹", 28)
	l.pressed.connect(func(): cb.call(-1))
	row.add_child(l)
	var name := InkUI.label("", 26)
	name.custom_minimum_size = Vector2(330, 0)
	name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	row.add_child(name)
	var r := InkUI.button("›", 28)
	r.pressed.connect(func(): cb.call(1))
	row.add_child(r)
	return name


func _cycle_char(d: int) -> void:
	var i := (Game.ROSTER.find(Game.character) + d + Game.ROSTER.size()) % Game.ROSTER.size()
	Game.character = Game.ROSTER[i]
	Game.weapon = Game.character.default_weapon
	_refresh()


func _cycle_weapon(d: int) -> void:
	var i := (Game.WEAPONS.find(Game.weapon) + d + Game.WEAPONS.size()) % Game.WEAPONS.size()
	Game.weapon = Game.WEAPONS[i]
	_refresh()


func _refresh() -> void:
	_char_label.text = Game.character.display_name
	_weap_label.text = Game.weapon.display_name
	var m: Dictionary = Game.moveset(Game.weapon)
	_desc.text = "%s style · %d-hit chain · reach %.1f m" % [Game.weapon.move_family, (m["light"] as Array).size(),
		float((m["light"] as Array)[0]["reach"])]
	if _preview:
		_preview.queue_free()
	_preview = Game.character.scene.instantiate()
	_pivot.add_child(_preview)
	_mount = WeaponMount.new()
	_mount.skeleton = _preview.find_children("*", "Skeleton3D", true, false)[0]
	_preview.add_child(_mount)
	_mount.equip(Game.weapon, true)
	var ap: AnimationPlayer = _preview.find_children("*", "AnimationPlayer", true, false)[0]
	ap.play(m["stance"])
