# Asset Register — Phase 1 (asset production)

Status keys: **final-v1**, meaning production quality for this phase, validated end to end, iterable; **blockout**, meaning deliberate placeholder massing for scale and layout, not art; **wip**, meaning functional but not yet at final quality.

| # | Deliverable | Asset / file | Status | Measured |
|---|---|---|---|---|
| 1 | Visual reference & art bible | `docs/art_bible.md`, `docs/renders/palette.png` | final-v1 | five-tone palette, shu accent rule |
| 2 | Assassin design | `docs/kage_character_design.md`, `docs/renders/blender/kage_sheet.png` | final-v1 | — |
| 3 | Assassin 3D model | `assets_src/characters/kage/kage.blend` → `game/assets/characters/kage/kage.glb` | final-v1 | 36,588 tris · 26 meshes · 9 materials · 1.80 m |
| 4 | Complete rig | same file (`Kage_Rig`) | final-v1 | 79 deform + 8 control bones · humanoid profile complete · IK/FK · 4 sockets · 4 cloth chains |
| 4a | Rig-test clips | `RigTest_ROM`, `Stance_DualDaggers_Idle` | **wip** (validation/blocking only, not shipped animation) | 133 f / 61 f loop |
| 5 | Dual daggers | `assets_src/weapons/kagenui_daggers/kagenui_daggers.blend` → `kagenui_dagger.glb`, `kagenui_saya.glb` | final-v1 | 6,000 + 1,588 tris |
| 5a | Weapon data | `game/data/weapons/kagenui_daggers.tres` | final-v1 | reverse grip, sockets, trail sockets |
| 9 | Ashen Knight | `assets_src/characters/knight/knight.blend` → `knight.glb` | final-v1 | 38.8k tris · shared rig + 3 cape chains |
| 10 | Viking Berserker | `assets_src/characters/viking/viking.blend` → `viking.glb` | final-v1 | 28.5k tris · shared rig + 3 cape chains |
| 11 | Halberd | `assets_src/weapons/halberd/halberd.blend` → `halberd.glb` | final-v1 | 3.8k tris · 2.37 m |
| 12 | Kuzuri handblades | `assets_src/weapons/handblade/handblade.blend` → `handblade.glb` | final-v1 | 1.3k tris |
| 14 | Greatsword, broadsword, naginata | `assets_src/weapons/{greatsword,broadsword,naginata}/` → `*.glb` | final-v1 | 2.1k / 1.0k / 3.4k tris |
| 15 | Moveset + gameplay | `tools/blender/lib/moves.py`, `game/data/movesets.json`, `game/scripts/{actors,game,ui,core}/` | wip (playable slice v1) | 3 weapon families |
| 16 | Mugai, the Straw Ronin | `assets_src/characters/ronin/ronin.blend` → `ronin.glb` | final-v1 | 44.9k tris · shared rig + 3 mino chains |
| 17 | Katana + saya | `assets_src/weapons/katana/katana.blend` → `katana.glb`, `katana_saya.glb` | final-v1 | 4.8k + 1.5k tris · 1.03 m |
| 18 | Control rig (IK/FK, foot roll, torso, snapping, panel) | `tools/blender/lib/kage_rig.py`, `kage_rig_ui.py` | final-v1 | all four characters |
| 19 | Dagger pose library + clips | `tools/blender/lib/{anim_engine,daggers}.py` → `game/data/clip_events.json` | wip | 21 poses · 15 baked clips |
| 13 | Roster/weapon data | `game/data/characters/*.tres`, `game/data/weapons/*.tres` | final-v1 | any character × any weapon |
| 6 | Environment concept | `docs/environment_kurogane_shrine.md`, `docs/renders/godot_env*.png` | final-v1 (concept) | — |
| 6a | Environment blockout | `assets_src/environments/kurogane_shrine/…blend` → `kurogane_shrine_blockout.glb` | **blockout** | 14,660 tris · 23 colliders · 6 markers |
| 7 | Ink material & shaders | `game/shaders/*`, `game/data/ink_materials.json`, `game/materials/*` | final-v1 | 9 shaders · 20 materials |
| 7a | Ink textures | `game/textures/ink/*.png` (generated) | final-v1 | 5 textures |
| 7b | Brushstroke VFX | `game/scripts/vfx/{ink_trail,ink_burst,phantom_step}.gd`, `game/materials/vfx/*` | final-v1 (system) | 1 draw call each |
| 8 | Validation & pipeline | `Makefile`, `tools/**`, `game/tools/**`, `build/reports/*` | final-v1 | 0 errors in both validators |

## Explicitly placeholder or incomplete

- **Kurogane Shrine geometry** is blockout. It is tagged in the source (`sumi_status`), flagged by the Godot validator and labelled in every render caption.
- **Playable slice v1:** main menu, player controller, combat, five enemies. Animations are blocking-quality key poses; enemy AI has no pathfinding; no audio.
- **Animation:** only rig validation and blocking stances (dagger guard, halberd guard) exist. There are no locomotion, attack, dodge, parry or finisher clips yet; those belong to the next phase.
- **Spin-slash in the showcase** is a procedural root rotation that drives the trails. It is a VFX demo, not an attack.
- **Cloth chains** are rigged and weighted but not simulated yet (no `SpringBoneSimulator3D` setup).
- **Not yet done:** authored LODs (the importer auto-generates them), a Windows build, Steam export presets, audio.
- **Remaining weapon categories** (longsword, rapier): not modelled yet. The gauntlet reference needs a decision on whether it is a sixth category.
