## Platformer stage. Zone 0 is the Kurogane Shrine and the mine beneath it, in
## ink: a vertical descent (layout after docs/reference/platformer/layout.jpeg).
## Shrine yard → right shaft → passage held by the Oni Captain → left shaft of
## maces and lifts → the pool where the Drowned Maw lives. Zone 1 (neon, Higan)
## sits behind the rift, which stays sealed for now (PORTAL_LOCKED).
##
## Map legend:  # rock   = one-way plank   ^ spikes   w ink pool   S spawn   K checkpoint
##   o ink drop   c crawler   f flyer   t bell turret   g yari goon   a archer goon
##   M swinging mace (anchor)   v / h chain lift (vertical / horizontal)
##   X arena gate (closes behind you)   Y lid (opens when the mini-boss falls)
##   O Oni Captain   Z Drowned Maw   P portal   G goal
##   decor: T torii   L lantern/beacon   B pine   H shrine hall   N holo sign   C chain to ceiling
##
## Capture for docs/tests:  godot --path game res://scenes/platformer/platformer.tscn -- --pf-shots
class_name PFLevel
extends Node2D

const ZONE_SHRINE := [
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                                          #",
	"#                                       oo                 #",
	"#  P    S     T    L     H   g  B    L                     #",
	"############################################        ########",
	"######################################                    ##",
	"######################################                    ##",
	"######################################                    ##",
	"######################################     C o o C        ##",
	"######################################     =======        ##",
	"######################################                    ##",
	"######################################                    ##",
	"######################################                 t  ##",
	"######################################               #######",
	"######################################               #######",
	"######################################                    ##",
	"######################################C  g                ##",
	"######################################=======             ##",
	"######################################                    ##",
	"######################################                    ##",
	"######################################                    ##",
	"######################################            v       ##",
	"######################################             f      ##",
	"######################################                    ##",
	"######################################              o     ##",
	"######################################        =========== ##",
	"######################################                    ##",
	"######################################                    ##",
	"######################################  c                 ##",
	"###                                   #####               ##",
	"###                                   #####               ##",
	"###                                             C  oo  C  ##",
	"###                                             ========  ##",
	"###        o            o   o    X                        ##",
	"###      =====        =====      X                        ##",
	"###                              X                        ##",
	"###                              X                        ##",
	"###              O               X  L       g     K     L ##",
	"###YYYYYY###################################################",
	"##                     #####################################",
	"##                     #####################################",
	"##                     #####################################",
	"##        C  o  C      #####################################",
	"##        =======      #####################################",
	"##                     #####################################",
	"##           M         #####################################",
	"##  g                  #####################################",
	"#######                #####################################",
	"#######                #####################################",
	"##                     #####################################",
	"##             o       #####################################",
	"##       =========     #####################################",
	"##                     #####################################",
	"##                     #####################################",
	"##                  a  #####################################",
	"##                ##########################################",
	"##      h         ##########################################",
	"##            f        #####################################",
	"##                     #####################################",
	"##  K                  #####################################",
	"#########              #####################################",
	"#########              #####################################",
	"##                     #####################################",
	"##         C   g   C   #####################################",
	"##         =========   #####################################",
	"##       M             #####################################",
	"##                     #####################################",
	"##    o                #####################################",
	"## ========            #####################################",
	"##                     #####################################",
	"##               o     #####################################",
	"##            ======== #####################################",
	"##                     #####################################",
	"##                                 #########################",
	"##                                 #########################",
	"##                                 #########################",
	"##                                 #########################",
	"##                                 #########################",
	"##               =====             #########################",
	"##                                 #########################",
	"##       =====           =====     #########################",
	"##                                 #########################",
	"## K                             L #########################",
	"######                         #############################",
	"######            Z            #############################",
	"######wwwwwwwwwwwwwwwwwwwwwwwww#############################",
	"############################################################",
	"############################################################",
	"############################################################",
]

const ZONE_NEON := [
	"                                                                                                                 ",
	"                                                                                                                 ",
	"                                                   o o                                                           ",
	"                                                  =====                       f                                  ",
	"                                         o                                                    o o o              ",
	"                                ##     ====             f         ====                       =======             ",
	"                    f           ##                              t ####                                           ",
	"           o o                  ##         ====       ####        ####           ####                    #####   ",
	"          =====            t    ##                    ####        ####     o     ####         t          #####   ",
	"                       ######   ##   c       N        ####   N    ####   ====    ####   N   #####        #####   ",
	"      T           N    ######   ##########          ######        ####           ####       #####   L    #####  G",
	"                       ######                                                                                    ",
	"  S        L      K    ######     c      K       c          c          K      c             c    L        L      ",
	"######################^^^^^^##########^^^^##############    #####################^^^^^^^#########################",
	"#################################################   ##############   ######################################  #####",
	"#################################################   ##############   ##############################################",
	"#################################################   ##############   ##############################################",
	"#################################################   ##############   ##############################################",
]

const WIPE_TIME := 0.55
const PORTAL_LOCKED := true

var hero: PFHero
var fx: PFFx
var hud: PFHud
var cam: Camera2D
var sky_mat: ShaderMaterial
var post_mat: ShaderMaterial
var portal_mat: ShaderMaterial
var zones: Array = []          # [{terrain, origin, size, backdrop, markers}]
var zone := 0
var checkpoint := Vector2.ZERO
var orbs: Array = []           # [{pos, zone, taken}]
var checkpoints: Array = []    # [{pos, zone, lit}]
var portal_pos := Vector2.ZERO
var goal_pos := Vector2.ZERO
var _busy := false
var _cleared := false
var _time := 0.0
var _world_art: Node2D
var _bot_held := {}
var gate: PFHazards.Gate
var lid: PFHazards.Gate
var oni: PFOni
var maw: PFMaw
var boss: Node              # the boss currently fighting, for the HUD bar
var pool := Rect2()
var _oni_done := false
var _sealed_told := false


func _ready() -> void:
	_bind_inputs()
	RenderingServer.set_default_clear_color(PFHeroes.PAPER)
	var noise: Texture2D = load("res://textures/ink/ink_wash_noise.png")
	# sky (behind everything)
	var sky_layer := CanvasLayer.new()
	sky_layer.layer = -20
	add_child(sky_layer)
	var sky := ColorRect.new()
	sky.set_anchors_preset(Control.PRESET_FULL_RECT)
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/platformer/pf_sky.gdshader")
	sky_mat.set_shader_parameter("wash_noise", noise)
	sky.material = sky_mat
	sky_layer.add_child(sky)
	# zones
	var origin := Vector2.ZERO
	for i in 2:
		var rows: Array = ZONE_SHRINE if i == 0 else ZONE_NEON
		var theme := "ink" if i == 0 else "neon"
		var back := PFBackdrop.new()
		back.setup(theme, origin.y + (11 if i == 0 else 13) * PFTerrain.TILE)
		back.visible = i == 0
		add_child(back)
		var t := PFTerrain.new()
		t.theme = theme
		t.cave_from_row = 12 if i == 0 else 9999
		var info := t.build(rows, origin)
		zones.append({"terrain": t, "origin": origin, "size": info.size, "backdrop": back, "markers": info.markers})
		origin.x += info.size.x + 40 * PFTerrain.TILE
	_world_art = _ArtScript.new()
	_world_art.set("level", self)
	add_child(_world_art)
	for z in zones:
		add_child(z.terrain)
	fx = PFFx.new()
	# hero
	hero = PFHero.new()
	hero.level = self
	hero.fx = fx
	add_child(hero)
	add_child(fx)
	for zi in zones.size():
		var m: Dictionary = zones[zi].markers
		for p in m.get("o", []):
			orbs.append({"pos": p + Vector2(0, -24), "zone": zi, "taken": false})
		for p in m.get("K", []):
			checkpoints.append({"pos": p, "zone": zi, "lit": false})
		for k in ["c", "f", "t", "g", "a"]:
			for p in m.get(k, []):
				_spawn_enemy(k, p, zi)
	_build_set_pieces(zones[0].markers)
	portal_pos = zones[0].markers["P"][0]
	goal_pos = zones[1].markers["G"][0]
	checkpoint = zones[0].markers["S"][0]
	hero.global_position = checkpoint
	hero.died.connect(_on_died)
	_build_portal()
	# camera
	cam = Camera2D.new()
	cam.zoom = Vector2(1.5, 1.5)
	cam.position_smoothing_enabled = true
	cam.position_smoothing_speed = 7.0
	add_child(cam)
	_apply_zone_limits()
	cam.global_position = hero.global_position
	# HUD + post
	var ui := CanvasLayer.new()
	ui.layer = 5
	add_child(ui)
	hud = PFHud.new()
	ui.add_child(hud)
	hud.orbs_total = orbs.size()
	hero.hp_changed.connect(func(h, m): hud.hp = h; hud.max_hp = m)
	hero.swapped.connect(func(h): hud.hero = h)
	hero.set_hero(PFHeroes.SWORDSMAN, false)
	var post_layer := CanvasLayer.new()
	post_layer.layer = 4
	add_child(post_layer)
	var post := ColorRect.new()
	post.set_anchors_preset(Control.PRESET_FULL_RECT)
	post.mouse_filter = Control.MOUSE_FILTER_IGNORE
	post_mat = ShaderMaterial.new()
	post_mat.shader = load("res://shaders/platformer/pf_post.gdshader")
	post_mat.set_shader_parameter("paper_grain", load("res://textures/ink/paper_grain.png"))
	post_mat.set_shader_parameter("wash_noise", noise)
	post.material = post_mat
	post_mat.set_shader_parameter("wipe", 0.0)
	post_layer.add_child(post)
	hero.input_enabled = false
	if "--pf-shots" in OS.get_cmdline_user_args():
		_capture()


func _spawn_enemy(kind: String, at: Vector2, zi: int) -> void:
	var e := PFEnemy.new()
	e.kind = {"g": "goon", "a": "bowgoon", "c": "crawler", "f": "flyer", "t": "turret"}.get(kind, kind)
	e.theme = "ink" if zi == 0 else "neon"
	e.radius = 16.0 if kind == "flyer" else 18.0
	e.hero = hero
	e.fx = fx
	e.position = at + (Vector2(0, -40) if e.kind == "flyer" else Vector2.ZERO)
	add_child(e)


func _bounds(points: Array) -> Rect2:
	var r := Rect2(points[0] - Vector2(PFTerrain.TILE * 0.5, PFTerrain.TILE), Vector2(PFTerrain.TILE, PFTerrain.TILE))
	for p in points:
		r = r.merge(Rect2(p - Vector2(PFTerrain.TILE * 0.5, PFTerrain.TILE), Vector2(PFTerrain.TILE, PFTerrain.TILE)))
	return r


## Maces, lifts, gates, the pool and both bosses, from zone-0 markers.
func _build_set_pieces(m: Dictionary) -> void:
	var T := PFTerrain.TILE
	var i := 0
	for p in m.get("M", []):
		var mace := PFHazards.Mace.new()
		mace.hero = hero
		mace.phase = i * 1.7
		mace.position = p - Vector2(0, T)
		add_child(mace)
		i += 1
	for k in ["v", "h"]:
		for p in m.get(k, []):
			var lift := PFHazards.Lift.new()
			lift.travel = Vector2(0, T * 4) if k == "v" else Vector2(T * 5, 0)
			lift.position = p - Vector2(0, T * 0.25)
			add_child(lift)
	gate = PFHazards.Gate.new()
	gate.rect = _bounds(m["X"])
	add_child(gate)
	lid = PFHazards.Gate.new()
	lid.rect = _bounds(m["Y"])
	lid.vertical = false
	lid.closed = true
	add_child(lid)
	pool = _bounds(m["w"])
	pool.position.y += T * 0.35
	oni = PFOni.new()
	oni.hero = hero
	oni.fx = fx
	oni.position = m["O"][0]
	oni.defeated.connect(_on_oni_defeated)
	add_child(oni)
	maw = PFMaw.new()
	maw.hero = hero
	maw.fx = fx
	maw.pool = pool
	maw.defeated.connect(_on_maw_defeated)
	maw.summon.connect(func(at): _spawn_enemy("f", at + Vector2(0, 40), 0))
	add_child(maw)
	var pool_art := _Pool.new()
	pool_art.rect = pool
	add_child(pool_art)
	# daylight from the mine mouth down the right shaft, and down the left shaft
	var mouth: Rect2 = Rect2(44 * T, 11 * T, 8 * T, T)
	zones[0].terrain.light_beams = [[mouth.get_center(), Vector2(mouth.get_center().x - 2 * T, 45 * T), 5 * T],
		[Vector2(6 * T, 45 * T), Vector2(12 * T, 92 * T), 4 * T]]


func _on_oni_defeated() -> void:
	_oni_done = true
	boss = null
	gate.closed = false
	lid.closed = false
	hud.boss_name = ""
	hud.card("鬼、斃る", "the Oni Captain falls — the seal below breaks")


func _on_maw_defeated() -> void:
	boss = null
	hud.boss_name = ""
	_cleared = true
	hud.card("濡れ口、沈む", "the Drowned Maw sinks for good · ink drops %d / %d — the rift above is still sealed" % [hud.orbs, hud.orbs_total], 7.0)


func _build_portal() -> void:
	var rect := ColorRect.new()
	rect.size = Vector2(230, 300)
	rect.position = portal_pos + Vector2(-115, -260)
	portal_mat = ShaderMaterial.new()
	portal_mat.shader = load("res://shaders/platformer/pf_portal.gdshader")
	portal_mat.set_shader_parameter("wash_noise", load("res://textures/ink/ink_wash_noise.png"))
	rect.material = portal_mat
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(rect)
	if PORTAL_LOCKED:
		portal_mat.set_shader_parameter("open", 0.55)
		var seal := _Seal.new()
		seal.position = portal_pos + Vector2(0, -110)
		add_child(seal)
	move_child(rect, get_children().find(zones[1].terrain) + 1)


func _apply_zone_limits() -> void:
	var z: Dictionary = zones[zone]
	cam.limit_left = int(z.origin.x)
	cam.limit_right = int(z.origin.x + z.size.x)
	cam.limit_top = int(z.origin.y - 400)
	cam.limit_bottom = int(z.origin.y + z.size.y)
	for i in zones.size():
		zones[i].backdrop.visible = i == zone


# ------------------------------------------------------------------ loop

func _process(delta: float) -> void:
	_time += delta
	if hud.selecting:
		_select_input()
		return
	_swap_input()
	if Input.is_action_just_pressed("pf_menu"):
		_to_menu()
	var shake := fx.shake
	cam.offset = Vector2(randf_range(-shake, shake), randf_range(-shake, shake))
	var look_down := clampf(hero.velocity.y * 0.18, 0.0, 160.0)
	var target := hero.global_position + Vector2(hero.facing * 70.0, -70.0 + look_down)
	if boss == maw and is_instance_valid(maw):
		target.y = pool.position.y - 250.0   # frame the whole pit: pool, platforms and you
	cam.global_position = target
	hud.boss_ratio = float(boss.hp) / float(boss.max_hp) if is_instance_valid(boss) else 0.0
	sky_mat.set_shader_parameter("scroll", cam.global_position.x / 1000.0)
	portal_mat.set_shader_parameter("pulse", 0.5 + 0.5 * sin(_time * 4.0))
	if _busy:
		return
	var z: Dictionary = zones[zone]
	# pits and spikes
	if hero.global_position.y > z.origin.y + z.size.y + 60.0:
		hero.hurt(1, Vector2.UP)
		hero._invuln = 0.0
		if hero.hp > 0:
			_respawn()
	elif z.terrain.spike_hit(hero.global_position + Vector2(0, -4)):
		hero.hurt(1, Vector2(-hero.facing, -1))
		if hero.hp > 0:
			hero.velocity.y = -700.0
	for o in orbs:
		if not o.taken and o.zone == zone and hero.global_position.distance_to(o.pos + Vector2(0, 30)) < 40.0:
			o.taken = true
			hud.orbs += 1
			fx.splat(o.pos, hero.hero.glow, 10, 240.0, 3.0)
			fx.ring(o.pos, hero.hero.glow, 30.0, 0.25)
	for c in checkpoints:
		if c.zone == zone and not c.lit and absf(hero.global_position.x - c.pos.x) < 40.0:
			c.lit = true
			checkpoint = c.pos
			hero.heal_full()
			fx.ring(c.pos + Vector2(0, -50), PFHeroes.SHU if zone == 0 else Color(0.3, 0.95, 1.0), 80.0, 0.5)
	if zone == 0 and hero.global_position.distance_to(portal_pos + Vector2(0, -30)) < 90.0:
		if not PORTAL_LOCKED:
			_cross_portal()
		elif not _sealed_told:
			_sealed_told = true
			hud.card("封", "the rift is sealed — something below is holding it shut")
	if zone == 0:
		_boss_triggers()
	if zone == 1 and not _cleared and absf(hero.global_position.x - goal_pos.x) < 60.0:
		_cleared = true
		hud.card("影渡り  完", "stage clear · ink drops %d / %d" % [hud.orbs, hud.orbs_total], 6.0)
		fx.ring(goal_pos + Vector2(0, -80), hero.hero.glow, 160.0, 0.9)


func _boss_triggers() -> void:
	var T := PFTerrain.TILE
	var hp_ := hero.global_position
	# the passage arena: step inside the gate and it shuts behind you
	if not _oni_done and is_instance_valid(oni) and not oni.active and hp_.x < 32 * T and hp_.y > 36 * T and hp_.y < 46 * T:
		oni.active = true
		gate.closed = true
		boss = oni
		hud.boss_name = PFOni.NAME
		hud.card("鬼の頭", "the Oni Captain bars the way down")
	if is_instance_valid(maw) and not maw.active and hp_.y > 82 * T:
		maw.active = true
		boss = maw
		hud.boss_name = PFMaw.NAME
		hud.card("濡れ口", "Nurekuchi, the Drowned Maw — strike the eye when it opens")
	# the ink pool burns
	if pool.size.x > 0.0 and pool.has_point(hp_ + Vector2(0, -6)):
		hero.hurt(1, Vector2.UP)
		hero.velocity.y = -820.0


func _select_input() -> void:
	for i in 3:
		if Input.is_action_just_pressed("pf_hero_%d" % (i + 1)):
			hud.select_index = i
	if Input.is_action_just_pressed("pf_left"):
		hud.select_index = (hud.select_index + 2) % 3
	if Input.is_action_just_pressed("pf_right"):
		hud.select_index = (hud.select_index + 1) % 3
	if Input.is_action_just_pressed("pf_jump") or Input.is_action_just_pressed("pf_confirm"):
		_begin(hud.select_index)
	if Input.is_action_just_pressed("pf_menu"):
		_to_menu()


func _begin(index: int) -> void:
	hud.selecting = false
	hero.set_hero(PFHeroes.ROSTER[index], false)
	hero.input_enabled = true
	hud.card("黒鉄神社", "Kurogane Shrine — something has torn the sky open")


func _swap_input() -> void:
	for i in 3:
		if Input.is_action_just_pressed("pf_hero_%d" % (i + 1)) and hero.hero != PFHeroes.ROSTER[i]:
			hero.set_hero(PFHeroes.ROSTER[i])
	if Input.is_action_just_pressed("pf_swap"):
		var i := (PFHeroes.ROSTER.find(hero.hero) + 1) % 3
		hero.set_hero(PFHeroes.ROSTER[i])


func _reset_bosses() -> void:
	if is_instance_valid(oni) and oni.active:
		oni.reset()
		gate.closed = false
	if is_instance_valid(maw) and maw.active:
		maw.reset()
	boss = null
	hud.boss_name = ""


func _respawn() -> void:
	hero.global_position = checkpoint
	hero.velocity = Vector2.ZERO
	cam.reset_smoothing()


func _on_died() -> void:
	_busy = true
	fx.splat(hero.global_position + Vector2(0, -36), hero.hero.body, 40, 520.0, 6.0)
	await _wipe(1.0)
	hero.heal_full()
	_reset_bosses()
	_respawn()
	await _wipe(0.0)
	_busy = false


func _cross_portal() -> void:
	_busy = true
	hero.input_enabled = false
	hero.velocity = Vector2.ZERO
	fx.ring(portal_pos + Vector2(0, -110), Color(0.3, 0.95, 1.0), 200.0, 0.6)
	await _wipe(1.0)
	zone = 1
	checkpoint = zones[1].markers["S"][0]
	_respawn()
	_apply_zone_limits()
	sky_mat.set_shader_parameter("zone", 1.0)
	post_mat.set_shader_parameter("zone", 1.0)
	hud.zone = 1
	RenderingServer.set_default_clear_color(Color(0.04, 0.02, 0.1))
	await _wipe(0.0)
	hud.card("彼岸  HIGAN", "the far shore — the ink came with you")
	hero.input_enabled = not hud.selecting and not hero.bot.is_valid()
	_busy = false


func _wipe(to: float) -> void:
	var tw := create_tween()
	tw.tween_method(func(v): post_mat.set_shader_parameter("wipe", v), post_mat.get_shader_parameter("wipe"), to, WIPE_TIME)
	await tw.finished


func _to_menu() -> void:
	RenderingServer.set_default_clear_color(Color(0.3, 0.3, 0.3))
	get_tree().change_scene_to_file("res://scenes/menu/main_menu.tscn")


# ------------------------------------------------------------------ inputs

func _bind_inputs() -> void:
	var keys := {
		"pf_left": [KEY_A, KEY_LEFT], "pf_right": [KEY_D, KEY_RIGHT], "pf_up": [KEY_W, KEY_UP],
		"pf_down": [KEY_S, KEY_DOWN], "pf_jump": [KEY_SPACE], "pf_attack": [KEY_J], "pf_special": [KEY_K],
		"pf_dash": [KEY_SHIFT, KEY_L], "pf_swap": [KEY_Q], "pf_menu": [KEY_ESCAPE], "pf_confirm": [KEY_ENTER],
		"pf_hero_1": [KEY_1], "pf_hero_2": [KEY_2], "pf_hero_3": [KEY_3],
	}
	var pads := {"pf_jump": JOY_BUTTON_A, "pf_attack": JOY_BUTTON_X, "pf_special": JOY_BUTTON_Y,
		"pf_dash": JOY_BUTTON_RIGHT_SHOULDER, "pf_swap": JOY_BUTTON_LEFT_SHOULDER, "pf_menu": JOY_BUTTON_START,
		"pf_left": JOY_BUTTON_DPAD_LEFT, "pf_right": JOY_BUTTON_DPAD_RIGHT, "pf_up": JOY_BUTTON_DPAD_UP,
		"pf_down": JOY_BUTTON_DPAD_DOWN}
	for a in keys:
		if InputMap.has_action(a):
			continue
		InputMap.add_action(a, 0.3)
		for k in keys[a]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(a, e)
		if pads.has(a):
			var j := InputEventJoypadButton.new()
			j.button_index = pads[a]
			InputMap.action_add_event(a, j)
	for pair in [["pf_attack", MOUSE_BUTTON_LEFT], ["pf_special", MOUSE_BUTTON_RIGHT]]:
		var m := InputEventMouseButton.new()
		m.button_index = pair[1]
		InputMap.action_add_event(pair[0], m)
	for pair in [["pf_left", JOY_AXIS_LEFT_X, -1.0], ["pf_right", JOY_AXIS_LEFT_X, 1.0],
			["pf_up", JOY_AXIS_LEFT_Y, -1.0], ["pf_down", JOY_AXIS_LEFT_Y, 1.0]]:
		var ax := InputEventJoypadMotion.new()
		ax.axis = pair[1]
		ax.axis_value = pair[2]
		InputMap.action_add_event(pair[0], ax)


# ------------------------------------------------------------------ capture

## Scripted run for screenshots and a smoke test: select screen, each hero in
## action in the shrine, the portal, then the neon side. Writes build/playtest/pf_*.png.
func _capture() -> void:
	var out := ProjectSettings.globalize_path("res://") + "../build/playtest/"
	DirAccess.make_dir_recursive_absolute(out)
	var T := PFTerrain.TILE
	hero.bot = func(): return _bot_held
	await _frames(40)
	await _shot(out + "pf_select.png")
	_begin(0)
	hero.input_enabled = false
	await _secs(0.4)
	await _shot(out + "pf_shrine.png")
	# walk toward the sealed rift (left), then turn and fight the yard goon
	_bot_held = {"pf_left": true}
	await _secs(0.5)
	_bot_held = {}
	await _secs(0.3)
	await _shot(out + "pf_sealed.png")
	_bot_held = {"pf_right": true}
	await _secs(1.4)
	_bot_held = {"pf_attack": true}
	await _secs(0.1)
	_bot_held = {}
	await _secs(0.12)
	await _shot(out + "pf_goon.png")
	# right shaft
	_teleport(Vector2(46 * T, 15 * T))
	hero.set_hero(PFHeroes.ARCHER)
	await _secs(0.6)
	_bot_held = {"pf_attack": true}
	await _secs(0.6)
	await _shot(out + "pf_shaft.png")
	_bot_held = {}
	# oni arena
	_teleport(Vector2(29 * T, 44 * T))
	hero.set_hero(PFHeroes.SWORDSMAN)
	await _secs(1.2)
	_bot_held = {"pf_left": true}
	await _secs(0.5)
	_bot_held = {"pf_left": true, "pf_attack": true}
	await _secs(0.12)
	_bot_held = {}
	await _secs(0.3)
	await _shot(out + "pf_oni.png")
	print("[pf] oni active=", oni.active, " gate=", gate.closed, " hp=", oni.hp)
	# kill the captain to prove the lid opens
	oni.hurt(99, Vector2.LEFT)
	await _secs(0.5)
	print("[pf] after oni: lid closed=", lid.closed)
	# left shaft: maces and lifts
	_teleport(Vector2(12 * T, 50 * T))
	hero.set_hero(PFHeroes.GUNSLINGER)
	await _secs(0.8)
	_bot_held = {"pf_attack": true}
	await _secs(0.3)
	await _shot(out + "pf_left_shaft.png")
	_bot_held = {}
	# the maw
	hero.hp = hero.hero.hp
	_teleport(Vector2(19 * T, 85 * T))
	hero.set_hero(PFHeroes.ARCHER)
	await _secs(2.3)
	await _shot(out + "pf_maw_stalk.png")
	await _secs(0.5)
	await _shot(out + "pf_maw.png")
	print("[pf] maw active=", maw.active, " hero hp=", hero.hp)
	# whole-level overview
	hud.visible = false
	cam.position_smoothing_enabled = false
	cam.limit_top = -10000
	cam.limit_bottom = 10000
	cam.limit_left = -10000
	cam.limit_right = 10000
	cam.zoom = Vector2(0.19, 0.19)
	cam.set_process(false)
	set_process(false)
	cam.global_position = Vector2(30 * T, 48 * T)
	cam.offset = Vector2.ZERO
	await _secs(0.3)
	await _shot(out + "pf_overview.png")
	print("[pf] capture done")
	get_tree().quit()


func _teleport(at: Vector2) -> void:
	hero.global_position = at
	hero.velocity = Vector2.ZERO
	cam.global_position = at
	cam.reset_smoothing()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _secs(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _shot(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
	print("[pf] ", path)


# ------------------------------------------------------------------ world art

## Pickups, checkpoints and the goal, drawn in world space behind the hero.
const _ArtScript := preload("res://scripts/platformer/pf_world_art.gd")


## Paper seals and a rope binding the rift shut.
class _Seal extends Node2D:
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var rope := Color(0.85, 0.8, 0.65)
		for k in [-1.0, 1.0]:
			draw_line(Vector2(-90, -120 * k), Vector2(90, 120 * k), PFHeroes.INK, 9.0)
			draw_line(Vector2(-90, -120 * k), Vector2(90, 120 * k), rope, 5.0)
		for i in 4:
			var p := Vector2(-48 + i * 32, -6 + sin(_t * 2.0 + i) * 3.0)
			draw_rect(Rect2(p, Vector2(18, 44)), PFHeroes.PAPER)
			draw_line(p + Vector2(9, 6), p + Vector2(9, 38), PFHeroes.SHU, 3.0)
			draw_line(p + Vector2(4, 14), p + Vector2(14, 14), PFHeroes.SHU, 2.0)
		draw_circle(Vector2.ZERO, 14.0, PFHeroes.SHU)
		draw_string(InkUI.font(true), Vector2(-11, 8), "封", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, PFHeroes.PAPER)


## The ink pool in the boss pit: a slow black surface with a paper sheen,
## drawn in front of the Maw so it really rises out of it.
class _Pool extends Node2D:
	var rect := Rect2()
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var top := PackedVector2Array()
		var n := int(rect.size.x / 16.0)
		for i in n + 1:
			var x := rect.position.x + rect.size.x * i / n
			top.append(Vector2(x, rect.position.y + sin(x * 0.03 + _t * 2.0) * 3.0 + sin(x * 0.011 - _t) * 2.0))
		var body := top.duplicate()
		body.append(Vector2(rect.end.x, rect.end.y + 30))
		body.append(Vector2(rect.position.x, rect.end.y + 30))
		draw_colored_polygon(body, PFHeroes.INK)
		draw_polyline(top, Color(PFHeroes.PAPER, 0.35), 2.0)
		for i in 6:
			var x := rect.position.x + fmod(i * 173.0 + _t * 30.0, rect.size.x)
			draw_line(Vector2(x, rect.position.y + 10), Vector2(x + 40, rect.position.y + 10), Color(PFHeroes.PAPER, 0.12), 1.5)
