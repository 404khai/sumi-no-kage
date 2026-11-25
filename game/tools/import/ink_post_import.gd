## glTF post-import: swaps Blender preview materials for the ink library by
## name (M_* -> res://materials/M_*.tres), loops idle/stance clips and reports
## anything unmapped. Registered in each .glb.import (import_script/path).
@tool
extends EditorScenePostImport

const LOOP_PREFIXES := ["Stance_", "Idle", "Loop_"]


func _post_import(scene: Node) -> Object:
	var missing := {}
	_apply(scene, missing)
	for m in missing:
		push_warning("[ink-import] %s: no ink material for '%s'" % [get_source_file(), m])
	return scene


func _apply(node: Node, missing: Dictionary) -> void:
	if node is MeshInstance3D and node.mesh:
		var mesh: Mesh = node.mesh
		for i in mesh.get_surface_count():
			var src := mesh.surface_get_material(i)
			if src == null:
				continue
			var mat_name := src.resource_name
			var path := "res://materials/%s.tres" % mat_name
			if ResourceLoader.exists(path):
				mesh.surface_set_material(i, load(path))
			else:
				missing[mat_name] = true
	if node is AnimationPlayer:
		for lib_name in node.get_animation_library_list():
			var lib: AnimationLibrary = node.get_animation_library(lib_name)
			for anim_name in lib.get_animation_list():
				for prefix in LOOP_PREFIXES:
					if String(anim_name).begins_with(prefix):
						lib.get_animation(anim_name).loop_mode = Animation.LOOP_LINEAR
	for child in node.get_children():
		_apply(child, missing)
