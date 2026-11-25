## Headless validation of the imported game assets against tools/asset_manifest.json.
## godot --headless --path game --script res://tools/validate_assets.gd [-- --report=<path>]
## Exit code 1 on any error. Writes a JSON report (default: ../build/reports/validation_godot.json).
extends SceneTree

var errors: Array[String] = []
var warnings: Array[String] = []
var report := {}


func _init() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../tools/asset_manifest.json"))
	if manifest == null:
		manifest = JSON.parse_string(FileAccess.get_file_as_string(ProjectSettings.globalize_path("res://") + "../tools/asset_manifest.json"))
	for asset: Dictionary in manifest["assets"]:
		_validate(asset)
	_check_materials()
	report["errors"] = errors
	report["warnings"] = warnings
	var out := ProjectSettings.globalize_path("res://") + "../build/reports/validation_godot.json"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--report="):
			out = a.trim_prefix("--report=")
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var f := FileAccess.open(out, FileAccess.WRITE)
	f.store_string(JSON.stringify(report, "  "))
	f.close()
	for w in warnings:
		print("[validate] WARN  ", w)
	for e in errors:
		print("[validate] ERROR ", e)
	print("[validate] %d assets, %d errors, %d warnings -> %s" % [report.size() - 2, errors.size(), warnings.size(), out])
	quit(1 if errors.size() > 0 else 0)


func _err(id: String, msg: String) -> void:
	errors.append("%s: %s" % [id, msg])


func _validate(asset: Dictionary) -> void:
	var id: String = asset["id"]
	var res_path: String = "res://" + String(asset["output"]).trim_prefix("game/")
	var info := {"path": res_path}
	report[id] = info
	if not ResourceLoader.exists(res_path):
		_err(id, "not imported: %s" % res_path)
		return
	var packed: PackedScene = load(res_path)
	var root := packed.instantiate()
	var tris := 0
	var mats := {}
	var non_ink := []
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		var mesh := mi.mesh
		for s in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(s)
			var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			tris += idx.size() / 3 if idx.size() > 0 else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() / 3
			var m := mesh.surface_get_material(s)
			if m:
				mats[m.resource_name if m.resource_name != "" else m.resource_path.get_file().get_basename()] = true
				if not (m is ShaderMaterial):
					non_ink.append(m.resource_name)
	info["tris"] = tris
	info["materials"] = mats.keys()
	var budget: Dictionary = asset.get("budget", {})
	if tris > int(budget.get("tris", 1 << 30)):
		_err(id, "triangle budget exceeded: %d > %d" % [tris, budget["tris"]])
	if mats.size() > int(budget.get("materials", 99)):
		_err(id, "material budget exceeded: %d" % mats.size())
	if non_ink.size() > 0:
		_err(id, "surfaces not using ink materials (post-import mapping failed): %s" % [non_ink])
	var expect: Dictionary = asset.get("expect", {})
	for n: String in expect.get("nodes", []):
		if root.find_child(n, true, false) == null:
			_err(id, "missing node %s" % n)
	if asset["kind"] == "character":
		_validate_character(id, root, asset, info)
	if asset["kind"] == "weapon" and expect.has("length"):
		var aabb := _aabb(root)
		var length := maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z))  # longest axis
		info["length"] = length
		if length < expect["length"][0] or length > expect["length"][1]:
			_err(id, "length %.3f outside %s" % [length, expect["length"]])
		if expect.get("origin_inside", true) and not aabb.grow(0.01).has_point(Vector3.ZERO):
			_err(id, "origin is not inside the weapon (grip convention)")
	if asset["kind"] == "environment":
		var shapes := root.find_children("*", "CollisionShape3D", true, false).size()
		info["colliders"] = shapes
		if shapes < int(expect.get("colliders_min", 0)):
			_err(id, "only %d collision shapes" % shapes)
		if asset.get("status") == "blockout":
			warnings.append("%s: BLOCKOUT geometry (placeholder by design, see docs/asset_register.md)" % id)
	root.free()


func _validate_character(id: String, root: Node, asset: Dictionary, info: Dictionary) -> void:
	var skels := root.find_children("*", "Skeleton3D", true, false)
	if skels.size() != 1:
		_err(id, "expected 1 Skeleton3D, found %d" % skels.size())
		return
	var skel: Skeleton3D = skels[0]
	info["bones"] = skel.get_bone_count()
	if skel.get_bone_count() > int(asset["budget"].get("bones", 999)):
		_err(id, "bone budget exceeded")
	# Godot humanoid profile coverage -> retargeting works without a manual BoneMap
	var profile := SkeletonProfileHumanoid.new()
	var missing := []
	for i in profile.bone_size:
		var bn := profile.get_bone_name(i)
		if skel.find_bone(bn) == -1 and not String(bn).ends_with("Eye") and bn != "Jaw":
			missing.append(bn)
	info["humanoid_missing"] = missing
	if missing.size() > 0:
		_err(id, "missing humanoid profile bones: %s" % [missing])
	for s: String in asset["expect"].get("sockets", []):
		if skel.find_bone(s) == -1:
			_err(id, "missing socket bone %s" % s)
	# socket frame: +Y of the hand weapon socket points out of the thumb side (toward model front, +Z)
	var b := skel.find_bone("LeftHandWeapon")
	if b != -1:
		var g := skel.get_bone_global_rest(b)
		info["LeftHandWeapon_basis_y"] = var_to_str(g.basis.y.normalized())
		info["LeftHandWeapon_basis_z"] = var_to_str(g.basis.z.normalized())
		if g.basis.y.normalized().dot(Vector3(0, 0, 1)) < 0.9:
			_err(id, "LeftHandWeapon +Y is not along the thumb side (got %s)" % g.basis.y)
	# height in rest
	var aabb := _aabb(root)
	info["height"] = aabb.end.y
	var h: Array = asset["expect"].get("height", [0, 100])
	if aabb.end.y < h[0] or aabb.end.y > h[1]:
		_err(id, "height %.2f outside %s" % [aabb.end.y, h])
	# skin weights: <= 4 influences, normalised
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		for s in mi.mesh.get_surface_count():
			var arr := mi.mesh.surface_get_arrays(s)
			var w = arr[Mesh.ARRAY_WEIGHTS]
			if w == null or (w as PackedFloat32Array).size() == 0:
				_err(id, "%s surface %d has no skin weights" % [mi.name, s])
				continue
			var weights: PackedFloat32Array = w
			var bad := 0
			for v in range(0, weights.size(), 4):
				var sum := weights[v] + weights[v + 1] + weights[v + 2] + weights[v + 3]
				if absf(sum - 1.0) > 0.01:
					bad += 1
			if bad > 0:
				_err(id, "%s: %d vertices with non-normalised weights" % [mi.name, bad])
	var players := root.find_children("*", "AnimationPlayer", true, false)
	var anims := []
	if players.size() > 0:
		anims = Array((players[0] as AnimationPlayer).get_animation_list())
	info["animations"] = anims
	for a: String in asset["expect"].get("actions", []):
		if not anims.has(a):
			_err(id, "missing animation %s" % a)
		elif a.begins_with("Stance_") and (players[0] as AnimationPlayer).get_animation(a).loop_mode == Animation.LOOP_NONE:
			_err(id, "%s should loop (post-import script not applied?)" % a)


func _aabb(root: Node) -> AABB:
	var out := AABB()
	var first := true
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		var xf := Transform3D.IDENTITY
		var n: Node = mi
		while n != root and n is Node3D:
			xf = (n as Node3D).transform * xf
			n = n.get_parent()
		var a := xf * mi.mesh.get_aabb()
		out = a if first else out.merge(a)
		first = false
	return out


func _check_materials() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/ink_materials.json"))
	for m: String in data["materials"]:
		if not ResourceLoader.exists("res://materials/%s.tres" % m):
			_err("materials", "%s not built (run tools/build_materials.gd)" % m)
