"""Joint layout for Kage, the assassin — the single source of truth shared by the
body mesh generator and the armature builder.

Coordinates are Blender metres, Z up, character facing -Y, character-left = +X.
Bone names follow Godot's SkeletonProfileHumanoid so the BoneMap auto-matches
and animations can be retargeted without manual mapping.
"""

from __future__ import annotations

import math

from mathutils import Vector

HEIGHT = 1.74  # crown of the head, without hood

# A-pose: arms 40 degrees below horizontal (better shoulder deformation than T-pose)
ARM_DIR = Vector((math.cos(math.radians(40)), 0.0, -math.sin(math.radians(40))))
THUMB_SIDE = Vector((0.0, -1.0, 0.0))                   # palms face the thighs
PALM_NORMAL = ARM_DIR.cross(THUMB_SIDE).normalized()   # points out of the palm


def V(x, y, z):
    return Vector((x, y, z))


def _curl(start, direction, lengths, curl):
    pts = [start.copy()]
    d = direction.normalized()
    for i, L in enumerate(lengths):
        d = (d + PALM_NORMAL * curl * (i + 1)).normalized()
        pts.append(pts[-1] + d * L)
    return pts


def left_side_joints():
    """Joint positions for the character's left side (+X)."""
    j = {}
    j["clavicle"] = V(0.022, 0.005, 1.405)
    j["shoulder"] = V(0.172, 0.018, 1.412)
    j["elbow"] = j["shoulder"] + ARM_DIR * 0.285 + V(0, 0.022, 0)
    j["wrist"] = j["elbow"] + ARM_DIR * 0.252 + V(0, -0.024, 0)
    w = j["wrist"]
    d, s, n = ARM_DIR, THUMB_SIDE, PALM_NORMAL
    j["palm"] = w + d * 0.045 + n * 0.004
    # knuckles spread across the palm, thumb side first
    knuckles = {
        "Index": w + d * 0.088 + s * 0.026,
        "Middle": w + d * 0.092 + s * 0.006,
        "Ring": w + d * 0.088 - s * 0.013,
        "Little": w + d * 0.080 - s * 0.030,
    }
    lengths = {
        "Index": (0.040, 0.024, 0.020),
        "Middle": (0.044, 0.027, 0.021),
        "Ring": (0.041, 0.025, 0.020),
        "Little": (0.032, 0.019, 0.017),
    }
    for name, k in knuckles.items():
        splay = (s * {"Index": 0.06, "Middle": 0.0, "Ring": -0.05, "Little": -0.11}[name])
        pts = _curl(k, d + splay, lengths[name], 0.10)
        for i, p in enumerate(pts):
            j[f"{name}{i}"] = p
    thumb_dir = (d * 0.55 + s * 0.75 + n * 0.35).normalized()
    t0 = w + d * 0.018 + s * 0.016 + n * 0.012
    t1 = t0 + thumb_dir * 0.034
    t_dir2 = (thumb_dir + d * 0.5).normalized()
    t2 = t1 + t_dir2 * 0.030
    t3 = t2 + (t_dir2 + d * 0.3).normalized() * 0.026
    j["Thumb0"], j["Thumb1"], j["Thumb2"], j["Thumb3"] = t0, t1, t2, t3
    # grip socket: centre of the closed fist, axis through the fist (thumb side)
    j["grip"] = w + d * 0.062 + n * 0.022
    # legs
    j["hip"] = V(0.092, 0.002, 0.925)
    j["knee"] = V(0.100, -0.012, 0.515)
    j["ankle"] = V(0.106, 0.028, 0.088)
    j["heel"] = V(0.104, 0.062, 0.030)
    j["ball"] = V(0.112, -0.098, 0.026)
    j["toe"] = V(0.114, -0.168, 0.022)
    # eyes
    j["eye"] = V(0.032, -0.082, 1.640)
    return j


CENTER = {
    "root": V(0, 0, 0),
    "pelvis": V(0, 0.004, 0.905),
    "hips": V(0, 0.006, 0.975),
    "spine": V(0, 0.010, 1.075),
    "chest": V(0, 0.006, 1.190),
    "upper_chest": V(0, 0.004, 1.300),
    "neck": V(0, 0.018, 1.455),
    "head": V(0, 0.012, 1.560),
    "head_top": V(0, 0.004, 1.760),
}


def mirror(p: Vector) -> Vector:
    return Vector((-p.x, p.y, p.z))


def joints():
    """All joints, with `L_`/`R_` prefixes for sided ones."""
    out = dict(CENTER)
    for k, p in left_side_joints().items():
        out["L_" + k] = p
        out["R_" + k] = mirror(p)
    return out


# Cloth chains (rest pose = gently streaming, which reads as motion in stills and
# gives spring bones a sensible target). Each entry: list of control points.
def tie_chain(side: int, segments: int, length: float):
    """Hood tie tails streaming from the knot at the back of the head."""
    knot = V(0.018 * side, 0.112, 1.612)
    pts = [knot]
    d = Vector((0.10 * side, 0.55, -0.82)).normalized()
    seg = length / segments
    for i in range(segments):
        # sweep from back-and-down to mostly down, slight outward drift
        t = i / max(segments - 1, 1)
        d = Vector((0.13 * side * (1 - t) + 0.05 * side, 0.55 - 0.32 * t, -0.82 - 0.1 * t)).normalized()
        pts.append(pts[-1] + d * seg)
    return pts


def sash_chain(side: int, segments: int, length: float):
    """Obi tails hanging from the knot at the lower back."""
    knot = V(0.055 * side, 0.135, 1.025)
    pts = [knot]
    seg = length / segments
    for i in range(segments):
        t = i / max(segments - 1, 1)
        d = Vector((0.08 * side * (1 - t), 0.30 - 0.2 * t, -1.0)).normalized()
        pts.append(pts[-1] + d * seg)
    return pts


TIE_L = dict(side=1, segments=6, length=0.92)
TIE_R = dict(side=-1, segments=5, length=0.74)
SASH_L = dict(side=1, segments=5, length=0.62)
SASH_R = dict(side=-1, segments=4, length=0.48)
