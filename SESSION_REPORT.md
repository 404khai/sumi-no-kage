# Session report: rig, dagger combat, Straw Ronin and katana

Worked in a Graft workspace (`graft new ronin-katana`) so the main checkout stayed free for parallel work; landed with `graft integrate`.

## What was done

### 1. Control rig: IK, FK and animator controls (all four characters)
- `tools/blender/lib/kage_rig.py`: IK/FK blend per limb, the IK hand copies its control's rotation, reverse-foot roll (heel → ball → toe pivots driven by one `roll` property), a `CTRL_Torso` centre-of-gravity control, pole targets, widgets, Rigify-style left/right colours, and a hidden Mechanism collection.
- Fixed a latent bug: leg IK targeted a ground-level bone, so turning it on would have pulled the ankles into the floor. Knee pole angle was inverted.
- Lossless FK↔IK snapping, plus a **Kage Rig** sidebar panel shipped inside each .blend (`kage_rig_ui.py`).
- Verified numerically: IK lands exactly on the ankle, roll pivots correctly, and snapping round-trips.

### 2. Pose-first dagger animation
- `anim_engine.py`: clips are key poses + timing.
  - Every frame is baked with Hermite splines, so motion flows through keys instead of stopping at each one.
  - Limbs lag the hips for overlap.
  - Footwork is a separate track: planted feet are pinned in world space so they cannot skate.
  - Root motion is exported to `game/data/clip_events.json` together with hit, link and trail timings.
- `daggers.py`: a pose library of 21 named fighting poses (guards, wind-ups, contacts, follow-throughs, links). Arms are authored as fist position + elbow/knuckle/blade direction and solved by IK.
- Dagger clips:
  - idle and block
  - walk forward, back, left and right, and a sprint, all phase-matched
  - a 5-hit chain (Kage-giri → Mikazuki → Tsubame → Senpu → Kage-tsuki), where each hit ends in the next one's start pose
  - heavy, a combo branch (heavy after hit 2+) and a finisher
- `preview_moves.py`: pose sheets and filmstrips (`docs/renders/poses/`) plus an IK reach check. It found and fixed lunges where the rear foot was stranded 1.2 m behind.

### 3. Godot runtime
- `FighterAnimator`: an AnimationTree built in code.
  - Locomotion is blended by real velocity, and playback rate follows speed.
  - Actions cross-fade through three slots.
- Fighter:
  - Attack input is buffered and released at the authored link frame.
  - Root motion follows the baked curve, fitted to the target distance.
  - Trails turn on per hand.
  - You can walk out of a recovery.
  - Acceleration, turn lean, lock-on strafing, and a walk key (Ctrl/Alt).
  - Spring bones on cloth chains and a head look-at toward the target.
- Movesets: the dagger family now has 5 lights, a heavy branch and a loco map.
- `--character=<id>` playtest flag.

### 4. New character: Mugai, the Straw Ronin
- Built from `docs/reference/characters/outlaw.jpeg`:
  - wide woven kasa with a ragged fringe hiding the eyes
  - straw mino: shoulder mantle plus long straw on three spring chains
  - black kimono with wide sleeves, hakama, grey obi
  - bandaged forearms and shins, waraji sandals, long hair
- 44.9k tris (budget 45k). Shares the rig and every clip.

### 5. New weapon: katana
- Built from `docs/reference/weapons/katana.jpeg`:
  - curved shinogi-zukuri blade with a hamon band
  - scalloped bronze tsuba
  - diamond ito wrap (two crossing helices over white same)
  - tan fittings
  - white saya with a black kurikata band
- Key 7 in game. Mugai's default.

Pipeline: `make all` is green, and both validators report 0 errors (the only warning is the shrine blockout, which is by design).

## What I loved
- **Feet that stay put.** Pinning planted feet in world space, and exporting the same root curve the game moves by, removed skating by construction rather than by tuning.
- **The checker loop.** Renders show whether a pose reads; the numeric IK-reach report shows what the eye misses, like the 1.2 m stranded rear foot in the L5 lunge.
- **One skeleton for everything.** The Ronin got the new rig, the pose library and every clip for free.
- **Graft.** Moving in-flight work out of the main checkout took one rsync, and `--clone-ignored game/.godot` meant no re-import.

## Pain points
- **Blind posing.** World-space aim vectors are hard to author; fist-in-chest-frame plus blade direction helped a lot, but some poses (Guard_Low, Run_Ready) still need an artist's eye.
- **API drift.** Blender 5.x slotted actions (no `action.fcurves`) and Godot 4.7 deprecations (named blend points, untyped dict iteration breaking `:=`) each cost a cycle.
- **Spring bones.** The defaults flung the long mino over the hat on fast turns. Capes now get their own stiffness, drag and gravity.
- **Playtest bot.** It stands and trades. With longer, committed combos it now **loses** (it won narrowly before). Teaching it to dodge telegraphs made it worse, because it dodges out of its own combos.

## Known gaps and next steps
- **The pose "site" (three.js Pose Lab) was not built yet.** The data it needs already exists: `Pose_Daggers_*` clips in `kage.glb` and `clip_events.json`.
- **Combat balance and the autoplay bot** need a pass; enemy damage versus the new combo pacing has not been tuned.
- The katana borrows the greatsword clips, whose off hand sits above the main hand. It needs its own katana moveset (and a kasa-tilt idle).
- Sprint over-reaches by about 6 cm at full stride. Walk and strafe blending is verified by numbers, but not yet watched in engine at length.
- `tools/blender/__pycache__/*.pyc` files are tracked in git; they should be ignored.
