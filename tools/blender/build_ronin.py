"""Build Mugai, the Straw Ronin (docs/reference/characters/outlaw.jpeg).

    blender -b --factory-startup --python tools/blender/build_ronin.py [-- --preview]

Output: assets_src/characters/ronin/ronin.blend
Shares Kage's skeleton, IK/FK control rig and every clip. Chains:
  Tie   -> long unkempt hair falling from under the hat
  Sash  -> obi tails
  Cape  -> the mino (straw rain cape) hanging down the back

Design: a wanderer hidden under a ragged kasa whose fringe hides the eyes,
a straw mino over a black kimono and hakama, forearms and shins bound in
bandage, bare hands, waraji sandals. The katana rides at the hip.
Ink translation: straw and bandage are the pale "kinari" tones, cloth is sumi,
hair is a mid warm grey. No red on the figure; the vermilion stays for the
seal and the blood.
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
OUT = sumi.repo_path("assets_src", "characters", "ronin", "ronin.blend")
J = ks.joints()
M = {}
RNG = sumi.seeded(23)
HEAD_TOP = J["head_top"]


def materials():
    M["skin"] = sumi.material("M_Ronin_Skin", 0.62)
    M["robe"] = sumi.material("M_Ronin_Robe", 0.085)
    M["bandage"] = sumi.material("M_Ronin_Bandage", 0.84)
    M["straw"] = sumi.material("M_Ronin_Straw", rgb=(0.80, 0.75, 0.62))
    M["straw_dark"] = sumi.material("M_Ronin_StrawShade", rgb=(0.56, 0.50, 0.38))
    M["hair"] = sumi.material("M_Ronin_Hair", rgb=(0.46, 0.40, 0.31))
    M["obi"] = sumi.material("M_Ronin_Obi", 0.40)
    M["sandal"] = sumi.material("M_Ronin_Sandal", 0.30)
    M["eye"] = sumi.material("M_Kage_Eye", 0.03)
    # Kage's garment builders read K.MAT: point them at the ronin's palette
    K.MAT.update(cloth=M["robe"], wrap=M["bandage"], glove=M["bandage"], tabi=M["sandal"], sash=M["obi"],
                 skin=M["skin"], eye=M["eye"], hood=M["robe"], red=M["obi"])


# ------------------------------------------------------------------ chains
def hair_chain(side, segments, length):
    """Long hair falls from under the back of the hat, down past the shoulder blades."""
    return ak.chain(V(0.05 * side, 0.11, 1.60), (0.12 * side, 0.55, -0.85), (0.06 * side, 0.18, -1), segments,
                    length * 0.80)


def obi_chain(side, segments, length):
    return ak.chain(V(0.07 * side, 0.15, 1.02), (0.03 * side, 0.15, -1), (0.02 * side, 0.25, -1), segments,
                    length * 0.75)


# mino: three chains over the back, from the shoulder line to the back of the knees
CAPE = [(f"Cape{n}", ak.chain(V(x, 0.16, 1.40), (x * 0.9, 0.55, -1), (x * 1.3, 0.30, -1), 6, 0.86), "UpperChest")
        for n, x in ((1, 0.15), (2, 0.0), (3, -0.15))]


# ------------------------------------------------------------------ the kasa
def kasa(col):
    """Conical woven straw hat with concentric weave ridges and a ragged fringe."""
    apex = HEAD_TOP + V(0, 0.005, 0.035)
    brim_z = 1.60
    R = 0.37
    rings = []
    n, steps = 40, 12
    for k in range(steps + 1):
        t = k / steps
        r = R * t
        z = apex.z + (brim_z - apex.z) * (t ** 1.15)   # slightly convex, like woven bamboo
        ridge = 0.004 * (1 if k % 2 else -0.4) * t       # woven bands
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            wob = 1 + 0.015 * math.sin(5 * a + k)
            # tilt forward: the brim dips over the eyes like the reference
            dz = -0.045 * t * max(0.0, -math.cos(a + math.pi / 2)) + 0.02 * t * math.sin(a + math.pi / 2) * 0
            ring.append(Vector((apex.x + math.cos(a) * r * wob, apex.y + math.sin(a) * r * wob,
                                z + ridge + dz - 0.035 * t * max(0.0, -math.sin(a)))))
        rings.append(ring)
    rings[0] = [apex.copy() for _ in range(n)]
    bm, _ = sumi.loft(rings, closed=True, u_scale=6.0, v_scale=4.0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    hat = sumi.mesh_object("Ronin_Kasa", bm, col)
    hat.data.materials.append(M["straw"])
    sumi.add_modifier(hat, "SOLIDIFY", thickness=0.008, offset=-1.0)
    sumi.apply_modifiers(hat)
    sumi.shade_smooth(hat, angle_deg=40)
    hat["rigid_bone"] = "Head"
    fringe = []
    edge = rings[-1]
    for i in range(108):
        a = 2 * math.pi * (i + RNG.random() * 0.6) / 108
        base = Vector((apex.x + math.cos(a) * R * 0.97, apex.y + math.sin(a) * R * 0.97, 0))
        base.z = brim_z - 0.035 * max(0.0, -math.sin(a)) + 0.004
        out = Vector((math.cos(a), math.sin(a), 0))
        L = 0.07 + 0.17 * RNG.random() ** 1.6
        # strands splay out and droop; longer and messier at the back
        L *= 1.0 + 0.4 * max(0.0, math.sin(a))
        d = (out * (0.55 + 0.4 * RNG.random()) + Vector((0, 0, -1))).normalized()
        pts = [base, base + d * L * 0.5 + out * 0.01, base + d * L + Vector((0, 0, -0.03 * RNG.random()))]
        fringe.append(_strand(f"Ronin_KasaFringe_{i}", pts, 0.006 + 0.006 * RNG.random(), col,
                              M["straw"] if i % 3 else M["straw_dark"]))
    fr = sumi.join(fringe, "Ronin_KasaFringe")
    fr["rigid_bone"] = "Head"
    return [hat, fr]


def _strand(name, pts, w, col, mat):
    """Flat straw blade along a short polyline (a thin tapered card, double sided)."""
    pts = sumi.catmull(pts, 2)
    bm = bmesh.new()
    prev = None
    for k, p in enumerate(pts):
        t = k / (len(pts) - 1)
        tg = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        side = tg.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side = side.normalized() * w * (1 - 0.85 * t)
        a, b = bm.verts.new(p - side), bm.verts.new(p + side)
        if prev:
            bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)
    bm.loops.layers.uv.new("UVMap")
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.add_modifier(obj, "SOLIDIFY", thickness=0.0015, offset=0.0)
    sumi.apply_modifiers(obj)
    return obj


# ------------------------------------------------------------------ the mino
def mino(col, fit):
    """Straw rain cape: a stiff shoulder mantle and long straw riding three chains."""
    out = []
    def flare(z):
        return 0.012 + (1.47 - z) * 0.22
    mantle = ak.torso_shell(K, "Ronin_MinoMantle", fit, [1.50, 1.47, 1.43, 1.38, 1.32, 1.26], M["straw"], col,
                            gap=0.035, flare=flare, thick=0.010)
    out.append(mantle)
    # ragged strands all around the mantle hem (rigid on the chest)
    hem = []
    for i in range(70):
        a = 2 * math.pi * (i + RNG.random() * 0.7) / 70
        d = Vector((math.sin(a), -math.cos(a), 0))
        r = (fit.outward(V(0, 0.006, 1.27), d, 0.35) or 0.16) + 0.035 + flare(1.26)
        base = V(0, 0.006, 1.27) + d * r
        L = 0.08 + 0.12 * RNG.random()
        pts = [base, base + d * 0.02 + Vector((0, 0, -L * 0.6)), base + d * 0.035 + Vector((0, 0, -L))]
        hem.append(_strand(f"Ronin_MinoHem_{i}", pts, 0.008, col, M["straw"] if i % 4 else M["straw_dark"]))
    h = sumi.join(hem, "Ronin_MinoHem")
    h["rigid_bone"] = "UpperChest"
    out.append(h)
    # back curtain: many narrow tattered ribbons per chain, fanned across its width
    for cname, pts, _ in CAPE:
        ribbons = []
        for j in range(7):
            off = Vector(((j - 3) * 0.035, 0.005 * (j % 2), 0))
            p = [q + off * (1 + 0.6 * k / len(pts)) for k, q in enumerate(pts)]
            p[-1] = p[-1] + Vector((0, 0, -0.08 * RNG.random()))
            ribbons.append(K.ribbon(f"Ronin_Mino_{cname}_{j}", p, 0.05, 0.55,
                                    M["straw"] if j % 3 else M["straw_dark"], col, twist=0.1 * (j - 3),
                                    seed=40 + j + 7 * int(cname[-1]), samples=18))
        r = sumi.join(ribbons, f"Ronin_Mino_{cname}")
        r["chain_prefix"] = cname
        r["chain_points"] = [list(q) for q in pts]
        r["chain_root"] = "UpperChest"
        r["chain_root_blend"] = 0.5
        out.append(r)
    return out


# ------------------------------------------------------------------ clothes
def kimono(col, fit):
    """Black kimono top crossing left over right, wide sleeves hanging off the arms."""
    out = [ak.torso_shell(K, "Ronin_Kimono", fit, [1.47, 1.44, 1.38, 1.30, 1.20, 1.10, 1.02, 0.96], M["robe"], col,
                          gap=0.016, flare=lambda z: 0.012 * max(0.0, 1.05 - z) * 10, thick=0.006)]
    for side in ("L", "R"):
        s = 1 if side == "L" else -1
        sh, el = J[f"{side}_shoulder"], J[f"{side}_elbow"]
        wr = J[f"{side}_wrist"]
        a, b = sh + V(-0.02 * s, 0, 0), el.lerp(wr, 0.25)
        rings = []
        for k in range(9):
            t = k / 8
            c = a.lerp(b, t)
            axis = (b - a).normalized()
            u = axis.cross(Vector((0, 1, 0))).normalized()
            w = axis.cross(u).normalized()
            r = 0.075 + 0.04 * t
            sag = Vector((0, 0, -0.05 * t * t))       # the sleeve bag hangs below the arm
            rings.append([c + sag * (1 + max(0.0, -math.sin(2 * math.pi * i / 16))) + (u * math.cos(2 * math.pi * i / 16)
                          + w * math.sin(2 * math.pi * i / 16)) * r for i in range(16)])
        bm, _ = sumi.loft(rings, closed=True, u_scale=2.0, v_scale=2.0)
        obj = sumi.mesh_object(f"Ronin_Sleeve_{side}", bm, col)
        out.append(K._finish(obj, M["robe"], thickness=0.004))
    return out


def waraji(col):
    out = []
    for side in ("L", "R"):
        heel, ball, toe = J[f"{side}_heel"], J[f"{side}_ball"], J[f"{side}_toe"]
        c = (heel + toe) * 0.5
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.085, (heel - toe).length + 0.05, 0.012), verts=bm.verts)
        bmesh.ops.translate(bm, vec=V(c.x, c.y, 0.006), verts=bm.verts)
        bm.loops.layers.uv.new("UVMap")
        sole = sumi.mesh_object(f"Ronin_Waraji_{side}", bm, col)
        sole.data.materials.append(M["straw_dark"])
        sole["rigid_bone"] = f"{K.SIDE_NAME[side]}Foot"
        out.append(sole)
        # straps from the toe over the instep to the ankle
        an = J[f"{side}_ankle"]
        for k, (x0, x1) in enumerate(((-0.04, 0.0), (0.04, 0.0))):
            pts = [V(ball.x + x0, ball.y - 0.02, 0.012), V(ball.x + x0 * 0.6, (ball.y + an.y) / 2, 0.07),
                   V(an.x + x1, an.y, an.z + 0.01)]
            t = K.tube(f"Ronin_WarajiStrap_{side}{k}", sumi.catmull(pts, 4), 0.005, M["sandal"], col, sides=5)
            t["rigid_bone"] = f"{K.SIDE_NAME[side]}Foot"
            out.append(t)
    return out


def hair(col):
    """Long locks on the Tie chains plus a short mass under the hat, rigid to the head."""
    out = []
    for side, spec in ((1, ks.TIE_L), (-1, ks.TIE_R)):
        pts = hair_chain(side, spec["segments"], spec["length"])
        locks = []
        for j in range(6):
            off = Vector((0.03 * (j - 2.5) * side, 0.01 * (j % 2), 0.0))
            p = [q + off * (1 + 0.8 * k / len(pts)) for k, q in enumerate(pts)]
            locks.append(K.ribbon(f"Ronin_Hair_{side}_{j}", p, 0.035, 0.4, M["hair"], col, twist=0.25 * (j - 2.5),
                                  seed=70 + j + (side > 0) * 10, samples=18))
        r = sumi.join(locks, f"Ronin_Hair_{'L' if side > 0 else 'R'}")
        r["chain_prefix"] = "TieL" if side > 0 else "TieR"
        r["chain_points"] = [list(q) for q in pts]
        r["chain_root"] = "Head"
        r["chain_root_blend"] = 0.5
        out.append(r)
    mass = ak.dome("Ronin_HairMass", HEAD_TOP + V(0, 0.03, -0.11), (0, 0.4, 1), (0.105, 0.11, 0.10), M["hair"], col,
                   cut=-0.25, rigid_bone="Head")
    out.append(mass)
    return out


# ------------------------------------------------------------------ build
def main():
    sumi.reset_scene()
    materials()
    ks.tie_chain = hair_chain
    ks.sash_chain = obi_chain
    col = sumi.collection("Ronin")
    body = K.build_body(col, girth=1.06, torso=1.04, name="Ronin_Body")
    body_ref = body.copy()
    body_ref.data = body.data.copy()
    body_ref.name = body_ref.data.name = "Ronin_BodyRef"
    sumi.link(body_ref, sumi.collection("Ronin_Reference"))
    # bare hands, sandalled feet; everything between is clothed or bandaged
    ak.region_materials(body, {"skin": M["skin"], "foot": M["skin"]},
                        lambda p: "foot" if ak.hands_and_feet(p) == "foot" else "skin")
    ak.cull_faces(body, lambda c: 0.16 < c.z < 1.44 and abs(c.x) < 0.25)  # under kimono and hakama
    head, eyes = K.build_head(col)
    K.FIT_TARGET = body_ref
    fit = K.Fitter([body_ref, head])
    garments = []
    garments += kimono(col, fit)
    garments += K.build_hakama(col, fit)
    garments += K.build_wraps(col, fit)          # shin wraps, forearm bandage, hand wraps
    garments += K.build_obi(col, fit)
    garments += mino(col, fit)
    garments += kasa(col)
    garments += hair(col)
    garments += waraji(col)
    for g in garments:
        g.name = g.name.replace("Kage_", "Ronin_")
    body_ref.hide_render = True
    for o in [body, head, *eyes, *garments]:
        sumi.ensure_uv(o)
        sumi.bake_cavity_to_color(o)
    arm = K.build_armature(col, extra_chains=CAPE, name="Ronin_Rig")
    K.rig_character(arm, body, body_ref, head, eyes, garments, prefix="Ronin")
    K.build_actions(arm)
    meshes = [o for o in col.objects if o.type == "MESH"]
    sumi.log("ronin meshes", len(meshes), "tris", sum(sumi.tri_count(o) for o in meshes))
    if "--preview" in ARGS:
        ak.preview(K, "ronin", actions=("Stance_Greatsword_Idle",))
    sumi.save_blend(OUT)


main()
