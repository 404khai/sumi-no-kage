## Builds the shared ink-painting world: environment, moon light, paper sky,
## fog, haboku mountain backdrop and the full-screen paper pass.
class_name InkWorld
extends RefCounted

const SKY_SHADER := preload("res://shaders/ink_sky.gdshader")
const POST_SHADER := preload("res://shaders/ink_post.gdshader")
const BACKDROP_SHADER := preload("res://shaders/ink_backdrop.gdshader")


static func build(parent: Node, fog := true, backdrop := true) -> Dictionary:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = SKY_SHADER
	sky_mat.set_shader_parameter("wash_noise", load("res://textures/ink/ink_wash_noise.png"))
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.42
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.fog_enabled = fog
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color(0.92, 0.905, 0.865)
	env.fog_density = 0.02
	env.fog_sky_affect = 0.0
	env.fog_height = 2.5
	env.fog_height_density = 0.06
	var we := WorldEnvironment.new()
	we.environment = env
	parent.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-38, -32, 0)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 50.0
	parent.add_child(sun)

	if backdrop:
		var tex := load("res://textures/ink/mountain_layers.png")
		var i := 0
		for l in [[150.0, 46.0, 1.0, 0.55, 0.1], [210.0, 70.0, 0.0, 0.34, 0.37], [290.0, 110.0, 3.0, 0.2, 0.71]]:
			var mi := MeshInstance3D.new()
			var cyl := CylinderMesh.new()
			cyl.top_radius = l[0]
			cyl.bottom_radius = l[0]
			cyl.height = l[1]
			cyl.cap_top = false
			cyl.cap_bottom = false
			cyl.radial_segments = 96
			mi.mesh = cyl
			mi.position.y = l[1] * 0.5 - 6.0
			var m := ShaderMaterial.new()
			m.shader = BACKDROP_SHADER
			m.set_shader_parameter("layers", tex)
			m.set_shader_parameter("band", l[2])
			m.set_shader_parameter("ink_amount", l[3])
			m.set_shader_parameter("u_offset", l[4])
			m.set_shader_parameter("repeats", 3.0)
			m.render_priority = -1 - i
			mi.material_override = m
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			parent.add_child(mi)
			i += 1

	var layer := CanvasLayer.new()
	layer.layer = -1
	var post := ColorRect.new()
	post.set_anchors_preset(Control.PRESET_FULL_RECT)
	post.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var pm := ShaderMaterial.new()
	pm.shader = POST_SHADER
	pm.set_shader_parameter("paper_grain", load("res://textures/ink/paper_grain.png"))
	post.material = pm
	layer.add_child(post)
	parent.add_child(layer)
	return {"env": env, "sun": sun}
