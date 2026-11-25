## Asset showcase + render harness for the asset-production phase.
## Builds the whole scene from code (no editor needed) and, with --shots, renders
## named camera setups to PNG and quits:
##   godot --path game -- --shots=hero,env,vfx_slash --out=../docs/renders
## Without --shots it runs interactively and loops the VFX demo
## (keys: 1-6 switch views, C = next character, W = next weapon,
## Space = Phantom Step, F = spin slash).
extends Node3D

const ROSTER: Array[CharacterDefinition] = [
	preload("res://data/characters/kage.tres"),
	preload("res://data/characters/knight.tres"),
	preload("res://data/characters/viking.tres"),
]
const WEAPONS: Array[WeaponDefinition] = [
	preload("res://data/weapons/kagenui_daggers.tres"),
	preload("res://data/weapons/halberd.tres"),
	preload("res://data/weapons/kuzuri_handblades.tres"),
]
const SHRINE := preload("res://assets/environments/kurogane_shrine/kurogane_shrine_blockout.glb")
const DAGGERS := preload("res://data/weapons/kagenui_daggers.tres")
const SKY_SHADER := preload("res://shaders/ink_sky.gdshader")
const POST_SHADER := preload("res://shaders/ink_post.gdshader")
const BACKDROP_SHADER := preload("res://shaders/ink_backdrop.gdshader")

const HERO_SPOT := Vector3(0.6, 0.0, 19.6)

var kage: Node3D            ## the active character root (name kept for the VFX code paths)
var character: CharacterDefinition
var weapon: WeaponDefinition
var _lineup: Array[Node3D] = []
var skeleton: Skeleton3D
var anim: AnimationPlayer
var mount: WeaponMount
var trails: Array[InkTrail] = []
var step_vfx: PhantomStepVFX
var shrine: Node3D
var backdrop: Node3D
var studio_floor: MeshInstance3D
var camera: Camera3D
var sun: DirectionalLight3D
var env: Environment
var post: ColorRect
var _step_side := 1.0


func _ready() -> void:
	_build_world()
	_build_kage()
	var args := _args()
	if args.has("shots"):
		_run_shots(String(args["shots"]).split(","), args.get("out", "../docs/renders"))
	else:
		set_view("hero")
		_demo_loop()


# ---------------------------------------------------------------- world
func _build_world() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = SKY_SHADER
	sky_mat.set_shader_parameter("wash_noise", load("res://textures/ink/ink_wash_noise.png"))
	sky.sky_material = sky_mat
	sky.process_mode = Sky.PROCESS_MODE_QUALITY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.42
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color(0.92, 0.905, 0.865)
	env.fog_light_energy = 1.0
	env.fog_density = 0.022
	env.fog_sky_affect = 0.0
	env.fog_height = 2.5
	env.fog_height_density = 0.06
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-38, -32, 0)
	sun.light_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 60.0
	sun.shadow_blur = 0.6
	add_child(sun)

	shrine = SHRINE.instantiate()
	add_child(shrine)
	backdrop = _build_backdrop()
	add_child(backdrop)

	studio_floor = MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(40, 40)
	studio_floor.mesh = plane
	studio_floor.material_override = load("res://materials/M_Env_Ground.tres")
	studio_floor.visible = false
	add_child(studio_floor)

	camera = Camera3D.new()
	camera.fov = 38
	camera.far = 600
	add_child(camera)

	var layer := CanvasLayer.new()
	post = ColorRect.new()
	post.set_anchors_preset(Control.PRESET_FULL_RECT)
	post.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var pm := ShaderMaterial.new()
	pm.shader = POST_SHADER
	pm.set_shader_parameter("paper_grain", load("res://textures/ink/paper_grain.png"))
	post.material = pm
	layer.add_child(post)
	add_child(layer)


func _build_backdrop() -> Node3D:
	var root := Node3D.new()
	root.name = "InkMountains"
	var layers := [[150.0, 46.0, 1.0, 0.55, 0.1], [210.0, 70.0, 0.0, 0.34, 0.37], [290.0, 110.0, 3.0, 0.2, 0.71]]
	var tex := load("res://textures/ink/mountain_layers.png")
	for l in layers:
		var mi := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = l[0]
		cyl.bottom_radius = l[0]
		cyl.height = l[1]
		cyl.cap_top = false
		cyl.cap_bottom = false
		cyl.radial_segments = 96
		cyl.rings = 1
		mi.mesh = cyl
		mi.position.y = l[1] * 0.5 - 6.0
		var m := ShaderMaterial.new()
		m.shader = BACKDROP_SHADER
		m.set_shader_parameter("layers", tex)
		m.set_shader_parameter("band", l[2])
		m.set_shader_parameter("ink_amount", l[3])
		m.set_shader_parameter("u_offset", l[4])
		m.set_shader_parameter("repeats", 3.0)
		m.render_priority = -1 - layers.find(l)
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mi)
	return root


# ---------------------------------------------------------------- character
func _build_kage() -> void:
	set_character(ROSTER[0])


## Swap the active character; keeps position/facing and re-equips its weapon.
func set_character(def: CharacterDefinition, with_weapon: WeaponDefinition = null) -> void:
	var xf := kage.global_transform if kage else Transform3D.IDENTITY
	if kage:
		kage.free()
		for t in trails:
			t.queue_free()
		trails.clear()
		if step_vfx:
			step_vfx.queue_free()
	character = def
	kage = def.scene.instantiate()
	kage.name = String(def.id)
	add_child(kage)
	kage.global_transform = xf
	skeleton = kage.find_children("*", "Skeleton3D", true, false)[0]
	anim = kage.find_children("*", "AnimationPlayer", true, false)[0]
	mount = WeaponMount.new()
	mount.skeleton = skeleton
	kage.add_child(mount)
	set_weapon(with_weapon if with_weapon else def.default_weapon)
	_new_step_vfx()
	print("[showcase] character: %s with %s" % [def.display_name, weapon.display_name])


func set_weapon(def: WeaponDefinition) -> void:
	weapon = def
	for t in trails:
		t.queue_free()
	trails.clear()
	mount.equip(def, true)
	anim.play(def.stance_idle)
	for i in mount.hands.size():
		var pts := mount.blade_points(i)
		var tr := InkTrail.new()
		tr.base_node = pts[0]
		tr.tip_node = pts[1]
		tr.lifetime = def.trail_lifetime
		tr.width_scale = 2.4 if def.dual_wield else 1.2
		tr.emitting = false
		add_child(tr)
		trails.append(tr)


func _new_step_vfx() -> void:
	if step_vfx:
		step_vfx.queue_free()
	step_vfx = PhantomStepVFX.new()
	step_vfx.body = kage
	add_child(step_vfx)


func next_character() -> void:
	set_character(ROSTER[(ROSTER.find(character) + 1) % ROSTER.size()])


func next_weapon() -> void:
	set_weapon(WEAPONS[(WEAPONS.find(weapon) + 1) % WEAPONS.size()])
	_new_step_vfx()  # re-collect geometry so the dissolve reaches the new weapon


## All three characters side by side (docs shot), each with its default weapon.
func _spawn_lineup() -> void:
	kage.visible = false
	for i in ROSTER.size():
		var def := ROSTER[i]
		var c: Node3D = def.scene.instantiate()
		add_child(c)
		c.position = Vector3((i - 1) * 1.8, 0, 0)
		c.rotation_degrees.y = (i - 1) * -12.0
		var sk: Skeleton3D = c.find_children("*", "Skeleton3D", true, false)[0]
		var m := WeaponMount.new()
		m.skeleton = sk
		c.add_child(m)
		m.equip(def.default_weapon, true)
		(c.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer).play(def.default_weapon.stance_idle)
		_lineup.append(c)


func _ground_height(x: float, z: float) -> float:
	var q := PhysicsRayQueryParameters3D.create(Vector3(x, 40, z), Vector3(x, -40, z))
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position.y if hit else 0.0


func _place_kage(at: Vector3, yaw_deg: float) -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var y := _ground_height(at.x, at.z) if shrine.visible else 0.0
	kage.global_position = Vector3(at.x, y, at.z)
	kage.rotation_degrees.y = yaw_deg


# ---------------------------------------------------------------- views
func set_view(view: String) -> void:
	var studio := view.begins_with("char") or view in ["hands", "lineup", "halberd", "handblades"]
	for n in _lineup:
		n.queue_free()
	_lineup.clear()
	kage.visible = true
	var wanted := {"char_knight": ROSTER[1], "char_viking": ROSTER[2], "halberd": ROSTER[1]}
	var want: CharacterDefinition = wanted.get(view, ROSTER[0])
	if character != want:
		set_character(want)
	var want_weapon: WeaponDefinition = WEAPONS[2] if view == "handblades" else character.default_weapon
	if weapon != want_weapon:
		set_weapon(want_weapon)
		_new_step_vfx()
	shrine.visible = not studio
	backdrop.visible = not studio
	studio_floor.visible = studio
	env.fog_enabled = not studio
	match view:
		"hero":
			await _place_kage(HERO_SPOT, 8.0)
			_look(kage.global_position + Vector3(2.3, 1.25, 4.1), kage.global_position + Vector3(0.1, 1.05, -0.6), 40)
		"env":
			await _place_kage(Vector3(0.3, 0, 12.0), 180.0)
			_look(Vector3(-9.0, 4.6, 31.0), Vector3(1.5, 3.2, -6.0), 52)
		"env_wide":
			await _place_kage(Vector3(19.0, 0, 6.0), 200.0)
			_look(Vector3(32.0, 9.0, 30.0), Vector3(2.0, 2.0, -4.0), 55)
		"char_front":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(0, 1.0, 4.4), Vector3(0, 0.88, 0), 32)
		"char_34":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(2.6, 1.5, 3.2), Vector3(0, 0.9, 0), 32)
		"char_back":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(-1.6, 1.4, -3.8), Vector3(0, 0.95, 0), 32)
		"char_knight", "char_viking":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(2.4, 1.45, 3.7), Vector3(0, 1.0, 0), 34)
		"lineup":
			await _place_kage(Vector3.ZERO, 0.0)
			_spawn_lineup()
			_look(Vector3(1.0, 1.5, 7.0), Vector3(0, 1.05, 0), 40)
		"halberd":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(-1.6, 1.7, 2.4), Vector3(-0.1, 1.2, -0.3), 38)
		"handblades":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(0.9, 1.45, 1.35), Vector3(0.02, 1.12, 0.12), 36)
		"hands":
			await _place_kage(Vector3.ZERO, 0.0)
			_look(Vector3(0.75, 1.42, 1.05), Vector3(0.02, 1.12, 0.12), 34)
		"vfx_slash", "vfx_step":
			await _place_kage(HERO_SPOT, 8.0)
			_look(kage.global_position + Vector3(3.2, 1.6, 4.8), kage.global_position + Vector3(-0.6, 0.95, -0.3), 42)


func _look(from: Vector3, to: Vector3, fov: float) -> void:
	camera.global_position = from
	camera.look_at(to)
	camera.fov = fov


# ---------------------------------------------------------------- VFX demo
func spin_slash() -> void:
	for t in trails:
		t.clear()
		t.emitting = true
	var tw := create_tween()
	tw.tween_property(kage, "rotation_degrees:y", kage.rotation_degrees.y - 360.0, 0.34) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func():
		for t in trails:
			t.emitting = false)
	InkBurst.spawn(self, kage.global_position + Vector3(0.7, 1.0, 0.4), 18, true, 0.5)


func phantom_step() -> void:
	var dest := kage.global_position + kage.global_transform.basis.x * 3.0 * _step_side
	dest.y = _ground_height(dest.x, dest.z)
	_step_side = -_step_side
	step_vfx.step(dest)


func _demo_loop() -> void:
	while true:
		await get_tree().create_timer(2.0).timeout
		spin_slash()
		await get_tree().create_timer(2.0).timeout
		phantom_step()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		var views := ["hero", "env", "env_wide", "char_front", "char_34", "char_back"]
		var k: int = event.keycode - KEY_1
		if k >= 0 and k < views.size():
			set_view(views[k])
		elif event.keycode == KEY_C:
			next_character()
		elif event.keycode == KEY_W:
			next_weapon()
		elif event.keycode == KEY_SPACE:
			phantom_step()
		elif event.keycode == KEY_F:
			spin_slash()


# ---------------------------------------------------------------- capture
func _run_shots(shots: PackedStringArray, out_dir: String) -> void:
	if not out_dir.is_absolute_path():
		out_dir = ProjectSettings.globalize_path("res://").path_join(out_dir).simplify_path()
	DirAccess.make_dir_recursive_absolute(out_dir)
	for shot in shots:
		await set_view(shot)
		await get_tree().create_timer(0.6).timeout
		match shot:
			"vfx_slash":
				spin_slash()
				await get_tree().create_timer(0.14).timeout
			"vfx_step":
				phantom_step()
				await get_tree().create_timer(0.17).timeout
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var path := out_dir.path_join("godot_%s.png" % shot)
		img.save_png(path)
		print("[capture] %s  fps=%d draw_calls=%d prims=%d" % [path, Engine.get_frames_per_second(),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])
		# reset between shots
		step_vfx.set_dissolve(0.0)
		for t in trails:
			t.clear()
	get_tree().quit()


func _args() -> Dictionary:
	var d := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			d[kv[0]] = kv[1]
	return d
