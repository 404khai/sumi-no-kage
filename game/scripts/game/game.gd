## Playable slice: the Kurogane Shrine courtyard, the chosen character and
## weapon, and a band of ashen sentinels. Win by defeating them all.
## CLI capture: godot --path game res://scenes/game/game.tscn -- --autoplay --shots=1.5,4,7 --out=<dir>
extends Node3D

const SHRINE := preload("res://assets/environments/kurogane_shrine/kurogane_shrine_blockout.glb")
const ENEMIES := [  # marker, character index, weapon id
	["Marker_Patrol_A", 1, "halberd"],
	["Marker_Patrol_B", 2, "greatsword"],
	["Marker_Sentry_Hall", 1, "naginata"],
	["Marker_Ambush_Bridge", 2, "broadsword"],
	["Marker_Courtyard", 1, "greatsword"],
]

var player: Player
var hud: Hud
var _over := false


func _ready() -> void:
	InkWorld.build(self)
	var shrine := SHRINE.instantiate()
	add_child(shrine)
	var start := _marker(shrine, "Marker_PlayerStart", Vector3(0, 0.5, 26))
	player = Player.new()
	add_child(player)
	player.global_position = start + Vector3(0, 0.5, 0)
	player.setup(Game.character, Game.weapon)
	player.died.connect(func(_f): _finish(false))
	for spec in ENEMIES:
		var e := Enemy.new()
		add_child(e)
		e.global_position = _marker(shrine, spec[0], Vector3(randf_range(-4, 4), 0.5, 6)) + Vector3(0, 0.6, 0)
		var w: WeaponDefinition = Game.WEAPONS.filter(func(x): return String(x.id) == spec[2])[0]
		e.setup(Game.ROSTER[spec[1]], w)
		e.model.rotation.y = PI
		e.died.connect(func(_f): _check_victory())
	hud = Hud.new()
	hud.player = player
	add_child(hud)
	_capture_mode()


func _marker(root: Node, name: String, fallback: Vector3) -> Vector3:
	var n := root.find_child(name, true, false) as Node3D
	return n.global_position if n else fallback


func _check_victory() -> void:
	await get_tree().process_frame
	for n in get_tree().get_nodes_in_group("enemies"):
		if (n as Fighter).state != Fighter.State.DEAD:
			return
	_finish(true)


func _finish(victory: bool) -> void:
	if _over:
		return
	_over = true
	await get_tree().create_timer(1.6).timeout
	hud.end_screen(victory)
	print("[game] %s" % ("VICTORY" if victory else "DEFEAT"))


func _capture_mode() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	if not args.has("shots"):
		return
	var out: String = args.get("out", ProjectSettings.globalize_path("res://") + "../build/playtest")
	DirAccess.make_dir_recursive_absolute(out)
	var t := 0.0
	for s in String(args["shots"]).split(","):
		await get_tree().create_timer(float(s) - t).timeout
		t = float(s)
		await RenderingServer.frame_post_draw
		var path := out.path_join("play_%05.1fs.png" % t)
		get_viewport().get_texture().get_image().save_png(path)
		var alive := get_tree().get_nodes_in_group("enemies").filter(
			func(n): return (n as Fighter).state != Fighter.State.DEAD).size()
		print("[playtest] t=%.1f hp=%.0f state=%s foes=%d fps=%d -> %s" % [t, player.health,
			Fighter.State.keys()[player.state], alive, Engine.get_frames_per_second(), path])
	get_tree().quit()
