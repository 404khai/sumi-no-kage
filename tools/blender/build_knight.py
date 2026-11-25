"""Build the Ashen Knight (docs/reference/characters/knight1.jpeg).

    blender -b --factory-startup --python tools/blender/build_knight.py [-- --preview]

Output: assets_src/characters/knight/knight.blend
Same skeleton, bone names, sockets and animation set as Kage (build_kage.py),
plus three cape chains. The Tie chains drive the helm plume; the Sash chains
drive the tabard tails.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import armor_kit as ak  # noqa: E402
import build_kage as K  # noqa: E402
import kage_skeleton as ks  # noqa: E402
import sumi  # noqa: E402

V = ks.V
ARGS = K.ARGS
OUT = sumi.repo_path("assets_src", "characters", "knight", "knight.blend")
J = ks.joints()
M = {}


def materials():
    M["plate"] = sumi.material("M_Knight_Plate", 0.60, roughness=0.4, metallic=0.6)
    M["mail"] = sumi.material("M_Knight_Mail", 0.30)
    M["cloth"] = sumi.material("M_Knight_Cloth", 0.09)
    M["under"] = sumi.material("M_Knight_Under", 0.16)
    M["leather"] = sumi.material("M_Knight_Leather", 0.40)
    M["red"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)
    K.MAT.update(eye=M["red"], skin=M["under"], cloth=M["mail"])


# cloth chains for this character ---------------------------------------
def plume_chain(side, segments, length):
    return ak.chain(V(0.02 * side, 0.07, 1.805), (0.06 * side, 0.85, -0.2), (0.1 * side, 0.35, -0.95),
                    segments, length)


def tabard_chain(side, segments, length):
    return ak.chain(V(0.07 * side, 0.205, 0.985), (0.02 * side, 0.18, -1), (0.03 * side, 0.30, -1), segments,
                    length + 0.15)


CAPE = [(f"Cape{n}", ak.chain(V(x, 0.155, 1.405), (x * 0.4, 0.28, -1), (x * 0.9, 0.42, -1), 6, L), "UpperChest")
        for n, x, L in (("L", 0.13, 1.05), ("M", 0.0, 1.12), ("R", -0.13, 0.98))]


def helmet(col, fit):
    """Beaked great helm with a crest, an eye slit and breathing slots."""
    n = 48
    axis = V(0, 0.004, 0)
    th_ = [2 * math.pi * i / n for i in range(n)]
    dirs = [Vector((math.sin(t), -math.cos(t), 0)) for t in th_]
    crown_z, top_z = 1.74, 1.86
    levels = [1.858, 1.85, 1.835, 1.81, 1.78, 1.74, 1.71, 1.68, 1.655, 1.635, 1.61, 1.585, 1.56, 1.535, 1.51,
              1.49, 1.47]
    crown = None
    rings = []
    for z in levels:
        zs = min(z, crown_z)
        rad = []
        for t, d in zip(th_, dirs):
            r = (fit.outermost(axis + V(0, 0, max(zs, 1.53)), d, 0.3) or 0.07) + 0.032
            fr = max(0.0, math.cos(t))
            beak = 0.065 * fr ** 10 * math.exp(-((zs - 1.60) / 0.07) ** 2)   # hounskull snout
            brow = 0.018 * fr ** 4 * math.exp(-((zs - 1.672) / 0.02) ** 2)  # visor lip over the slit
            gorget = 0.03 * max(0.0, (1.53 - z) / 0.06)
            rad.append(r + beak + brow + gorget)
        rad = K._smooth_ring(rad, 2)
        if z == crown_z:
            crown = rad
        rings.append(None if z > crown_z else [axis + V(0, 0, z) + d * r for d, r in zip(dirs, rad)])
    for i, z in enumerate(levels):
        if rings[i] is None:
            k = max(0.10, math.sqrt(max(0.0, 1 - ((z - crown_z) / (top_z - crown_z)) ** 2)))
            ring = []
            for t, d, r in zip(th_, dirs, crown):
                crest = 0.018 * abs(math.cos(t)) ** 24 * (1 - k)  # raised ridge front-to-back
                ring.append(axis + V(0, -0.02 * (1 - k), z) + d * (r * k + crest))
            rings[i] = ring
    bm, _ = sumi.loft(rings, closed=True, cap_start=True)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        t = math.degrees(math.atan2(c.x, -(c.y - axis.y)))
        if abs(t) < 52 and 1.641 < c.z < 1.664:
            kill.append(f)  # eye slit
        elif 1.545 < c.z < 1.595 and 8 < abs(t) < 40 and int((abs(t) - 8) / 6) % 2 == 0:
            kill.append(f)  # breathing slots
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    obj = sumi.mesh_object("Knight_Helm", bm, col)
    obj = K._finish(obj, M["plate"], thickness=0.006)
    obj["rigid_bone"] = "Head"
    parts = [obj]
    for s in (1, -1):  # swept fins from the temples, like the reference
        parts.append(ak.horn(f"Knight_HelmFin_{'L' if s > 0 else 'R'}",
                             [V(0.088 * s, -0.04, 1.69), V(0.115 * s, 0.0, 1.725), V(0.13 * s, 0.06, 1.76),
                              V(0.135 * s, 0.13, 1.80)], 0.024, M["plate"], col, sides=6, rigid_bone="Head"))
    return parts


def cowl(col, fit):
    """Tattered dark cowl around the neck, falling over the chest and shoulders."""
    n = 48
    axis = V(0, 0.01, 0)
    th_ = [2 * math.pi * i / n for i in range(n)]
    dirs = [Vector((math.sin(t), -math.cos(t), 0)) for t in th_]

    def hem(t):
        side = abs(math.sin(t))
        return 1.20 + 0.15 * side ** 1.3 + 0.03 * math.sin(7 * t + 1.0)
    rings, prev = [], None
    steps = 12
    for s_i in range(steps + 1):
        k = s_i / steps
        zs = [1.50 + (hem(t) - 1.50) * k for t in th_]
        rad = []
        for i, (t, d) in enumerate(zip(th_, dirs)):
            r = (fit.outermost(axis + V(0, 0, zs[i]), d, 0.5) or 0.1) + 0.055 + 0.02 * k
            if prev:
                r = max(r, prev[i] + 0.003)
            rad.append(r)
        rad = K._smooth_ring(rad, 2)
        rad = [r + 0.012 * k * math.sin(11 * t + 2.0) for r, t in zip(rad, th_)]
        prev = rad
        rings.append([axis + V(0, 0, z) + d * r for d, r, z in zip(dirs, rad, zs)])
    for i, p in enumerate(rings[-1]):  # deep tatters
        p.z -= (0.05 + 0.03 * math.sin(i * 2.3)) * (i % 3 == 0)
    bm, _ = sumi.loft(rings, closed=True, u_scale=4.0, v_scale=3.0)
    obj = sumi.mesh_object("Knight_Cowl", bm, col)
    return K._finish(obj, M["cloth"], thickness=0.005)


def limbs(col, fit):
    out = []
    for side in ("L", "R"):
        s = 1 if side == "L" else -1
        P = lambda k: J[f"{side}_{k}"]  # noqa: E731
        out.append(K._limb_wrap(f"Knight_Rerebrace_{side}", P("shoulder").lerp(P("elbow"), 0.30),
                                P("shoulder").lerp(P("elbow"), 0.88), fit, M["plate"], col, gap=0.018,
                                ridge=0.004, count=24, rings_n=10, pitch=0.06))
        out.append(K._limb_wrap(f"Knight_Vambrace_{side}", P("elbow").lerp(P("wrist"), 0.12),
                                P("wrist").lerp(P("palm"), 0.2), fit, M["plate"], col, gap=0.016, ridge=0.0,
                                count=24, rings_n=12, flare=0.02))
        out.append(K._limb_wrap(f"Knight_Cuisse_{side}", P("hip").lerp(P("knee"), 0.22),
                                P("hip").lerp(P("knee"), 0.92), fit, M["plate"], col, gap=0.022, ridge=0.005,
                                count=28, rings_n=14, pitch=0.07))
        out.append(K._limb_wrap(f"Knight_Greave_{side}", P("ankle") + V(0, -0.005, 0.03),
                                P("knee").lerp(P("ankle"), 0.08), fit, M["plate"], col, gap=0.02, ridge=0.0,
                                count=28, rings_n=16, flare=0.01))
        # couter (elbow) and poleyn (knee) caps
        el = P("elbow")
        out.append(ak.dome(f"Knight_Couter_{side}", el + V(0.0, 0.04, 0.0), (0.1 * s, 1, 0.2), (0.05, 0.05, 0.04),
                           M["plate"], col, cut=-0.1))
        kn = P("knee")
        out.append(ak.dome(f"Knight_Poleyn_{side}", kn + V(0, -0.09, 0.01), (0, -1, 0.15), (0.075, 0.075, 0.05),
                           M["plate"], col, cut=-0.15, lames=2))
        # pauldron: the left one is the big layered shield of the reference
        big = 1.25 if side == "L" else 1.0
        sh = P("shoulder")
        for i in range(3):
            c = sh + V(0.03 * s, 0.0, 0.05 - 0.055 * i) * big
            out.append(ak.dome(f"Knight_Pauldron_{side}{i}", c, (0.6 * s, 0, 1), (0.105 * big - 0.006 * i,
                               0.115 * big - 0.006 * i, 0.055 * big), M["plate"], col, cut=0.0 + 0.12 * i))
    return out


def torso(col, fit):
    out = []
    out.append(ak.torso_shell(K, "Knight_Breastplate", fit, [1.45, 1.43, 1.39, 1.33, 1.26, 1.18, 1.10, 1.03, 0.99],
                              M["plate"], col, gap=0.045, keel=0.03))
    # faulds: stepped lames flaring over the hips
    out.append(ak.torso_shell(K, "Knight_Faulds", fit, [1.00, 0.97, 0.955, 0.925, 0.91, 0.88, 0.865, 0.835],
                              M["plate"], col, gap=0.07,
                              flare=lambda z: 0.012 * math.floor((1.0 - z) / 0.045) + 0.03 * (1.0 - z)))
    out.append(ak.torso_shell(K, "Knight_Belt", fit, [1.015, 0.985], M["leather"], col, gap=0.082, thick=0.012))
    # diagonal baldric from the left shoulder to the right hip, over the breastplate
    plate_fit = K.Fitter([out[0]])
    pts = []
    for k in range(18):
        t = k / 17
        p = V(0.16, -0.02, 1.43).lerp(V(-0.17, -0.03, 0.99), t)
        d = Vector((p.x * 0.3, -1, 0)).normalized()
        r = plate_fit.outermost(V(p.x * 0.3, 0.006, p.z), d, 0.4) or 0.16
        pts.append(V(p.x * 0.3, 0.006, p.z) + d * (r + 0.01) + V(p.x * 0.7, 0, 0))
    out.append(K.tube("Knight_Baldric", pts, 0.012, M["leather"], col))
    return out


def main():
    sumi.reset_scene()
    materials()
    ks.tie_chain = plume_chain
    ks.sash_chain = tabard_chain
    col = sumi.collection("Knight")
    body = K.build_body(col, girth=1.12, torso=1.08, name="Knight_Body")
    body_ref = body.copy()
    body_ref.data = body.data.copy()
    body_ref.name = body_ref.data.name = "Knight_BodyRef"
    sumi.link(body_ref, sumi.collection("Knight_Reference"))
    ak.region_materials(body, {"under": M["under"], "hand": M["plate"], "foot": M["plate"]},
                        lambda p: ak.hands_and_feet(p) or "under")
    ak.cull_faces(body, lambda c: (c.z > 1.46 and abs(c.x) < 0.08) or (1.02 < c.z < 1.42 and abs(c.x) < 0.17))
    head, eyes = K.build_head(col)
    for e in eyes:  # the eyes are the red glints behind the visor
        e.scale = (1.3, 1.0, 0.7)
        sumi.apply_transforms(e)
    K.FIT_TARGET = body_ref
    fit = K.Fitter([body_ref, head])
    garments = []
    garments += torso(col, fit)
    garments += limbs(col, fit)
    garments += helmet(col, fit)
    garments.append(cowl(col, fit))
    garments += ak.strips(K, "Knight_Plume", [("TieL", plume_chain(1, 6, 0.85)), ("TieR", plume_chain(-1, 5, 0.65))],
                          [0.07, 0.06], M["cloth"], col, "Head", seed=3, twist=0.6)
    garments += ak.strips(K, "Knight_Tabard", [("SashL", tabard_chain(1, 5, 0.62)), ("SashR", tabard_chain(-1, 4, 0.48))],
                          [0.13, 0.11], M["cloth"], col, "Hips", seed=8)
    garments += ak.strips(K, "Knight_Cape", [(n, p) for n, p, _ in CAPE], [0.24, 0.26, 0.22], M["cloth"], col,
                          "UpperChest", taper=0.85, seed=21, twist=0.15)
    body_ref.hide_render = True
    for o in [body, head, *eyes, *garments]:
        sumi.ensure_uv(o)
        sumi.bake_cavity_to_color(o)
    arm = K.build_armature(col, extra_chains=CAPE, name="Knight_Rig")
    K.rig_character(arm, body, body_ref, head, eyes, garments, prefix="Knight")
    bpy.data.objects.remove(head)  # sealed inside the helm; only the red eye glints remain
    K.build_actions(arm)
    meshes = [o for o in col.objects if o.type == "MESH"]
    sumi.log("knight meshes", len(meshes), "tris", sum(sumi.tri_count(o) for o in meshes))
    if "--preview" in ARGS:
        ak.preview(K, "knight")
    sumi.save_blend(OUT)


main()
