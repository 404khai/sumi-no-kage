"""Shared moveset for every character on the common skeleton (playable-slice v1).

Called from build_kage.build_actions(), so Kage, the Knight and the Viking all
get identical clips. Poses are authored as data: world-space aim directions for
limbs (character faces -Y, left = +X) and, for the two-handed halberd, IK grip
targets + a shaft direction so the weapon always sits in both fists.

Clip naming (the Godot side keys off these prefixes):
  Stance_*  looping holds        Loop_*  looping cycles
  Atk_<Family>_*  attacks        Act_*   one-shot actions
Families: Daggers (daggers + handblades), Halberd.

These are blocking-quality game animations: readable key poses with timing,
made for gameplay feel, not final polish.
"""

import math

import bpy
from mathutils import Vector

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _n(v):
    return Vector(v).normalized()


# ----------------------------------------------------------------------- bodies
def legs_guard(b=0.0):
    return {
        "LeftUpperLeg": {"aim": (0.16, -0.58, -0.80), "twist": 15},
        "LeftLowerLeg": {"aim": (0.04, 0.10, -0.995)},
        "LeftFoot": {"aim": (0.22, -0.95, -0.20)},
        "RightUpperLeg": {"aim": (-0.16, 0.36, -0.92), "twist": -10},
        "RightLowerLeg": {"aim": (-0.06, 0.50, -0.86)},
        "RightFoot": {"aim": (-0.30, -0.86, -0.42)},
    }


def legs_lunge(depth=1.0):
    """Deep forward lunge on the left leg."""
    return {
        "LeftUpperLeg": {"aim": (0.14, -0.85, -0.50 * depth - 0.2), "twist": 10},
        "LeftLowerLeg": {"aim": (0.02, 0.15, -0.99)},
        "LeftFoot": {"aim": (0.15, -0.97, -0.15)},
        "RightUpperLeg": {"aim": (-0.12, 0.55, -0.82), "twist": -8},
        "RightLowerLeg": {"aim": (-0.04, 0.80, -0.60)},
        "RightFoot": {"aim": (-0.1, -0.5, -0.86)},
    }


def legs_run(phase):
    """phase 0..1. Left leg forward at 0, right leg forward at 0.5."""
    out = {}
    for side, off in (("Left", 0.0), ("Right", 0.5)):
        p = (phase + off) % 1.0
        sx = 0.10 if side == "Left" else -0.10
        swing = math.cos(p * 2 * math.pi)           # +1 forward, -1 back
        lift = max(0.0, math.sin(p * 2 * math.pi))  # knee lift in the forward swing
        out[f"{side}UpperLeg"] = {"aim": (sx * 0.4, -0.62 * swing - 0.1 * lift, -0.78)}
        out[f"{side}LowerLeg"] = {"aim": (0.0, 0.15 + 0.75 * lift + 0.25 * max(0, -swing), -0.85)}
        out[f"{side}Foot"] = {"aim": (sx * 0.5, -0.95, -0.25 + 0.3 * lift)}
    return out


def torso(lean=8.0, twist=0.0, hips_drop=0.10, hips_turn=-24.0, side_bend=0.0, b=0.0, fwd=0.02):
    return {
        "Hips": {"loc": (0, fwd, -hips_drop - 0.008 * b), "rot": [(Z, hips_turn), (X, -4), (Y, side_bend)]},
        "Spine": [(X, lean + 1.5 * b), (Z, 6 + twist * 0.5)],
        "Chest": [(X, lean * 0.6 + 1.5 * b), (Z, 6 + twist * 0.5)],
        "UpperChest": [(X, 2 - b)],
        "Neck": [(X, -lean * 0.8), (Z, -twist * 0.4 + 6)],
        "Head": [(X, -lean * 0.5 - 1.5 * b), (Z, -twist * 0.4)],
    }


def arms_dagger_guard(b=0.0):
    return {
        "LeftShoulder": [(X, -8)],
        "LeftUpperArm": {"aim": (0.36, -0.62, -0.46 + 0.02 * b), "twist": -30},
        "LeftLowerArm": {"aim": (-0.38, -0.52, 0.62)},
        "LeftHand": {"aim": (-0.34, -0.62, 0.50), "twist": 20},
        "RightShoulder": [(X, 6)],
        "RightUpperArm": {"aim": (-0.34, 0.22, -0.90), "twist": 20},
        "RightLowerArm": {"aim": (0.22, -0.88, 0.22 + 0.02 * b)},
        "RightHand": {"aim": (0.30, -0.92, 0.05), "twist": -30},
    }


def arm(side, upper, lower, hand=None, twist=0.0):
    S = "Left" if side == "L" else "Right"
    out = {f"{S}UpperArm": {"aim": upper, "twist": twist}, f"{S}LowerArm": {"aim": lower}}
    out[f"{S}Hand"] = {"aim": hand or lower}
    return out


# -------------------------------------------------------------------- authoring
class Author:
    def __init__(self, K, arm):
        self.K, self.arm = K, arm

    def clip(self, name, keys, ik=False):
        """keys: [(frame, spec)] for FK clips, [(frame, (body, grip, shaft))] for halberd clips."""
        K, arm = self.K, self.arm
        K.new_action(arm, name)
        for frame, spec in keys:
            if ik:
                self.key_halberd(frame, *spec)
            else:
                full = {}
                full.update(spec)
                full.update(K.fist("L"))
                full.update(K.fist("R"))
                K.pose(arm, full)
                K.key_all(arm, frame)

    off = 0.52

    def key_halberd(self, frame, body, grip_r, shaft, up=(0, 0, -1), off=None):
        K, arm = self.K, self.arm
        off = self.off if off is None else off
        shaft = _n(shaft)
        edge = Vector(up)
        edge = (edge - shaft * edge.dot(shaft)).normalized()
        arm["ik_arm_L"] = arm["ik_arm_R"] = 1.0
        full = dict(body)
        full.update(K.fist("L"))
        full.update(K.fist("R"))
        K.pose(arm, full)
        bpy.context.view_layer.update()
        pb = arm.pose.bones

        def place(ctrl, side, grip):
            pb[ctrl].location = pb[ctrl].bone.matrix_local.to_3x3().inverted() @ (
                K._wrist_target(arm, side, Vector(grip)) - pb[ctrl].bone.head_local)

        place("CTRL_IK_Hand.R", "R", grip_r)
        K.orient_socket(arm, "RightHand", "RightHandWeapon", shaft, edge)
        bpy.context.view_layer.update()
        s_m = pb["RightHandWeapon"].matrix
        axis = (s_m.to_3x3() @ Vector((0, 1, 0))).normalized()
        place("CTRL_IK_Hand.L", "L", s_m.translation + axis * off)
        K.orient_socket(arm, "RightHand", "RightHandWeapon", shaft, edge)
        K.orient_socket(arm, "LeftHand", "LeftHandWeapon", axis, edge)
        K.key_all(arm, frame, props={"ik_arm_L": 1.0, "ik_arm_R": 1.0})
        arm["ik_arm_L"] = arm["ik_arm_R"] = 0.0


def M(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


# ------------------------------------------------------------------- dagger set
def dagger_clips(A):
    guard = lambda b=0.0: M(torso(b=b), legs_guard(), arms_dagger_guard(b))  # noqa: E731
    G = guard()

    A.clip("Loop_Run_Daggers", [
        (f, M(torso(lean=18, hips_drop=0.05, hips_turn=-6, b=0, fwd=-0.03), legs_run((f - 1) / 20),
              arm("L", (0.25, -0.55 + 0.25 * math.cos((f - 1) / 20 * 6.283), -0.75), (0.0, -0.75, 0.55)),
              arm("R", (-0.25, 0.45 - 0.25 * math.cos((f - 1) / 20 * 6.283), -0.80), (-0.05, -0.55, 0.3)),
              {"Hips": {"loc": (0, -0.03, -0.05 - 0.03 * abs(math.sin((f - 1) / 20 * 6.283))),
                        "rot": [(Z, -6), (X, -4)]}}))
        for f in (1, 6, 11, 16, 21)])

    # L1: rear (right) hand hooks across the body
    A.clip("Atk_Daggers_L1", [
        (1, G),
        (5, M(torso(twist=-30, lean=10), legs_guard(), arms_dagger_guard(),
              arm("R", (-0.65, 0.35, -0.55), (-0.45, -0.35, 0.45), twist=20))),
        (9, M(torso(twist=35, lean=14, hips_turn=-10), legs_lunge(0.6), arms_dagger_guard(),
              arm("R", (0.35, -0.90, -0.10), (0.92, -0.35, 0.05), (0.85, 0.2, 0.0), twist=-20))),
        (13, M(torso(twist=40, lean=12, hips_turn=-8), legs_lunge(0.6), arms_dagger_guard(),
               arm("R", (0.55, -0.70, -0.25), (0.75, 0.45, -0.1), twist=-30))),
        (22, G)])

    # L2: lead (left) hand cuts down diagonally
    A.clip("Atk_Daggers_L2", [
        (1, G),
        (5, M(torso(twist=20, lean=4), legs_guard(), arms_dagger_guard(),
              arm("L", (0.45, -0.25, 0.65), (0.05, -0.35, 0.93), twist=-30))),
        (9, M(torso(twist=-30, lean=18), legs_lunge(0.8), arms_dagger_guard(),
              arm("L", (-0.10, -0.92, -0.30), (-0.65, -0.55, -0.45), twist=-10))),
        (13, M(torso(twist=-35, lean=16), legs_lunge(0.8), arms_dagger_guard(),
               arm("L", (-0.35, -0.70, -0.55), (-0.70, 0.10, -0.60)))),
        (22, G)])

    # L3: double thrust with a lunge (the code moves the body forward)
    A.clip("Atk_Daggers_L3", [
        (1, G),
        (6, M(torso(lean=4, hips_turn=-10), legs_guard(),
              arm("L", (0.30, 0.40, -0.80), (0.15, -0.70, 0.60)), arm("R", (-0.30, 0.40, -0.80), (-0.15, -0.70, 0.60)))),
        (10, M(torso(lean=22, hips_turn=-4, hips_drop=0.16), legs_lunge(1.0),
               arm("L", (0.12, -0.97, -0.10), (0.02, -0.99, 0.05), twist=-80),
               arm("R", (-0.12, -0.97, -0.05), (-0.02, -0.99, 0.08), twist=80))),
        (15, M(torso(lean=20, hips_turn=-4, hips_drop=0.16), legs_lunge(1.0),
               arm("L", (0.15, -0.90, -0.30), (0.05, -0.95, -0.2)), arm("R", (-0.15, -0.90, -0.30), (-0.05, -0.95, -0.2)))),
        (26, G)])

    # Heavy: crouch, then a full spinning double slash with arms flung wide
    crouch = M(torso(lean=20, hips_drop=0.22), legs_lunge(1.0),
               arm("L", (-0.2, -0.5, -0.4), (-0.7, -0.3, 0.6)), arm("R", (0.2, -0.5, -0.4), (0.7, -0.3, 0.6)))
    wide = lambda turn: M(torso(lean=6, hips_drop=0.12, hips_turn=turn), legs_guard(),  # noqa: E731
                          arm("L", (0.95, -0.15, 0.05), (0.98, 0.1, 0.1)), arm("R", (-0.95, -0.15, 0.05), (-0.98, 0.1, 0.1)))
    A.clip("Atk_Daggers_Heavy", [(1, G), (9, crouch), (13, wide(-24 - 120)), (16, wide(-24 - 240)),
                                 (19, wide(-24 - 355)), (30, G)])

    # Finisher: leap and plunge both blades down into a staggered foe
    A.clip("Atk_Daggers_Finisher", [
        (1, G),
        (8, M(torso(lean=-6, hips_drop=-0.12), legs_run(0.25),
              arm("L", (0.2, -0.45, 0.87), (0.05, 0.2, 0.98)), arm("R", (-0.2, -0.45, 0.87), (-0.05, 0.2, 0.98)))),
        (13, M(torso(lean=35, hips_drop=0.38), legs_lunge(1.2),
               arm("L", (0.12, -0.85, -0.50), (0.0, -0.35, -0.94)), arm("R", (-0.12, -0.85, -0.50), (0.0, -0.35, -0.94)))),
        (24, M(torso(lean=35, hips_drop=0.38), legs_lunge(1.2),
               arm("L", (0.12, -0.85, -0.50), (0.0, -0.35, -0.94)), arm("R", (-0.12, -0.85, -0.50), (0.0, -0.35, -0.94)))),
        (36, G)])

    block = M(torso(lean=12, hips_drop=0.14), legs_guard(),
              arm("L", (0.30, -0.70, -0.25), (-0.55, -0.40, 0.73), twist=-40),
              arm("R", (-0.30, -0.70, -0.25), (0.55, -0.40, 0.73), twist=40))
    A.clip("Stance_Block_Daggers", [(1, block), (20, block)])


# ------------------------------------------------------------------ halberd set
def halberd_clips(A, family="Halberd", off=0.52, reach=1.0):
    """Two-handed clips. family 'Halberd' = polearms (halberd, naginata, off hand 0.52 m up
    the shaft); 'Greatsword' = two-handed swords (hands together on the grip)."""
    def body(twist=0.0, lean=6.0, drop=0.09, turn=-18.0, legs=None, b=0.0):
        d = torso(lean=lean, twist=twist, hips_drop=drop, hips_turn=turn, b=b, fwd=0.03)
        d.update(legs or legs_guard())
        return d

    A.off = off
    guard = (body(), (-0.17, -0.06, 0.90), (0.42, -0.70, 0.50))
    if family != "Halberd":  # sword guard: hilt at the navel, blade raised (vom Tag / chudan)
        guard = (body(), (-0.08, -0.16, 0.98), (0.20, -0.55, 0.81))
        A.clip(f"Stance_{family}_Idle", [(1, guard), (31, (body(b=1.0), (-0.08, -0.16, 0.97), (0.20, -0.55, 0.81))),
                                          (61, guard)], ik=True)

    A.clip(f"Loop_Run_{family}", [
        (f, (M(torso(lean=14, hips_drop=0.05, hips_turn=-10, fwd=0.0), legs_run((f - 1) / 20),
               {"Hips": {"loc": (0, 0.0, -0.05 - 0.03 * abs(math.sin((f - 1) / 20 * 6.283))), "rot": [(Z, -10)]}}),
             (-0.18, 0.02, 0.95), (0.30, -0.55, 0.78)))
        for f in (1, 6, 11, 16, 21)], ik=True)

    # L1: horizontal sweep, right to left
    A.clip(f"Atk_{family}_L1", [
        (1, guard),
        (7, (body(twist=-40, turn=10), (-0.30, 0.10, 1.00), (-0.80, 0.40, 0.35))),
        (12, (body(twist=40, lean=12, turn=-40, legs=legs_lunge(0.7)), (-0.10, -0.25, 1.00), (0.75, -0.65, 0.10),
              (0, 0, 1))),
        (16, (body(twist=55, lean=10, turn=-55, legs=legs_lunge(0.7)), (0.05, -0.20, 1.00), (0.95, 0.20, 0.10),
              (0, 0, 1))),
        (26, guard)], ik=True)

    # L2: driving thrust with the spike
    A.clip(f"Atk_{family}_L2", [
        (1, guard),
        (6, (body(lean=2, turn=-25), (-0.20, 0.22, 1.02), (0.20, -0.95, 0.15))),
        (11, (body(lean=18, turn=-12, drop=0.16, legs=legs_lunge(1.0)), (-0.10, -0.45, 1.05), (0.12, -0.99, 0.05))),
        (15, (body(lean=18, turn=-12, drop=0.16, legs=legs_lunge(1.0)), (-0.10, -0.42, 1.03), (0.12, -0.99, 0.0))),
        (26, guard)], ik=True)

    # Heavy: overhead axe chop
    A.clip(f"Atk_{family}_Heavy", [
        (1, guard),
        (10, (body(lean=-10, turn=-10, drop=0.04), (-0.12, 0.05, 1.45), (0.05, 0.45, 0.89), (0, -1, 0))),
        (15, (body(lean=28, turn=-10, drop=0.22, legs=legs_lunge(1.1)), (-0.10, -0.40, 1.00), (0.05, -0.75, -0.65),
              (0, 0, -1))),
        (22, (body(lean=28, turn=-10, drop=0.22, legs=legs_lunge(1.1)), (-0.10, -0.38, 0.95), (0.05, -0.70, -0.70),
              (0, 0, -1))),
        (34, guard)], ik=True)

    # Finisher: rising hook then a crushing downward drive of the spike
    A.clip(f"Atk_{family}_Finisher", [
        (1, guard),
        (9, (body(lean=-12, drop=0.0), (-0.10, 0.0, 1.55), (0.05, -0.25, 0.97), (0, -1, 0))),
        (14, (body(lean=32, drop=0.30, legs=legs_lunge(1.2)), (-0.05, -0.35, 1.15), (0.02, -0.45, -0.89), (0, -1, 0))),
        (26, (body(lean=32, drop=0.30, legs=legs_lunge(1.2)), (-0.05, -0.35, 1.12), (0.02, -0.45, -0.89), (0, -1, 0))),
        (38, guard)], ik=True)

    blk = (body(lean=10, drop=0.14), (-0.25, -0.20, 1.20), (0.98, -0.10, 0.15), (0, 0, 1))
    A.clip(f"Stance_Block_{family}", [(1, blk), (20, blk)], ik=True)


# --------------------------------------------------------------- shared actions
def shared_clips(A):
    G = M(torso(), legs_guard(), arms_dagger_guard())
    tuck = M(torso(lean=45, hips_drop=0.45, hips_turn=0), legs_lunge(1.4),
             arm("L", (0.3, -0.3, -0.9), (0.1, -0.9, 0.4)), arm("R", (-0.3, -0.3, -0.9), (-0.1, -0.9, 0.4)))
    A.clip("Act_Dodge", [(1, G), (4, tuck), (12, tuck), (18, G)])
    hit = M(torso(lean=-18, twist=15, hips_drop=0.06), legs_guard(),
            arm("L", (0.6, 0.2, -0.75), (0.7, -0.2, -0.3)), arm("R", (-0.6, 0.3, -0.7), (-0.7, -0.1, -0.4)))
    A.clip("Act_Hit", [(1, G), (4, hit), (14, G)])
    reel = M(torso(lean=-25, twist=-20, hips_drop=0.18, side_bend=12), legs_lunge(0.6),
             arm("L", (0.95, 0.1, 0.1), (0.9, 0.3, 0.3)), arm("R", (-0.9, 0.3, -0.2), (-0.8, 0.5, 0.0)))
    A.clip("Act_Stagger", [(1, G), (5, reel), (40, reel), (50, G)])
    dead = M({"Hips": {"loc": (0, 0.55, -0.78), "rot": [(X, 78)]}, "Spine": [(X, -5)], "Neck": [(X, 20)]},
             {"LeftUpperLeg": {"aim": (0.2, -0.3, 0.6)}, "LeftLowerLeg": {"aim": (0.25, -0.6, -0.2)},
              "RightUpperLeg": {"aim": (-0.2, -0.5, 0.4)}, "RightLowerLeg": {"aim": (-0.2, -0.9, 0.1)}},
             arm("L", (0.9, 0.3, 0.1), (0.8, 0.5, 0.0)), arm("R", (-0.9, 0.1, 0.2), (-0.9, -0.3, 0.1)))
    A.clip("Act_Death", [(1, hit), (10, M(reel)), (24, dead), (40, dead)])


def build(K, arm):
    A = Author(K, arm)
    dagger_clips(A)
    halberd_clips(A)
    halberd_clips(A, family="Greatsword", off=0.13)
    shared_clips(A)
