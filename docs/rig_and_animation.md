# Rig, poses and the dagger combo

**Control rig** (`tools/blender/lib/kage_rig.py`, every character): IK/FK per limb (`ik_arm_L/R`, `ik_leg_L/R`), IK hand copies the control's rotation, reverse-foot roll (`roll` on `CTRL_IK_Foot.*`: + heel up over ball then toe, − heel rock), `CTRL_Torso` moves the upper body with feet planted, pole targets, widgets and Rigify-style colours, hidden `Mechanism` collection. The **Kage Rig** sidebar panel (text block `kage_rig_ui.py` in each .blend; enable Auto Run Scripts or run it once) has the sliders and lossless FK↔IK snapping. Non-deforming bones are stripped at export; constraints are baked.

**Pose-first authoring** (`anim_engine.py`, `daggers.py`): poses are fist position in the chest frame + elbow, knuckle and blade directions (solved by IK, snapped to FK), planted IK feet and a head look direction. Clips are poses + timing; the engine bakes every frame with Hermite splines, limb overlap, a footwork track (planted feet pinned in world space) and root motion, and writes `game/data/clip_events.json` (hits, link frame, trail windows, root curve, native loco speeds).
`blender -b --python tools/blender/preview_moves.py -- poses clips check` renders the pose sheet and filmstrips to `docs/renders/poses/` and reports IK reach errors.

**Dagger set:** guard/idle, block, walk F/B/L/R, sprint, 5-hit chain (Kage-giri → Mikazuki → Tsubame → Senpu → Kage-tsuki), heavy (Kage-otoshi), combo branch (heavy after L2+: Tsubame-gaeshi), finisher (Kage-nui).

**In game:** `FighterAnimator` (AnimationTree built in code) blends locomotion by real velocity and cross-fades actions through three slots; attacks buffer input and chain at the authored link frame; root motion follows the baked curve (scaled to the target); per-hand trails; walking out of a recovery; spring bones on cloth chains; head look-at toward the target.
