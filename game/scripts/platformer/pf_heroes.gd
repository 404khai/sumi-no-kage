## Platformer roster: the three classes, their palettes and movement/combat numbers.
## Palettes follow docs/reference/platformer: flat colour blocks, ink-black
## undersuit, one saturated rim colour, one glowing "light" colour for weapons.
class_name PFHeroes
extends RefCounted

const INK := Color(0.045, 0.04, 0.05)
const PAPER := Color(0.93, 0.91, 0.86)
const SHU := Color(0.78, 0.16, 0.1)

const SWORDSMAN := {
	"id": "swordsman", "name": "Swordsman", "kanji": "剣",
	"blurb": "3-hit slash combo · down-slash pogo · air dash",
	"body": Color(0.13, 0.22, 0.48), "body_dark": Color(0.07, 0.11, 0.27), "armor": Color(0.36, 0.37, 0.4),
	"head": Color(0.06, 0.06, 0.08), "rim": Color(0.33, 0.62, 1.0), "glow": Color(0.42, 0.98, 0.95),
	"hp": 6, "speed": 330.0, "jump": 640.0, "air_jumps": 0, "dashes": 1, "glide": false,
}
const GUNSLINGER := {
	"id": "gunslinger", "name": "Gunslinger", "kanji": "銃",
	"blurb": "hold to fire twin pistols · aim down to hover on recoil",
	"body": Color(0.95, 0.64, 0.16), "body_dark": Color(0.62, 0.36, 0.08), "armor": Color(0.1, 0.09, 0.1),
	"head": Color(0.87, 0.86, 0.79), "rim": Color(0.34, 0.66, 1.0), "glow": Color(1.0, 0.86, 0.38),
	"hp": 5, "speed": 310.0, "jump": 620.0, "air_jumps": 0, "dashes": 1, "glide": false,
}
const ARCHER := {
	"id": "archer", "name": "Archer", "kanji": "弓",
	"blurb": "hold to draw, release to loose (full draw pierces) · double jump · cloak glide",
	"body": Color(0.47, 0.2, 0.78), "body_dark": Color(0.33, 0.08, 0.42), "armor": Color(0.08, 0.08, 0.14),
	"head": Color(0.05, 0.05, 0.08), "rim": Color(1.0, 0.62, 0.68), "glow": Color(0.3, 0.92, 0.84),
	"hp": 4, "speed": 300.0, "jump": 600.0, "air_jumps": 1, "dashes": 1, "glide": true,
}
const ROSTER := [SWORDSMAN, GUNSLINGER, ARCHER]

# Foes are drawn by the same puppet rig, in ink with a vermilion rim.
const GOON := {
	"id": "goon", "name": "Ashigaru", "body": Color(0.13, 0.12, 0.13), "body_dark": Color(0.08, 0.075, 0.08),
	"armor": Color(0.22, 0.2, 0.2), "head": Color(0.05, 0.05, 0.05), "rim": Color(0.78, 0.16, 0.1),
	"glow": Color(0.95, 0.3, 0.2), "hp": 3, "weapon": "yari",
}
const GOON_ARCHER := {
	"id": "goon", "name": "Ashigaru archer", "body": Color(0.13, 0.12, 0.13), "body_dark": Color(0.08, 0.075, 0.08),
	"armor": Color(0.22, 0.2, 0.2), "head": Color(0.05, 0.05, 0.05), "rim": Color(0.78, 0.16, 0.1),
	"glow": Color(0.95, 0.3, 0.2), "hp": 3, "weapon": "yumi",
}
const ONI := {
	"id": "oni", "name": "Oni Captain", "body": Color(0.16, 0.15, 0.16), "body_dark": Color(0.09, 0.085, 0.09),
	"armor": Color(0.3, 0.28, 0.27), "head": Color(0.62, 0.11, 0.08), "rim": Color(0.85, 0.2, 0.12),
	"glow": Color(1.0, 0.45, 0.25), "hp": 24,
}
