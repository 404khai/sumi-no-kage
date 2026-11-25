## Generates res://materials/*.tres from res://data/ink_materials.json.
## godot --headless --path game --script res://tools/build_materials.gd
extends SceneTree

const SHADERS := {
	"surface": "res://shaders/ink_surface.gdshader",
	"blade": "res://shaders/ink_blade.gdshader",
}
const OUTLINE_SHADER := "res://shaders/ink_outline.gdshader"
const WASH := "res://textures/ink/ink_wash_noise.png"
const BRUSH := "res://textures/ink/brush_stroke.png"


func _init() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/ink_materials.json"))
	var defaults: Dictionary = data["defaults"]
	var wash: Texture2D = load(WASH)
	var brush: Texture2D = load(BRUSH)
	var outline_shader: Shader = load(OUTLINE_SHADER)
	DirAccess.make_dir_recursive_absolute("res://materials")
	var count := 0
	for mat_name: String in data["materials"]:
		var spec: Dictionary = data["materials"][mat_name]
		var mat := ShaderMaterial.new()
		mat.resource_name = mat_name
		mat.shader = load(SHADERS[spec.get("shader", defaults["shader"])])
		mat.set_shader_parameter("wash_noise", wash)
		if spec.get("shader", "surface") == "surface":
			mat.set_shader_parameter("brush_tex", brush)
		if spec.has("color"):
			var c: Array = spec["color"]
			mat.set_shader_parameter("base_color", Color(c[0], c[1], c[2]))
		var params: Dictionary = defaults["params"].duplicate()
		params.merge(spec.get("params", {}), true)
		for key: String in params:
			var value = params[key]
			if value is Array and value.size() == 2:
				value = Vector2(value[0], value[1])
			mat.set_shader_parameter(key, value)
		var outline: float = spec.get("outline", defaults["outline"])
		if outline > 0.0:
			var o := ShaderMaterial.new()
			o.shader = outline_shader
			o.set_shader_parameter("width", outline)
			o.set_shader_parameter("wash_noise", wash)
			mat.next_pass = o
		var path := "res://materials/%s.tres" % mat_name
		var err := ResourceSaver.save(mat, path)
		if err != OK:
			push_error("failed to save %s (%d)" % [path, err])
			quit(1)
			return
		count += 1
	print("[materials] wrote %d ink materials" % count)
	quit(0)
