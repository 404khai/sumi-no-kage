## Attaches a WeaponDefinition's meshes to the character's socket bones.
## Pure presentation: combat state machines call draw()/sheathe().
class_name WeaponMount
extends Node

signal weapons_changed

@export var definition: WeaponDefinition
@export var skeleton: Skeleton3D

var hands: Array[Node3D] = []     # drawn weapon instances [main, off]
var sheaths: Array[Node3D] = []
var _attachments := {}


func equip(def: WeaponDefinition, drawn := true) -> void:
	clear()
	definition = def
	var sockets := [def.main_hand_socket, def.off_hand_socket] if def.dual_wield else [def.main_hand_socket]
	var sheath_sockets := [def.main_sheath_socket, def.off_sheath_socket] if def.dual_wield else [def.main_sheath_socket]
	var sheath_offsets := [def.sheath_offset_main, def.sheath_offset_off]
	for i in sockets.size():
		var w := def.weapon_scene.instantiate() as Node3D
		w.name = "%s_%d" % [def.id, i]
		_attach(sockets[i]).add_child(w)
		w.transform = def.grip_transform()
		hands.append(w)
		if def.sheath_scene:
			var s := def.sheath_scene.instantiate() as Node3D
			s.name = "%s_sheath_%d" % [def.id, i]
			_attach(sheath_sockets[i]).add_child(s)
			s.transform = sheath_offsets[i]
			sheaths.append(s)
	set_drawn(drawn)
	weapons_changed.emit()


func set_drawn(drawn: bool) -> void:
	# a sheathed weapon rides inside its saya: same frame as the sheath
	for i in hands.size():
		var target: Node3D = _attachments[definition.main_hand_socket if i == 0 else definition.off_hand_socket]
		if not drawn and i < sheaths.size():
			target = sheaths[i]
		if hands[i].get_parent() != target:
			hands[i].reparent(target, false)
		hands[i].transform = definition.grip_transform() if drawn else Transform3D.IDENTITY


func clear() -> void:
	for n in _attachments.values():
		n.queue_free()
	_attachments.clear()
	hands.clear()
	sheaths.clear()


func blade_points(index: int) -> Array[Node3D]:
	var w := hands[index]
	return [w.find_child(String(definition.trail_base_node), true, false) as Node3D,
		w.find_child(String(definition.trail_tip_node), true, false) as Node3D]


func _attach(bone: StringName) -> Node3D:
	if _attachments.has(bone):
		return _attachments[bone]
	assert(skeleton.find_bone(bone) != -1, "socket bone %s missing" % bone)
	var a := BoneAttachment3D.new()
	a.name = "Socket_%s" % bone
	a.bone_name = bone
	skeleton.add_child(a)
	_attachments[bone] = a
	return a
