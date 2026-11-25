## Data for one weapon category. Combat code reads stances/sockets from here;
## nothing about a weapon is hard-coded in scripts.
class_name WeaponDefinition
extends Resource

enum Category { DUAL_DAGGERS, LONGSWORD, GREATSWORD, RAPIER, NAGINATA }
enum GripMode { FORWARD, REVERSE, TWO_HANDED }

@export var id: StringName
@export var display_name: String
@export var category: Category = Category.DUAL_DAGGERS
@export_group("Meshes")
@export var weapon_scene: PackedScene
@export var sheath_scene: PackedScene
@export var dual_wield := false
@export_group("Grip")
@export var grip_mode: GripMode = GripMode.FORWARD
## Extra offset in socket space, applied after the grip-mode rotation.
@export var grip_offset := Transform3D.IDENTITY
@export_group("Sockets (skeleton bone names)")
@export var main_hand_socket := &"RightHandWeapon"
@export var off_hand_socket := &"LeftHandWeapon"
@export var main_sheath_socket := &"RightSheathBack"
@export var off_sheath_socket := &"LeftSheathBack"
@export var sheath_offset_main := Transform3D.IDENTITY
@export var sheath_offset_off := Transform3D.IDENTITY
@export_group("VFX")
@export var trail_base_node := &"Socket_BladeBase"
@export var trail_tip_node := &"Socket_BladeTip"
@export var trail_lifetime := 0.28
@export_group("Animation")
@export var stance_idle := &"Stance_DualDaggers_Idle"
## Moveset family in res://data/movesets.json (Daggers, Halberd, Greatsword).
@export var move_family := &"Daggers"
@export_group("Feel (placeholders for the combat prototype)")
@export var move_speed_scale := 1.15
@export var phantom_step_distance := 4.0


func grip_transform() -> Transform3D:
	var t := Transform3D.IDENTITY
	if grip_mode == GripMode.REVERSE:
		# blade leaves the pinky side; edge keeps facing the knuckles
		t.basis = Basis(Vector3(0, 0, 1), PI)
	return t * grip_offset
