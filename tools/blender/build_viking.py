"""Build the Viking berserker (docs/reference/characters/viking.jpeg).

    blender -b --factory-startup --python tools/blender/build_viking.py [-- --preview]

Output: assets_src/characters/viking/viking.blend
Shares Kage's skeleton and animation set. Tie chains = hair braids,
Sash chains = rear kilt flaps, Cape chains = the red cape.

Art-bible note: the red cape is the one sanctioned large vermilion mass in the
roster (it is this character's identity in the reference). It uses a darker,
ink-loaded shu so it reads as stained cloth, not a colour field.
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
OUT = sumi.repo_path("assets_src", "characters", "viking", "viking.blend")
J = ks.joints()
M = {}


def materials():
    M["skin"] = sumi.material("M_Viking_Skin", 0.66)
    M["leather"] = sumi.material("M_Viking_Leather", 0.24)
    M["metal"] = sumi.material("M_Viking_Metal", 0.50, roughness=0.4, metallic=0.6)
    M["helm"] = sumi.material("M_Viking_Helm", 0.14)
    M["bone"] = sumi.material("M_Viking_Horn", 0.84)
    M["fur"] = sumi.material("M_Viking_Fur", 0.88)
    M["hair"] = sumi.material("M_Viking_Hair", 0.30)
    M["cape"] = sumi.material("M_Viking_Cape", rgb=(0.42, 0.075, 0.06))
    M["eye"] = sumi.material("M_Kage_Eye", 0.03)
    K.MAT.update(eye=M["eye"], skin=M["skin"])


def braid_chain(side, segments, length):
    return ak.chain(V(0.05 * side, 0.10, 1.62), (0.15 * side, 0.45, -0.9), (0.05 * side, 0.15, -1), segments,
                    length * 0.62)


def flap_chain(side, segments, length):
    return ak.chain(V(0.075 * side, 0.20, 0.975), (0.02 * side, 0.10, -1), (0.02 * side, 0.20, -1), segments, length)


CAPE = [(f"Cape{n}", ak.chain(V(x, 0.17, 1.43), (x * 0.6, 0.35, -1), (x * 1.4, 0.55, -1), 6, L), "UpperChest")
        for n, x, L in (("L", 0.15, 1.12), ("M", 0.0, 1.2), ("R", -0.15, 1.0))]


def muscles(body):
    """Sculpt a heavy build into the skin-modifier body: pecs, abs, delts, biceps, calves."""
    me = body.data
    me.calc_normals_split() if hasattr(me, "calc_normals_split") else None
    bumps = [  # (centre, radius, height)
        (V(0.075, -0.115, 1.30), 0.075, 0.022), (V(-0.075, -0.115, 1.30), 0.075, 0.022),
        (V(0.21, 0.0, 1.40), 0.07, 0.02), (V(-0.21, 0.0, 1.40), 0.07, 0.02),
        (V(0.10, 0.09, 1.30), 0.09, 0.02), (V(-0.10, 0.09, 1.30), 0.09, 0.02),     # lats / traps
        (V(0.0, 0.07, 1.46), 0.09, 0.025),
    ]
    for z in (1.17, 1.11, 1.05):
        for x in (0.032, -0.032):
            bumps.append((V(x, -0.118, z), 0.03, 0.009))
    for side in ("L", "R"):
        P = lambda k: J[f"{side}_{k}"]  # noqa: E731
        bumps.append((P("shoulder").lerp(P("elbow"), 0.5) + V(0, -0.02, 0.02), 0.06, 0.016))
        bumps.append((P("elbow").lerp(P("wrist"), 0.3), 0.05, 0.010))
        bumps.append((P("knee").lerp(P("ankle"), 0.3) + V(0, 0.03, 0), 0.06, 0.012))
        bumps.append((P("hip").lerp(P("knee"), 0.4) + V(0, -0.04, 0), 0.08, 0.014))
    for v in me.vertices:
        off = 0.0
        for c, r, h in bumps:
            d2 = (v.co - c).length_squared / (r * r)
            if d2 < 4:
                off += h * math.exp(-d2)
        v.co += v.normal * off


def tattoos(objs):
    """Knotwork bands drawn as ink into the vertex-colour cavity channel (R)."""
    for o in objs:
        ca = o.data.color_attributes.get("Color")
        if not ca:
            continue
        for i, v in enumerate(o.data.vertices):
            p = v.co
            ink = 0.0
            for side in ("L", "R"):
                P = lambda k: J[f"{side}_{k}"]  # noqa: E731
                for a, b, n_bands in ((P("shoulder"), P("elbow"), 3), (P("elbow"), P("wrist"), 2),
                                      (P("hip"), P("knee"), 3)):
                    ab = b - a
                    t = (p - a).dot(ab) / ab.length_squared
                    if not 0.2 < t < 0.85 or (p - (a + ab * t)).length > 0.12:
                        continue
                    ang = math.atan2(p.y - (a + ab * t).y, p.x - (a + ab * t).x)
                    u = t * n_bands * 2.0
                    weave = abs(((u + 0.18 * math.sin(ang * 4)) % 1.0) - 0.5)
                    ink = max(ink, 1.0 if weave < 0.09 else 0.0)
            # chest: a single sweeping mark over the heart
            if -0.2 < p.y < 0 and 1.22 < p.z < 1.38 and 0.04 < p.x < 0.16:
                ink = max(ink, 1.0 if abs(math.sin((p.x * 40 + p.z * 25))) < 0.22 else 0.0)
            if ink:
                c = list(ca.data[i].color)
                c[0] = min(c[0], 0.08)
                ca.data[i].color = c


def helm(col, fit):
    parts = []
    n = 40
    axis = V(0, 0.004, 0)
    rings = []
    levels = [1.80, 1.795, 1.785, 1.77, 1.75, 1.725, 1.70, 1.675, 1.655]
    crown = None
    for z in levels:
        zs = min(z, 1.725)
        rad = []
        for i in range(n):
            t = 2 * math.pi * i / n
            d = Vector((math.sin(t), -math.cos(t), 0))
            rad.append((fit.outermost(axis + V(0, 0, zs), d, 0.3) or 0.08) + 0.026)
        rad = K._smooth_ring(rad, 2)
        if z <= 1.725:
            crown = crown or rad
        rings.append((z, rad))
    out = []
    for z, rad in rings:
        k = 1.0 if z <= 1.725 else max(0.12, math.sqrt(max(0, 1 - ((z - 1.725) / 0.075) ** 2)))
        base = crown if z > 1.725 else rad
        out.append([axis + V(0, 0, z) + Vector((math.sin(2 * math.pi * i / n), -math.cos(2 * math.pi * i / n), 0))
                    * (r * k + (0.004 if z in (1.70, 1.675) else 0.0)) for i, r in enumerate(base)])
    bm, _ = sumi.loft(out, closed=True, cap_start=True)
    h = K._finish(sumi.mesh_object("Viking_Helm", bm, col), M["helm"], thickness=0.005)
    h["rigid_bone"] = "Head"
    parts.append(h)
    # brow band + spectacle guard + nasal
    for s in (1, -1):
        e = J["L_eye" if s > 0 else "R_eye"] + V(0, -0.028, 0.0)
        ring = [e + Vector((math.cos(a) * 0.025, -0.006 * math.sin(a) ** 2, math.sin(a) * 0.019)) for a in
                [2 * math.pi * i / 14 for i in range(15)]]
        parts.append(ak.horn(f"Viking_Spectacle_{'LR'[s < 0]}", ring, 0.0055, M["metal"], col, sides=6,
                             r1=0.005, rigid_bone="Head"))
    parts.append(ak.horn("Viking_Nasal", [V(0, -0.118, 1.67), V(0, -0.122, 1.62), V(0, -0.118, 1.58)], 0.009,
                         M["metal"], col, sides=6, r1=0.006, rigid_bone="Head"))
    for s in (1, -1):  # great horns
        parts.append(ak.horn(f"Viking_Horn_{'LR'[s < 0]}", [V(0.085 * s, -0.005, 1.74), V(0.15 * s, -0.01, 1.80),
                                                             V(0.19 * s, 0.0, 1.92), V(0.18 * s, 0.03, 2.04)],
                             0.032, M["bone"], col, sides=10, rigid_bone="Head", ridges=0.04))
    return parts


def fur_mantle(col, fit):
    """Shaggy pale fur over the shoulders: a lofted collar with clumped, spiky hems."""
    n = 64
    axis = V(0, 0.02, 0)
    th_ = [2 * math.pi * i / n for i in range(n)]
    dirs = [Vector((math.sin(t), -math.cos(t), 0)) for t in th_]
    rings, prev = [], None
    for s_i in range(9):
        k = s_i / 8
        zs = [1.53 - (0.15 + 0.08 * max(0, math.cos(t)) + 0.05 * max(0, -math.cos(t))) * k for t in th_]
        rad = []
        for i, (t, d) in enumerate(zip(th_, dirs)):
            r = (fit.outermost(axis + V(0, 0, zs[i]), d, 0.6) or 0.12) + 0.035 + 0.03 * k
            if prev:
                r = max(r, prev[i] + 0.006)
            rad.append(r)
        rad = K._smooth_ring(rad, 2)
        prev = rad
        rings.append([axis + V(0, 0, z) + d * r for d, r, z in zip(dirs, rad, zs)])
    # clumps: alternate long pointed locks along the hem and a ruff at the top
    for i, p in enumerate(rings[-1]):
        lock = (0.08 + 0.05 * math.sin(i * 1.9)) if i % 2 == 0 else 0.0
        p.z -= lock
        p += (p - V(axis.x, axis.y, p.z)).normalized() * lock * 0.6
    for i, p in enumerate(rings[0]):
        if i % 2 == 0:
            p.z += 0.035 + 0.02 * math.sin(i * 2.7)
    bm, _ = sumi.loft(rings, closed=True, u_scale=6.0, v_scale=2.0)
    obj = sumi.mesh_object("Viking_Fur", bm, col)
    return K._finish(obj, M["fur"], thickness=0.02)


def limbs(col, fit):
    out = []
    for side in ("L", "R"):
        P = lambda k: J[f"{side}_{k}"]  # noqa: E731
        out.append(K._limb_wrap(f"Viking_Bracer_{side}", P("elbow").lerp(P("wrist"), 0.35),
                                P("wrist").lerp(P("palm"), 0.15), fit, M["leather"], col, gap=0.008, ridge=0.006,
                                count=22, rings_n=10, pitch=0.035))
        out.append(K._limb_wrap(f"Viking_ArmRing_{side}", P("shoulder").lerp(P("elbow"), 0.62),
                                P("shoulder").lerp(P("elbow"), 0.70), fit, M["metal"], col, gap=0.006, ridge=0.0,
                                count=22, rings_n=2))
        out.append(K._limb_wrap(f"Viking_Boot_{side}", P("ankle") + V(0, -0.004, 0.012),
                                P("knee").lerp(P("ankle"), 0.35), fit, M["leather"], col, gap=0.012, ridge=0.004,
                                count=26, rings_n=14, pitch=0.05))
        cuff = P("knee").lerp(P("ankle"), 0.35)
        out.append(ak.dome(f"Viking_BootFur_{side}", cuff + V(0, 0.0, -0.03), (0, 0, 1), (0.09, 0.09, 0.07),
                           M["fur"], col, cut=-0.2, segs=(16, 6),
                           flat=lambda c: c * (1.0 + 0.25 * (abs(math.sin(math.atan2(c.y, c.x) * 7)) ** 3))))
    return out


def torso(col, fit):
    out = []
    out.append(ak.torso_shell(K, "Viking_Belt", fit, [1.065, 1.045, 0.995, 0.975], M["leather"], col, gap=0.018,
                              thick=0.01))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.075, 0.025, 0.085), verts=bm.verts)
    bmesh.ops.translate(bm, vec=V(0.0, -0.155, 1.02), verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    buckle = sumi.mesh_object("Viking_Buckle", bm, col)
    buckle.data.materials.append(M["metal"])
    buckle["rigid_bone"] = "Hips"
    out.append(buckle)
    kilt = ak.torso_shell(K, "Viking_Kilt", fit, [0.99, 0.95, 0.90, 0.85, 0.80, 0.76], M["leather"], col,
                          gap=0.02, flare=lambda z: 0.10 * (0.99 - z) + 0.01 * math.sin(z * 200), thick=0.006)
    ak.cull_faces(kilt, lambda c: abs(c.x) < 0.07 and c.z < 0.93 and c.y < 0)  # split front, walking room
    out.append(kilt)
    # front loin panel
    out.append(K.ribbon("Viking_LoinFront", [V(0, -0.16, 0.98), V(0, -0.175, 0.80), V(0, -0.17, 0.60)], 0.15, 0.8,
                        M["leather"], col, seed=5))
    # shoulder strap across the chest
    pts = []
    for k in range(18):
        t = k / 17
        p = V(0.15, -0.0, 1.47).lerp(V(-0.17, 0.0, 1.03), t)
        d = Vector((0, -1, 0))
        r = fit.outward(V(p.x, 0.01, p.z), d, 0.35) or 0.13
        pts.append(V(p.x, 0.01, p.z) + d * (r + 0.012))
    out.append(K.tube("Viking_Strap", pts, 0.013, M["leather"], col))
    return out


def braids(col):
    out = []
    for name, spec in (("TieL", dict(side=1, segments=6, length=0.92)), ("TieR", dict(side=-1, segments=5, length=0.74))):
        pts = braid_chain(**spec)
        b = K.tube(f"Viking_Braid_{name}", sumi.catmull(pts, 4), 0.016, M["hair"], col)
        for v in b.data.vertices:  # plaited bumps
            v.co.x += 0.004 * math.sin(v.co.z * 140)
        b["chain_prefix"] = name
        b["chain_points"] = [list(p) for p in pts]
        b["chain_root"] = "Head"
        out.append(b)
    # beard below the mask, two plaits
    for s in (1, -1):
        bd = K.tube(f"Viking_Beard_{'LR'[s < 0]}", sumi.catmull([V(0.025 * s, -0.10, 1.57), V(0.03 * s, -0.125, 1.50),
                                                                 V(0.02 * s, -0.13, 1.40)], 5), 0.017, M["hair"], col)
        bd["rigid_bone"] = "Head"
        out.append(bd)
    return out


def main():
    sumi.reset_scene()
    materials()
    ks.tie_chain = braid_chain
    ks.sash_chain = flap_chain
    col = sumi.collection("Viking")
    body = K.build_body(col, girth=1.30, torso=1.18, name="Viking_Body")
    muscles(body)
    body_ref = body.copy()
    body_ref.data = body.data.copy()
    body_ref.name = body_ref.data.name = "Viking_BodyRef"
    sumi.link(body_ref, sumi.collection("Viking_Reference"))
    ak.region_materials(body, {"skin": M["skin"], "foot": M["leather"]},
                        lambda p: "foot" if ak.hands_and_feet(p) == "foot" else "skin")
    ak.cull_faces(body, lambda c: 0.80 < c.z < 0.99 and abs(c.x) < 0.2)  # inside the kilt
    head, eyes = K.build_head(col)
    K.FIT_TARGET = body_ref
    fit = K.Fitter([body_ref, head])
    garments = []
    garments += torso(col, fit)
    garments += limbs(col, fit)
    garments += helm(col, fit)
    garments.append(fur_mantle(col, fit))
    garments += braids(col)
    garments += ak.strips(K, "Viking_Flap", [("SashL", flap_chain(1, 5, 0.50)), ("SashR", flap_chain(-1, 4, 0.42))],
                          [0.14, 0.12], M["leather"], col, "Hips", seed=4, twist=0.05)
    garments += ak.strips(K, "Viking_Cape", [(n, p) for n, p, _ in CAPE], [0.30, 0.32, 0.28], M["cape"], col,
                          "UpperChest", taper=0.7, seed=31, twist=0.25)
    body_ref.hide_render = True
    for o in [body, head, *eyes, *garments]:
        sumi.ensure_uv(o)
        sumi.bake_cavity_to_color(o)
    tattoos([body])
    arm = K.build_armature(col, extra_chains=CAPE, name="Viking_Rig")
    K.rig_character(arm, body, body_ref, head, eyes, garments, prefix="Viking")
    K.build_actions(arm)
    meshes = [o for o in col.objects if o.type == "MESH"]
    sumi.log("viking meshes", len(meshes), "tris", sum(sumi.tri_count(o) for o in meshes))
    if "--preview" in ARGS:
        ak.preview(K, "viking")
    sumi.save_blend(OUT)


main()
