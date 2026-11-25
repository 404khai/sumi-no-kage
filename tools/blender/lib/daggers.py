"""Kage's dual-dagger style: pose library, locomotion and the five-hit combo.

Authoring vocabulary (see `stance()`):
  * torso: hips drop/turn/lean, spine twist/lean/bend spread over three bones,
    head looks along a world direction (eyes stay on the target while the body
    winds up and unwinds).
  * arms: fist position in the *chest frame* (x = character-left, -y = forward,
    z = up; it turns with the chest), elbow direction, knuckle direction and
    blade direction. Solved with the rig's arm IK, snapped to FK, forearm takes
    half of the wrist twist. Daggers are held in reverse grip (blade out of the
    pinky side, edge facing the knuckles), so a cut travels knuckles-first.
  * feet: planted IK feet (ground point under the ankle, yaw, foot roll).

Clips are pose-to-pose with timing, footwork and root motion (anim_engine).
Every attack starts on the previous attack's link pose, so the combo chains
without a pop: L1 -> L2 -> L3 -> L4 -> L5, heavy branches off L2..L4.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Quaternion, Vector

import anim_engine as E
from anim_engine import Clip, Foot, Step

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _n(v):
    return Vector(v).normalized()


# ---------------------------------------------------------------- footwork
# Left-lead fighting stance (ground point under each ankle, root-local).
GUARD_FEET = {"L": Foot(0.13, -0.27, -6, 0), "R": Foot(-0.15, 0.27, -38, 14)}
RIGHT_LEAD = {"L": Foot(0.16, 0.25, 34, 14), "R": Foot(-0.12, -0.29, 8, 0)}
SQUARE = {"L": Foot(0.15, -0.02, 6, 0), "R": Foot(-0.15, 0.02, -6, 0)}


def feet(base, **over):
    out = {s: Foot(f.x, f.y, f.yaw, f.roll, f.z) for s, f in base.items()}
    for side, vals in over.items():
        f = out[side]
        for k, v in vals.items():
            setattr(f, k, v)
    return out


# ------------------------------------------------------------- pose spec
def stance(drop=0.13, turn=-28.0, pelvis=4.0, hips_x=0.0, hips_y=0.01, side=0.0,
           twist=10.0, lean=12.0, bend=0.0, look=(0, -1, 0.02), L=None, R=None, feet=GUARD_FEET,
           neck=0.45):
    """One pose. L/R: dict(fist, elbow, knuckles, blade) in the chest frame."""
    body = {
        "Hips": {"loc": (hips_x, hips_y, -drop), "rot": [(Z, turn), (X, -pelvis), (Y, side)]},
        "Spine": [(X, lean * 0.40), (Z, twist * 0.35), (Y, bend * 0.40)],
        "Chest": [(X, lean * 0.35), (Z, twist * 0.35), (Y, bend * 0.35)],
        "UpperChest": [(X, lean * 0.25), (Z, twist * 0.30), (Y, bend * 0.25)],
        "Neck": [(X, -lean * 0.35), (Z, -(turn + twist) * neck)],
    }
    return {"body": body, "arms": {"L": L, "R": R}, "look": look, "feet": feet}


def A(fist, elbow, knuckles, blade):
    return {"fist": fist, "elbow": elbow, "knuckles": knuckles, "blade": blade}


# ------------------------------------------------------------- resolving
def _chest_frame(arm):
    pb = arm.pose.bones["UpperChest"]
    rot = pb.matrix.to_3x3() @ pb.bone.matrix_local.to_3x3().inverted()
    return pb.head.copy(), rot


def _orient(arm, name, y_dir, z_dir):
    """Rotate pose bone `name` so its armature-space axes are +Y=y_dir, +Z~z_dir."""
    from mathutils import Matrix
    bpy.context.view_layer.update()
    pb = arm.pose.bones[name]
    y = _n(y_dir)
    x = y.cross(Vector(z_dir)).normalized()
    z = x.cross(y)
    r = Matrix((x, y, z)).transposed()
    m0 = pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
    pb.rotation_quaternion = (m0.to_3x3().inverted() @ r).to_quaternion()


def _twist_y(q):
    """Twist angle of quaternion q about local +Y (swing-twist decomposition)."""
    return 2.0 * math.atan2(q.y, q.w)


class Resolver:
    def __init__(self, K, arm):
        self.K, self.arm = K, arm
        import kage_rig
        self.rig = kage_rig

    def __call__(self, name, spec, meta=None):
        K, arm, rig = self.K, self.arm, self.rig
        body = dict(spec["body"])
        body.update(K.fist("L"))
        body.update(K.fist("R"))
        K.pose(arm, body)
        bpy.context.view_layer.update()
        origin, crot = _chest_frame(arm)
        for side, a in spec["arms"].items():
            if not a:
                continue
            S = "Left" if side == "L" else "Right"
            fist = origin + crot @ Vector(a["fist"])
            kn = _n(crot @ Vector(a["knuckles"]))
            blade = _n(crot @ Vector(a["blade"]))
            wrist = fist - kn * 0.062
            arm[f"ik_arm_{side}"] = 1.0
            rig.set_point(arm, f"CTRL_IK_Hand.{side}", wrist)
            sh = arm.pose.bones[f"{S}UpperArm"].head
            mid = (sh + wrist) * 0.5
            rig.set_point(arm, f"CTRL_Pole_Arm.{side}", mid + _n(crot @ Vector(a["elbow"])) * 0.45)
            bpy.context.view_layer.update()
            rig.snap_fk_to_ik(arm, "arm", side)
            arm[f"ik_arm_{side}"] = 0.0
            # reverse grip: socket +Y (thumb side) points away from the blade
            K.orient_socket(arm, f"{S}Hand", f"{S}HandWeapon", -blade, kn)
            hand = arm.pose.bones[f"{S}Hand"]
            tw = _twist_y(hand.rotation_quaternion)
            fore = arm.pose.bones[f"{S}LowerArm"]
            fore.rotation_quaternion = fore.rotation_quaternion @ Quaternion((0, 1, 0), tw * 0.5)
            K.orient_socket(arm, f"{S}Hand", f"{S}HandWeapon", -blade, kn)
        look = _n(spec["look"])
        up = _n(Vector((0, 0, 1)) - look * 0.15)
        _orient(arm, "Head", up, look)
        bpy.context.view_layer.update()
        rot = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones
               if not pb.name.startswith(("CTRL_", "MCH_"))}
        hips = arm.pose.bones["Hips"].location.copy()
        return E.Pose(name, rot, hips, spec["feet"], meta or {})


# ============================================================ POSE LIBRARY
# Chest-frame cheat sheet: shoulders sit at (+-0.17, 0.01, 0.11); a straight arm
# reaches ~0.6 m from the shoulder. -y is forward, z up.
def library():
    P = {}

    def add(name, phase, desc, spec):
        P[name] = (spec, {"phase": phase, "desc": desc})

    # --- guards ---------------------------------------------------------
    add("Guard", "guard", "Kage no kamae. Low bladed stance, lead dagger forward along the forearm, "
        "rear dagger cocked at the sternum.",
        stance(L=A((0.13, -0.42, 0.11), (0.55, 0.15, -0.8), (-0.05, -0.35, 0.94), (0.20, 0.50, -0.84)),
               R=A((-0.06, -0.26, -0.03), (-0.70, 0.35, -0.6), (0.25, -0.55, 0.80), (0.55, -0.75, -0.25))))
    add("Guard_Breathe", "guard", "Exhale of the guard loop: shoulders settle, hands sink a finger's width.",
        stance(drop=0.145, lean=13.5,
               L=A((0.13, -0.42, 0.09), (0.55, 0.15, -0.8), (-0.05, -0.35, 0.94), (0.20, 0.50, -0.84)),
               R=A((-0.06, -0.26, -0.05), (-0.70, 0.35, -0.6), (0.25, -0.55, 0.80), (0.55, -0.75, -0.25))))
    add("Guard_Low", "guard", "Kasumi. Predator crouch: both blades low and wide, weight forward.",
        stance(drop=0.30, turn=-18, lean=26, twist=4, pelvis=10,
               L=A((0.30, -0.30, -0.30), (0.8, 0.4, 0.2), (0.3, -0.7, 0.4), (0.0, 0.75, 0.6)),
               R=A((-0.30, -0.22, -0.34), (-0.8, 0.4, 0.2), (-0.3, -0.7, 0.4), (0.0, 0.75, 0.6)),
               feet=feet(GUARD_FEET, L={"y": -0.36, "x": 0.18}, R={"y": 0.34, "x": -0.19, "roll": 24})))
    add("Guard_Cross", "guard", "Juji-uke. Forearms crossed before the face, blades flared out: the block.",
        stance(drop=0.17, turn=-16, lean=16, twist=6,
               L=A((-0.04, -0.30, 0.20), (0.75, 0.1, -0.65), (-0.35, -0.2, 0.9), (0.75, -0.1, -0.65)),
               R=A((0.04, -0.33, 0.15), (-0.75, 0.1, -0.65), (0.35, -0.2, 0.9), (-0.75, -0.1, -0.65))))
    add("Run_Ready", "locomotion", "Sprint carriage: chest over the lead knee, blades trailing behind the forearms.",
        stance(drop=0.07, turn=-6, lean=30, twist=0, pelvis=-2,
               L=A((0.22, 0.14, -0.34), (0.3, 0.5, -0.8), (0.1, -0.5, -0.85), (0.1, 0.85, 0.5)),
               R=A((-0.22, 0.16, -0.34), (-0.3, 0.5, -0.8), (-0.1, -0.5, -0.85), (-0.1, 0.85, 0.5)),
               feet=SQUARE))

    # --- L1  Kage-giri: rear-hand horizontal cut, right to left ---------
    add("L1_Wind", "anticipation", "Coil right: hips close, rear fist pulled back beside the shoulder.",
        stance(drop=0.15, turn=-44, twist=-16, lean=10,
               L=A((0.14, -0.36, 0.06), (0.6, 0.1, -0.8), (-0.05, -0.4, 0.9), (0.2, 0.5, -0.84)),
               R=A((-0.34, -0.05, 0.10), (-0.4, 0.6, -0.2), (0.4, -0.8, 0.3), (0.05, -0.6, -0.8))))
    add("L1_Cut", "contact", "Hips snap through, the rear blade crosses the centre line at throat height.",
        stance(drop=0.17, turn=-6, twist=26, lean=14, hips_y=-0.03,
               L=A((0.22, -0.18, 0.02), (0.7, 0.3, -0.5), (0.1, -0.4, 0.9), (0.3, 0.6, -0.74)),
               R=A((0.02, -0.52, 0.12), (-0.55, 0.45, 0.3), (1.0, -0.15, 0.0), (0.15, -0.9, -0.4))))
    add("L1_Follow", "follow", "Blade runs on past the body; rear shoulder rolls over the lead knee.",
        stance(drop=0.17, turn=8, twist=40, lean=14, hips_y=-0.03,
               L=A((0.26, -0.08, 0.10), (0.7, 0.4, -0.4), (0.0, -0.3, 0.95), (0.3, 0.7, -0.6)),
               R=A((0.32, -0.30, 0.06), (-0.4, 0.2, 0.85), (0.5, 0.8, 0.0), (0.6, -0.6, -0.4))))
    add("L1_Link", "link", "Loaded for the backhand: chest wound left, lead blade raised behind the ear.",
        stance(drop=0.15, turn=-2, twist=34, lean=12,
               L=A((0.30, 0.00, 0.26), (0.5, 0.5, -0.6), (-0.4, -0.3, 0.85), (0.2, 0.9, 0.3)),
               R=A((0.18, -0.28, 0.02), (-0.5, 0.1, -0.85), (0.6, 0.4, 0.6), (0.4, -0.8, -0.4))))

    # --- L2  Mikazuki: lead-hand falling backhand, high-left to low-right
    add("L2_Wind", "anticipation", "Rise onto the balls of the feet, lead blade high over the left shoulder.",
        stance(drop=0.10, turn=2, twist=40, lean=6,
               L=A((0.34, 0.04, 0.34), (0.4, 0.6, -0.5), (-0.3, -0.2, 0.93), (0.25, 0.85, 0.45)),
               R=A((0.16, -0.26, 0.00), (-0.5, 0.1, -0.85), (0.6, 0.4, 0.6), (0.4, -0.8, -0.4)),
               feet=feet(GUARD_FEET, R={"roll": 26})))
    add("L2_Cut", "contact", "The crescent falls: lead blade cuts down across the chest line.",
        stance(drop=0.21, turn=-40, twist=-24, lean=20, hips_y=-0.05,
               L=A((-0.04, -0.52, -0.06), (0.75, 0.2, 0.6), (-0.6, -0.3, -0.75), (0.1, -0.85, 0.5)),
               R=A((-0.24, -0.08, 0.02), (-0.6, 0.6, -0.5), (0.3, -0.6, 0.75), (0.5, -0.7, -0.5))))
    add("L2_Follow", "follow", "Blade finishes low by the rear hip, torso folded over the lead leg.",
        stance(drop=0.23, turn=-52, twist=-34, lean=24, hips_y=-0.05,
               L=A((-0.26, -0.32, -0.30), (0.6, 0.3, 0.75), (-0.5, 0.5, -0.7), (-0.2, -0.75, 0.6)),
               R=A((-0.26, -0.02, 0.04), (-0.6, 0.6, -0.5), (0.3, -0.6, 0.75), (0.5, -0.7, -0.5))))
    add("L2_Link", "link", "Coiled right and low; rear fist cocked under the ribs for the rising cut.",
        stance(drop=0.21, turn=-48, twist=-26, lean=20,
               L=A((-0.12, -0.36, -0.14), (0.7, 0.2, 0.6), (-0.3, -0.5, 0.8), (0.3, 0.7, -0.6)),
               R=A((-0.30, 0.02, -0.18), (-0.6, 0.7, -0.3), (0.3, -0.5, 0.8), (0.1, 0.7, -0.7))))

    # --- L3  Tsubame: rear-hand rising diagonal with a step-through ----
    add("L3_Cut", "contact", "Step through to right lead; the rear blade rises from hip to opposite shoulder.",
        stance(drop=0.18, turn=24, twist=18, lean=12, hips_y=-0.04,
               L=A((0.20, -0.14, -0.02), (0.7, 0.4, -0.5), (0.0, -0.4, 0.9), (0.3, 0.6, -0.74)),
               R=A((0.10, -0.50, 0.24), (-0.6, 0.3, -0.7), (0.6, -0.2, 0.75), (0.1, -0.7, -0.7)),
               feet=RIGHT_LEAD))
    add("L3_Follow", "follow", "Rising cut spends itself high left; weight settles on the new lead leg.",
        stance(drop=0.16, turn=34, twist=30, lean=8, hips_y=-0.04,
               L=A((0.20, -0.10, -0.04), (0.7, 0.4, -0.5), (0.0, -0.4, 0.9), (0.3, 0.6, -0.74)),
               R=A((0.28, -0.30, 0.38), (-0.6, 0.3, 0.6), (0.5, 0.4, 0.75), (0.4, -0.85, 0.1)),
               feet=RIGHT_LEAD))
    add("L3_Link", "link", "Right lead, both blades gathered at the chest, hips loaded for the spin.",
        stance(drop=0.16, turn=30, twist=-6, lean=12,
               L=A((0.06, -0.26, 0.02), (0.7, 0.3, -0.6), (-0.2, -0.4, 0.9), (0.5, 0.6, -0.6)),
               R=A((-0.06, -0.30, 0.06), (-0.7, 0.3, -0.6), (0.2, -0.4, 0.9), (-0.5, 0.6, -0.6)),
               feet=RIGHT_LEAD))

    # --- L4  Senpu: airborne whirlwind, two cuts in one turn ------------
    add("L4_Spin", "contact", "Mid-turn: arms flung wide, both blades out like a pinwheel.",
        stance(drop=0.06, turn=150, twist=0, lean=4, pelvis=0,
               L=A((0.58, -0.12, 0.06), (0.0, 0.3, -0.95), (0.3, -0.95, 0.0), (0.2, 0.1, -0.97)),
               R=A((-0.58, -0.12, 0.06), (0.0, 0.3, -0.95), (-0.3, -0.95, 0.0), (-0.2, 0.1, -0.97)),
               feet=SQUARE))
    add("L4_Land", "follow", "Land low out of the turn, lead blade still sweeping, rear arm thrown back.",
        stance(drop=0.24, turn=-40, twist=-20, lean=18,
               L=A((0.02, -0.50, 0.04), (0.6, 0.3, -0.75), (-0.9, -0.3, 0.2), (0.1, -0.9, -0.4)),
               R=A((-0.44, 0.10, 0.04), (-0.3, 0.7, -0.6), (-0.6, 0.7, 0.3), (0.0, 0.5, -0.85))))
    add("L4_Link", "link", "Gathered low in left lead, both fists chambered at the hips for the thrust.",
        stance(drop=0.22, turn=-22, twist=4, lean=16,
               L=A((0.16, -0.08, -0.26), (0.5, 0.7, -0.4), (0.0, -0.4, 0.9), (0.0, -0.9, -0.4)),
               R=A((-0.16, -0.02, -0.26), (-0.5, 0.7, -0.4), (0.0, -0.4, 0.9), (0.0, -0.9, -0.4))))

    # --- L5  Kage-tsuki: lunging double thrust ---------------------------
    add("L5_Thrust", "contact", "Full lunge: both hammer-fists driven through, blades level with the target's heart.",
        stance(drop=0.30, turn=-14, twist=8, lean=26, hips_y=-0.10, pelvis=8,
               L=A((0.08, -0.62, -0.04), (0.6, 0.2, -0.75), (0.0, -0.2, 0.98), (0.05, -0.97, -0.2)),
               R=A((-0.06, -0.60, -0.08), (-0.6, 0.2, -0.75), (0.0, -0.2, 0.98), (-0.05, -0.97, -0.2)),
               feet=feet(GUARD_FEET, L={"y": -0.40}, R={"y": 0.40, "roll": 30})))

    # --- heavy, branch and finisher -------------------------------------
    add("Heavy_Leap", "anticipation", "Kage-otoshi: off the ground, both blades raised high behind the head.",
        stance(drop=-0.10, turn=-12, twist=0, lean=-6, pelvis=-4,
               L=A((0.20, 0.06, 0.48), (0.6, 0.0, 0.0), (0.0, 0.6, 0.8), (0.1, 0.8, -0.6)),
               R=A((-0.20, 0.06, 0.48), (-0.6, 0.0, 0.0), (0.0, 0.6, 0.8), (-0.1, 0.8, -0.6)),
               feet=feet(SQUARE, L={"z": 0.22, "y": -0.10, "roll": 20}, R={"z": 0.18, "y": 0.10, "roll": 26})))
    add("Heavy_Drop", "contact", "Both blades drop in a closing X; land in a crouch on the cut.",
        stance(drop=0.40, turn=-12, twist=0, lean=34, pelvis=12,
               L=A((-0.02, -0.52, -0.34), (0.7, 0.2, -0.65), (-0.4, -0.2, -0.9), (0.2, -0.9, -0.4)),
               R=A((0.02, -0.50, -0.36), (-0.7, 0.2, -0.65), (0.4, -0.2, -0.9), (-0.2, -0.9, -0.4)),
               feet=feet(GUARD_FEET, L={"y": -0.36, "x": 0.20}, R={"y": 0.34, "x": -0.20, "roll": 30})))
    add("Rising_Cross", "contact", "Tsubame-gaeshi: rising scissor cut that lifts the foe off balance.",
        stance(drop=0.08, turn=-10, twist=0, lean=-4, pelvis=-6,
               L=A((0.30, -0.36, 0.44), (0.7, 0.3, -0.6), (0.4, 0.0, 0.9), (0.4, -0.85, 0.3)),
               R=A((-0.30, -0.36, 0.44), (-0.7, 0.3, -0.6), (-0.4, 0.0, 0.9), (-0.4, -0.85, 0.3)),
               feet=feet(GUARD_FEET, R={"roll": 40}, L={"roll": 16})))
    add("Finisher_Plunge", "contact", "Kage-nui: both blades driven down into the collarbones of a reeling foe.",
        stance(drop=0.20, turn=-10, twist=0, lean=30, pelvis=6, hips_y=-0.06,
               L=A((0.08, -0.50, 0.16), (0.7, 0.3, 0.2), (0.0, -0.5, 0.85), (0.0, -0.3, -0.95)),
               R=A((-0.08, -0.50, 0.16), (-0.7, 0.3, 0.2), (0.0, -0.5, 0.85), (0.0, -0.3, -0.95)),
               feet=feet(GUARD_FEET, L={"y": -0.34}, R={"y": 0.36, "roll": 34})))
    return P


# ================================================================== CLIPS
def shuffle(lead_side, a0, a1, b0, b1, lead_to, rear_to, lift=0.06):
    """Lunge footwork: lead foot steps out, rear foot drags in behind it."""
    rear = "R" if lead_side == "L" else "L"
    return [Step(lead_side, a0, a1, lead_to, lift=lift), Step(rear, b0, b1, rear_to, drag=True)]


def clips(R, poses):
    """All dagger clips. R = Resolver, poses = {name: E.Pose}."""
    p = poses
    G = p["Guard"]
    out = []

    def C(name, keys, **kw):
        out.append(Clip(name, keys, **kw))

    # ---------------------------------------------------- idle / block
    breathe = p["Guard_Breathe"]
    C("Stance_DualDaggers_Idle", [(1, G, 0.6), (31, breathe, 0.6), (61, G, 0.6)], loop=True,
      root=[(1, 0.0), (61, 0.0)])
    C("Stance_Block_Daggers", [(1, p["Guard_Cross"], 1.0), (21, p["Guard_Cross"], 1.0)], loop=True,
      root=[(1, 0.0), (21, 0.0)])

    # ------------------------------------------------------------ attacks
    gf = GUARD_FEET
    # L1 (hit f7, link f13, recover to guard by f24)
    C("Atk_Daggers_L1",
      [(1, G, 0.0), (4, p["L1_Wind"], 0.2), (7, p["L1_Cut"], 0.0), (10, p["L1_Follow"], 0.3),
       (14, p["L1_Link"], 0.6), (24, G, 1.0)],
      root=[(1, 0.0), (3, 0.02), (8, 0.55), (12, 0.62)],
      steps=shuffle("L", 3, 8, 5, 12, gf["L"], gf["R"]),
      hits=[7], link=13, trails={"R": (4, 11)}, drag=1.0)
    # L2 (hit f8, link f15)
    C("Atk_Daggers_L2",
      [(1, p["L1_Link"], 0.0), (4, p["L2_Wind"], 0.2), (8, p["L2_Cut"], 0.0), (11, p["L2_Follow"], 0.3),
       (16, p["L2_Link"], 0.6), (27, G, 1.0)],
      root=[(1, 0.0), (4, 0.02), (9, 0.62), (13, 0.70)],
      steps=shuffle("L", 4, 9, 6, 13, gf["L"], gf["R"]),
      hits=[8], link=15, trails={"L": (5, 12)}, drag=1.1)
    # L3: step through into right lead (hit f8, link f15); recovery steps back to left lead
    C("Atk_Daggers_L3",
      [(1, p["L2_Link"], 0.0), (5, p["L2_Link"], 0.4), (8, p["L3_Cut"], 0.0), (11, p["L3_Follow"], 0.3),
       (16, p["L3_Link"], 0.6), (30, G, 1.0)],
      root=[(1, 0.0), (3, 0.03), (9, 0.80), (13, 0.86)],
      steps=[Step("R", 3, 9, RIGHT_LEAD["R"], lift=0.08), Step("L", 9, 14, RIGHT_LEAD["L"], drag=True),
             Step("R", 20, 27, gf["R"], lift=0.05), Step("L", 18, 24, gf["L"], drag=True)],
      hits=[8], link=15, trails={"R": (5, 12)}, drag=1.0)
    # L4: hop-spin, two hits (feet scripted: rotate around the root while airborne)
    spin = [(1, p["L3_Link"], 0.0)]
    s_turn = (30, 150, 270, 332)  # hips yaw through the turn (deg)
    for f, yaw in zip((5, 8, 11, 14), s_turn):
        spin.append((f, R(f"_spin{f}", stance(drop=0.08, turn=yaw, twist=0, lean=4, pelvis=0,
                                               L=A((0.58, -0.12, 0.06), (0.0, 0.3, -0.95), (0.3, -0.95, 0.0),
                                                   (0.2, 0.1, -0.97)),
                                               R=A((-0.58, -0.12, 0.06), (0.0, 0.3, -0.95), (-0.3, -0.95, 0.0),
                                                   (-0.2, 0.1, -0.97)),
                                               feet=SQUARE, look=(0, -1, 0.05))), 0.0))
    spin += [(17, p["L4_Land"], 0.2), (22, p["L4_Link"], 0.6), (34, G, 1.0)]
    C("Atk_Daggers_L4", spin, root=[(1, 0.0), (4, 0.02), (14, 0.55), (18, 0.62)],
      feet_fn=_spin_feet(spin_start=3, air=(5, 15), land=17, settle=22),
      hits=[8, 13], link=21, trails={"L": (5, 16), "R": (5, 16)}, drag=0.8)
    # L5: big lunge thrust, long recovery (hit f9, link f20)
    C("Atk_Daggers_L5",
      [(1, p["L4_Link"], 0.0), (5, p["Guard_Low"], 0.3), (9, p["L5_Thrust"], 0.0), (14, p["L5_Thrust"], 0.8),
       (22, p["Guard_Low"], 0.4), (34, G, 1.0)],
      root=[(1, 0.0), (4, 0.05), (10, 1.65), (14, 1.80)],
      steps=[Step("L", 4, 10, p["L5_Thrust"].feet["L"], lift=0.10), Step("R", 4, 11, p["L5_Thrust"].feet["R"], lift=0.07)]
      + [Step("L", 22, 28, gf["L"], lift=0.04), Step("R", 24, 30, gf["R"], drag=True)],
      hits=[9], link=20, trails={"L": (6, 12), "R": (6, 12)}, drag=1.0)

    # Heavy from neutral: leap and double drop-cut (hit f14)
    C("Atk_Daggers_Heavy",
      [(1, G, 0.0), (6, p["Guard_Low"], 0.6), (11, p["Heavy_Leap"], 0.2), (14, p["Heavy_Drop"], 0.0),
       (22, p["Heavy_Drop"], 0.8), (36, G, 1.0)],
      root=[(1, 0.0), (6, 0.0), (14, 1.0), (16, 1.05)],
      steps=[Step("L", 7, 14, p["Heavy_Drop"].feet["L"], lift=0.30), Step("R", 8, 14, p["Heavy_Drop"].feet["R"], lift=0.26),
             Step("L", 24, 30, gf["L"], drag=True), Step("R", 26, 32, gf["R"], drag=True)],
      hits=[14], link=26, trails={"L": (10, 16), "R": (10, 16)}, drag=0.9)
    # Combo branch (heavy after L2-L4): rising scissor (hit f9)
    C("Atk_Daggers_Rising",
      [(1, p["Guard_Low"], 0.0), (5, p["Guard_Low"], 0.4), (9, p["Rising_Cross"], 0.0), (14, p["Rising_Cross"], 0.7),
       (30, G, 1.0)],
      root=[(1, 0.0), (5, 0.05), (10, 0.5), (13, 0.55)],
      steps=shuffle("L", 4, 9, 6, 13, gf["L"], gf["R"], lift=0.08),
      hits=[9], link=22, trails={"L": (5, 12), "R": (5, 12)}, drag=1.0)
    # Finisher: leap in, plunge, rip out, hop back (hit f13)
    C("Atk_Daggers_Finisher",
      [(1, G, 0.0), (6, p["Guard_Low"], 0.5), (10, p["Heavy_Leap"], 0.2), (13, p["Finisher_Plunge"], 0.0),
       (26, p["Finisher_Plunge"], 0.9), (31, p["Rising_Cross"], 0.3), (44, G, 1.0)],
      root=[(1, 0.0), (6, 0.0), (13, 1.6), (26, 1.65), (34, 1.05), (40, 1.0)],
      steps=[Step("L", 7, 13, p["Finisher_Plunge"].feet["L"], lift=0.28),
             Step("R", 8, 13, p["Finisher_Plunge"].feet["R"], lift=0.24),
             Step("L", 28, 35, gf["L"], lift=0.08), Step("R", 30, 36, gf["R"], lift=0.06)],
      hits=[13], link=36, trails={"L": (9, 15), "R": (9, 15)}, drag=0.8)
    return out


def _spin_feet(spin_start, air, land, settle):
    """L4 footwork: right-lead start, hop and turn 360 about the root, land in left lead."""
    a0, a1 = air
    start, end = RIGHT_LEAD, GUARD_FEET

    def lerp_foot(f0, f1, t):
        return Foot(f0.x + (f1.x - f0.x) * t, f0.y + (f1.y - f0.y) * t, f0.yaw + (f1.yaw - f0.yaw) * t,
                    f0.roll + (f1.roll - f0.roll) * t)

    def fn(f):
        out = {}
        for side in ("L", "R"):
            if f <= a0:
                t = max(0.0, (f - spin_start) / (a0 - spin_start))
                ft = lerp_foot(start[side], Foot(start[side].x * 0.6, start[side].y * 0.6, start[side].yaw,
                                                 22), t * t)
                out[side] = (Vector((ft.x, ft.y, 0)), ft.yaw, ft.roll)
                continue
            if f >= land:
                t = min(1.0, (f - land) / (settle - land))
                ft = lerp_foot(end[side], end[side], t)
                out[side] = (Vector((ft.x, ft.y, 0)), ft.yaw, ft.roll * t + 18 * (1 - t))
                continue
            u = (f - a0) / (land - a0)
            e = u * u * (3 - 2 * u)
            ang = math.radians(360 * e)
            # interpolate the stance in a frame that turns with the body
            ft = lerp_foot(Foot(start[side].x * 0.6, start[side].y * 0.6, start[side].yaw, 22), end[side], e)
            c, s = math.cos(ang), math.sin(ang)
            px, py = ft.x * c - ft.y * s, ft.x * s + ft.y * c
            z = 0.16 * math.sin(math.pi * min(1.0, (f - a0) / (a1 - a0)))
            out[side] = (Vector((px, py, z)), ft.yaw + 360 * e, 10 + 20 * math.sin(math.pi * u))
        return out
    return fn


# ============================================================ LOCOMOTION
CYCLE = 18          # frames per locomotion cycle (shared, so blends stay in phase)
WALK_SPEED = 2.4    # native m/s at playback rate 1 (the game rescales to the real speed)
BACK_SPEED = 1.9
SIDE_SPEED = 2.0
RUN_SPEED = 6.4


def _gait(f, speed, duty, lift, base, axis=(0, -1), lag_r=0.5, rolls=(28, -12)):
    """Analytic two-foot gait in root-local space; left foot lands at frame 1.

    A planted foot slides against the travel direction at exactly `speed`
    (sweep = speed * duty * cycle time), so the game's movement matches it."""
    out = {}
    ax = Vector((axis[0], axis[1], 0)).normalized()
    sweep = speed * duty * CYCLE / E.FPS
    for side, off in (("L", 0.0), ("R", -lag_r)):
        ph = ((f - 1) / CYCLE + off) % 1.0
        b = base[side]
        if ph < duty:                      # stance: planted, slides back under the body
            u = ph / duty
            along = sweep * (0.5 - u)
            z = 0.0
            roll = rolls[0] * max(0.0, (u - 0.65) / 0.35) ** 1.5      # heel peels off late
        else:                              # swing: lifted arc back to the front
            u = (ph - duty) / (1 - duty)
            e = u * u * (3 - 2 * u)
            along = sweep * (-0.5 + e)
            z = lift * math.sin(math.pi * u) ** 1.2
            roll = rolls[0] * (1 - u / 0.6) if u < 0.6 else rolls[1] * math.sin(math.pi * (u - 0.6) / 0.4)
        pos = Vector((b.x, b.y, 0)) + ax * along
        pos.z = z
        out[side] = (pos, b.yaw, roll + b.roll * (1 if ph < duty else 0))
    return out


def locomotion(R, poses):
    """Walk in guard (forward, back, left, right) and the sprint. All CYCLE frames,
    left foot landing at frame 1, so the game can blend them in phase."""
    out = []
    narrow = {"L": Foot(0.11, -0.02, -4), "R": Foot(-0.11, 0.02, 4)}
    T = CYCLE / E.FPS

    def cycle_keys(fn, n=8):
        keys = []
        for i in range(n + 1):
            t = i / n
            s = math.cos(4 * math.pi * t)       # +1 at each foot contact (low point)
            keys.append((1 + t * CYCLE, R(f"_{fn.__name__}{i}", fn(t, s)), 0.0))
        return keys

    lead = A((0.10, -0.34, 0.05), (0.55, 0.15, -0.8), (-0.05, -0.35, 0.94), (0.20, 0.50, -0.84))
    rear = A((-0.08, -0.24, -0.05), (-0.70, 0.35, -0.6), (0.25, -0.55, 0.80), (0.55, -0.75, -0.25))

    def bob(a, dz):
        return A((a["fist"][0], a["fist"][1], a["fist"][2] + dz), a["elbow"], a["knuckles"], a["blade"])

    # forward: a low stalk in guard, hips swing with each step
    def walk_f(t, s):
        sw = math.sin(2 * math.pi * t)
        return stance(drop=0.15 + 0.02 * s, turn=-14 + 7 * sw, twist=6 - 5 * sw, lean=14, hips_x=0.015 * sw,
                      L=bob(lead, 0.012 * s), R=bob(rear, 0.012 * s), feet=narrow)
    out.append(Clip("Loop_Walk_Daggers_F", cycle_keys(walk_f), loop=True, root=[(1, 0.0), (1 + CYCLE, WALK_SPEED * T)],
                    feet_fn=lambda f: _gait(f, WALK_SPEED, 0.58, 0.08, narrow), meta={"dir": [0, 1]}))

    # back: guard held high, short careful steps
    def walk_b(t, s):
        sw = math.sin(2 * math.pi * t)
        return stance(drop=0.16 + 0.015 * s, turn=-18 + 5 * sw, twist=8, lean=10, hips_y=0.03,
                      L=bob(lead, 0.03), R=bob(rear, 0.02), feet=narrow)
    out.append(Clip("Loop_Walk_Daggers_B", cycle_keys(walk_b), loop=True, root=[(1, 0.0), (1 + CYCLE, BACK_SPEED * T)],
                    feet_fn=lambda f: _gait(f, BACK_SPEED, 0.62, 0.05, narrow, axis=(0, 1)), meta={"dir": [0, -1]}))

    # sideways: fighting stance kept, the foot toward travel leads, the other follows
    for name, sgn in (("L", 1), ("R", -1)):
        def walk_s(t, s, sgn=sgn):
            return stance(drop=0.15 + 0.015 * s, hips_x=0.02 * sgn * math.sin(2 * math.pi * t),
                          L=bob(lead, 0.01 * s), R=bob(rear, 0.01 * s))
        walk_s.__name__ = f"walk_{name.lower()}"
        lag = 0.3 if sgn > 0 else 0.7          # trailing foot follows the leading one
        out.append(Clip(f"Loop_Walk_Daggers_{name}", cycle_keys(walk_s), loop=True,
                        root=[(1, 0.0), (1 + CYCLE, SIDE_SPEED * T)],
                        feet_fn=lambda f, sgn=sgn, lag=lag: _gait(f, SIDE_SPEED, 0.6, 0.05, GUARD_FEET,
                                                                   axis=(sgn, 0), lag_r=lag),
                        meta={"dir": [-sgn, 0]}))

    # sprint: blades trail along the forearms, counter-swing of hips and chest
    def run(t, s):
        sw = math.sin(2 * math.pi * t)
        return stance(drop=0.07 - 0.04 * s, turn=-4 + 10 * sw, twist=-16 * sw, lean=24, pelvis=-2, hips_y=-0.03,
                      L=A((0.22, 0.10 - 0.22 * sw, -0.32 + 0.08 * sw), (0.3, 0.5, -0.8), (0.1, -0.5, -0.85),
                          (0.1, 0.85, 0.5)),
                      R=A((-0.22, 0.10 + 0.22 * sw, -0.32 - 0.08 * sw), (-0.3, 0.5, -0.8), (-0.1, -0.5, -0.85),
                          (-0.1, 0.85, 0.5)),
                      feet=narrow, look=(0, -1, 0.12))
    out.append(Clip("Loop_Run_Daggers", cycle_keys(run), loop=True, root=[(1, 0.0), (1 + CYCLE, RUN_SPEED * T)],
                    feet_fn=lambda f: _gait(f, RUN_SPEED, 0.21, 0.22, narrow, rolls=(42, -16)), meta={"dir": [0, 1]}))
    return out


# ================================================================ BUILD
COMBO = ["Atk_Daggers_L1", "Atk_Daggers_L2", "Atk_Daggers_L3", "Atk_Daggers_L4", "Atk_Daggers_L5"]


def build(K, arm):
    """Bake the pose library and every dagger clip. Returns clip_events data."""
    R = Resolver(K, arm)
    lib = library()
    poses = {}
    events = {"clips": {}, "poses": {}, "combo": {"Daggers": COMBO}}
    for name, (spec, meta) in lib.items():
        poses[name] = R(name, spec, meta)
    for name, pose in poses.items():
        clip_name = f"Pose_Daggers_{name}"
        E.bake_pose(arm, pose, clip_name)
        events["poses"][clip_name] = {"name": name.replace("_", " "), **pose.meta}
    for clip in clips(R, poses) + locomotion(R, poses):
        # a previous builder may have made a clip of the same name: replace it
        old = bpy.data.actions.get(clip.name)
        if old is not None:
            bpy.data.actions.remove(old)
        events["clips"][clip.name] = E.bake(arm, clip)
    return events
