## One playable character. All characters share the humanoid skeleton, sockets
## and clip names, so any WeaponDefinition works on any character.
class_name CharacterDefinition
extends Resource

@export var id: StringName
@export var display_name: String
@export var scene: PackedScene
@export var default_weapon: WeaponDefinition
## Gameplay feel placeholders for the combat prototype.
@export var move_speed := 5.0
@export var mass_scale := 1.0
