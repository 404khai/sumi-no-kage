"""Build Kage, the assassin: body, garments, rig, skin weights and rig-test actions.

    blender -b --factory-startup --python tools/blender/build_kage.py [-- --preview]

Output: assets_src/characters/kage/kage.blend
Everything is generated from code, so the design is reproducible and diffable.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

import kage_rig  # noqa: E402
import kage_skeleton as ks  # noqa: E402
import sumi  # noqa: E402
from kage_skeleton import V  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = sumi.repo_path("assets_src", "characters", "kage", "kage.blend")
J = ks.joints()
RNG = sumi.seeded(7)

MAT = {}


def make_materials():
    T = sumi.INK_TONES
    MAT["cloth"] = sumi.material("M_Kage_Cloth", 0.115)
    MAT["hood"] = sumi.material("M_Kage_Hood", 0.075)
    MAT["wrap"] = sumi.material("M_Kage_Wrap", 0.20)
    MAT["glove"] = sumi.material("M_Kage_Glove", 0.085)
    MAT["tabi"] = sumi.material("M_Kage_Tabi", 0.16)
    MAT["sash"] = sumi.material("M_Kage_Sash", 0.26)
    MAT["skin"] = sumi.material("M_Kage_Skin", 0.74)
    MAT["eye"] = sumi.material("M_Kage_Eye", T["sho"])
    MAT["red"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)


# ==========================================================================
# BODY — skin-modifier base mesh driven by the shared joint layout
# ==========================================================================
def build_body(col, girth=1.0, name="Kage_Body", torso=1.0):
    """girth scales limbs, torso additionally scales the trunk (for heavier builds)."""
    verts, edges, radii = [], [], []
    index = {}
    trunk = {"pelvis", "hips", "waist", "chest", "upper_chest", "yoke"}

    def vtx(key, p, r, k=1.34):
        # subdivision shrinks the skin hull; radii are authored as final sizes
        index[key] = len(verts)
        verts.append(Vector(p))
        r = r if isinstance(r, tuple) else (r, r)
        if r[0] < 0.02:
            k = 1.18 * girth ** 0.5
        else:
            k *= girth * (torso if key in trunk else 1.0)
        radii.append((r[0] * k, r[1] * k))
        return index[key]

    def edge(a, b):
        edges.append((index[a], index[b]))

    # torso chain
    vtx("pelvis", J["pelvis"], (0.128, 0.100))
    vtx("hips", J["hips"], (0.142, 0.106))
    vtx("waist", J["spine"], (0.124, 0.092))
    vtx("chest", J["chest"], (0.138, 0.100))
    vtx("upper_chest", J["upper_chest"], (0.150, 0.098))
    vtx("yoke", V(0, 0.010, 1.392), (0.118, 0.080))
    vtx("neck", V(0, 0.018, 1.470), (0.050, 0.054))
    vtx("neck_top", V(0, 0.010, 1.565), (0.046, 0.050))
    for a, b in (("pelvis", "hips"), ("hips", "waist"), ("waist", "chest"),
                 ("chest", "upper_chest"), ("upper_chest", "yoke"), ("yoke", "neck"),
                 ("neck", "neck_top")):
        edge(a, b)

    for side, s in (("L", 1), ("R", -1)):
        def P(k):
            return J[f"{side}_{k}"]
        g = lambda k: f"{side}_{k}"  # noqa: E731
        # arm
        vtx(g("clav"), V(0.105 * s, 0.012, 1.405), 0.060)
        vtx(g("shoulder"), P("shoulder"), 0.056)
        vtx(g("bicep"), P("shoulder").lerp(P("elbow"), 0.5), 0.045)
        vtx(g("elbow"), P("elbow"), 0.037)
        vtx(g("forearm"), P("elbow").lerp(P("wrist"), 0.35), 0.041)
        vtx(g("wrist"), P("wrist"), 0.026)
        vtx(g("palm"), P("palm"), (0.034, 0.016))
        edge("yoke", g("clav"))
        for a, b in (("clav", "shoulder"), ("shoulder", "bicep"), ("bicep", "elbow"),
                     ("elbow", "forearm"), ("forearm", "wrist"), ("wrist", "palm")):
            edge(g(a), g(b))
        for f, rads in (("Index", (0.0105, 0.0095, 0.0088, 0.0078)),
                        ("Middle", (0.0108, 0.0098, 0.0090, 0.0080)),
                        ("Ring", (0.0102, 0.0093, 0.0086, 0.0076)),
                        ("Little", (0.0090, 0.0082, 0.0076, 0.0068))):
            prev = g("palm")
            for i in range(4):
                key = g(f"{f}{i}")
                vtx(key, P(f"{f}{i}"), rads[i])
                edge(prev, key)
                prev = key
        prev = g("wrist")
        for i, r in enumerate((0.016, 0.0125, 0.0105, 0.0090)):
            key = g(f"Thumb{i}")
            vtx(key, P(f"Thumb{i}"), r)
            edge(prev if i else g("palm"), key)
            prev = key
        # leg
        vtx(g("hip"), P("hip"), 0.090)
        vtx(g("thigh"), P("hip").lerp(P("knee"), 0.45), 0.076)
        vtx(g("knee"), P("knee"), 0.053)
        vtx(g("calf"), P("knee").lerp(P("ankle"), 0.32) + V(0, 0.012, 0), 0.056)
        vtx(g("shin_low"), P("knee").lerp(P("ankle"), 0.75), 0.040)
        vtx(g("ankle"), P("ankle"), 0.036)
        vtx(g("heel"), P("heel"), 0.034)
        vtx(g("ball"), P("ball"), (0.042, 0.022))
        vtx(g("toe"), P("toe"), (0.032, 0.018))
        edge("pelvis", g("hip"))
        for a, b in (("hip", "thigh"), ("thigh", "knee"), ("knee", "calf"), ("calf", "shin_low"),
                     ("shin_low", "ankle"), ("ankle", "heel"), ("ankle", "ball"), ("ball", "toe")):
            edge(g(a), g(b))

    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    obj = bpy.data.objects.new(name, me)
    sumi.link(obj, col)
    skin = sumi.add_modifier(obj, "SKIN", branch_smoothing=0.6, use_smooth_shade=True)
    for i, r in enumerate(radii):
        sv = me.skin_vertices[0].data[i]
        sv.radius = r
        sv.use_root = (i == index["pelvis"])
    sumi.add_modifier(obj, "SUBSURF", levels=2, render_levels=2)
    sumi.apply_modifiers(obj)
    del skin
    sumi.shade_smooth(obj)
    return obj


def build_head(col):
    """Skull with a sculpted eye band; only the band shows through the hood slit."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    c = V(0, -0.004, 1.648)
    for v in bm.verts:
        x, y, z = v.co
        # base ellipsoid (half-extents)
        p = Vector((x * 0.074, y * 0.094, z * 0.114))
        front = max(0.0, -y)  # 0 at sides, 1 at face
        # flatten the face plane and narrow the jaw
        if z < 0:
            p.x *= 1.0 - 0.28 * (-z) ** 1.5
            p.y *= 1.0 - 0.12 * (-z) * front
        # brow ridge
        brow = math.exp(-((z - 0.18) / 0.10) ** 2) * front ** 3
        p.y -= 0.010 * brow
        # eye sockets (two soft dents either side of the nose bridge)
        for sx in (-1, 1):
            d2 = ((x - 0.42 * sx) / 0.22) ** 2 + ((z - 0.03) / 0.12) ** 2
            p.y += 0.011 * math.exp(-d2) * front
        # nose bridge
        nb = math.exp(-(x / 0.10) ** 2) * math.exp(-((z + 0.06) / 0.16) ** 2) * front ** 4
        p.y -= 0.018 * nb
        # cheekbones
        for sx in (-1, 1):
            d2 = ((x - 0.62 * sx) / 0.2) ** 2 + ((z + 0.12) / 0.10) ** 2
            p.y -= 0.006 * math.exp(-d2) * front
        v.co = c + p
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            d = (loop.vert.co - c).normalized()
            loop[uv].uv = (0.5 + math.atan2(d.x, -d.y) / (2 * math.pi), 0.5 + math.asin(max(-1, min(1, d.z))) / math.pi)
    head = sumi.mesh_object("Kage_Head", bm, col)
    sumi.shade_smooth(head)

    eyes = []
    for side, s in (("L", 1), ("R", -1)):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.0125)
        bmesh.ops.scale(bm, vec=(1.0, 0.55, 0.62), verts=bm.verts)
        e = J[f"{side}_eye"]
        bmesh.ops.translate(bm, vec=e, verts=bm.verts)
        bm.loops.layers.uv.new("UVMap")
        o = sumi.mesh_object(f"Kage_Eye_{side}", bm, col)
        sumi.shade_smooth(o)
        o.data.materials.append(MAT["eye"])
        eyes.append(o)
    head.data.materials.append(MAT["skin"])
    return head, eyes


def region_materials_and_cull(body):
    """Assign glove/tabi regions; delete faces that garments fully cover."""
    me = body.data
    for m in (MAT["cloth"], MAT["glove"], MAT["tabi"]):
        me.materials.append(m)
    # wrist boundary plane per side: points beyond the wrist along the arm are glove
    def beyond_wrist(p):
        s = 1 if p.x > 0 else -1
        w = J["L_wrist" if s > 0 else "R_wrist"]
        d = ks.ARM_DIR if s > 0 else Vector((-ks.ARM_DIR.x, ks.ARM_DIR.y, ks.ARM_DIR.z))
        return (p - w).dot(d) > -0.012

    cull = []
    for poly in me.polygons:
        p = poly.center
        if abs(p.x) > 0.45 and beyond_wrist(p):
            poly.material_index = 1
        elif p.z < 0.118:
            poly.material_index = 2
        else:
            poly.material_index = 0
        # covered by hakama (pelvis to mid calf) and leg wraps; keep a margin
        if 0.16 < p.z < 0.99 and abs(p.x) < 0.25:
            cull.append(poly.index)
        # neck is inside the hood
        elif p.z > 1.45 and abs(p.x) < 0.07:
            cull.append(poly.index)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in cull], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


# ==========================================================================
# GARMENTS — fitted to the body by ray casting so they never clip in rest pose
# ==========================================================================
class Fitter:
    """Ray-cast helper against the full (unculled) body + head."""

    def __init__(self, objs):
        from mathutils.bvhtree import BVHTree
        dg = bpy.context.evaluated_depsgraph_get()
        self.trees = [BVHTree.FromObject(o, dg) for o in objs]

    def outward(self, origin, direction, max_dist=0.6):
        """Distance from origin to the first surface going outward."""
        best = None
        for t in self.trees:
            hit = t.ray_cast(origin, direction, max_dist)
            if hit[0] is not None and (best is None or hit[3] < best):
                best = hit[3]
        return best

    def outermost(self, origin, direction, max_dist=0.6):
        """Distance from origin to the outermost surface along direction."""
        start = origin + direction * max_dist
        best = None
        for t in self.trees:
            hit = t.ray_cast(start, -direction, max_dist)
            if hit[0] is not None:
                d = max_dist - hit[3]
                best = d if best is None else max(best, d)
        return best


def _smooth_ring(vals, passes=2, closed=True):
    n = len(vals)
    for _ in range(passes):
        if closed:
            vals = [(vals[i - 1] + 2 * vals[i] + vals[(i + 1) % n]) / 4 for i in range(n)]
        else:
            vals = [vals[0]] + [(vals[i - 1] + 2 * vals[i] + vals[i + 1]) / 4 for i in range(1, n - 1)] + [vals[-1]]
    return vals


def _finish(obj, mat, thickness=None, smooth=True, offset=1.0):
    obj.data.materials.append(mat)
    if thickness:
        sumi.add_modifier(obj, "SOLIDIFY", thickness=thickness, offset=offset, use_even_offset=True,
                          use_quality_normals=True)
        sumi.apply_modifiers(obj)
    if smooth:
        sumi.shade_smooth(obj)
    return obj


def build_hood(col, fit):
    """Zukin: hood, face mask and shoulder mantle as one lofted cloth with an eye slit."""
    N = 56
    axis = V(0, 0.006, 0)
    thetas = [2 * math.pi * i / N for i in range(N)]
    dirs = [Vector((math.sin(t), -math.cos(t), 0.0)) for t in thetas]  # theta 0 = face

    def front(t):
        return max(0.0, math.cos(t))

    def hem_z(t):
        side = abs(math.sin(t))
        ragged = 0.018 * math.sin(5 * t + 0.6) + 0.012 * math.sin(11 * t + 2.0)
        return 1.235 + 0.120 * side ** 1.4 + ragged  # sides ride up over the arms

    rings = []
    # head section: crown -> chin
    crown_z, top_z = 1.735, 1.796
    head_levels = [1.795, 1.790, 1.782, 1.771, 1.756, 1.735, 1.712, 1.690, 1.668, 1.645, 1.622,
                   1.600, 1.578, 1.556, 1.535]
    crown = None
    for z in head_levels:
        zs = min(z, crown_z)
        rad = []
        for t, d in zip(thetas, dirs):
            o = axis + V(0, 0, zs)
            r = fit.outermost(o, d, 0.3) or 0.0
            fr = front(t) ** 2
            margin = 0.034 - 0.022 * fr  # snug across the face, roomy behind and above
            if 1.60 < zs < 1.70:
                margin -= 0.004 * fr
            rad.append(r + margin)
        rad = _smooth_ring(rad, 3)
        if z == crown_z:
            crown = rad
        if z > crown_z:  # elliptical dome over the crown, shifted slightly back
            k = math.sqrt(max(0.0, 1 - ((z - crown_z) / (top_z - crown_z)) ** 2))
            rad = None
        if rad is None:
            rings.append(None)
            continue
        rings.append([axis + V(0, 0, z) + d * r for d, r in zip(dirs, rad)])
    # fill the dome rings now that the crown ring is known
    for idx, z in enumerate(head_levels):
        if rings[idx] is None:
            k = math.sqrt(max(0.0, 1 - ((z - crown_z) / (top_z - crown_z)) ** 2))
            k = max(k, 0.12)
            back = V(0, 0.010 * (1 - k), 0)
            rings[idx] = [axis + back + V(0, 0, z) + d * (r * k) for d, r in zip(dirs, crown)]
    chin = [((p - axis).to_2d()).length for p in [Vector((q.x, q.y, 0)) for q in rings[-1]]]
    # mask drape: front falls straight from the chin, back tucks to the nape
    for z in (1.515, 1.495, 1.475, 1.455):
        rad = []
        for i, (t, d) in enumerate(zip(thetas, dirs)):
            o = axis + V(0, 0, z)
            r_body = (fit.outermost(o, d, 0.4) or 0.0) + 0.018
            k = (1.535 - z) / 0.08
            fr = front(t)
            target = chin[i] * (1.0 + 0.05 * fr) if fr > 0.2 else chin[i] * (1 - 0.25 * k) + r_body * 0.25 * k
            rad.append(max(target, r_body))
        rad = _smooth_ring(rad, 3)
        rings.append([axis + V(0, 0, z) + d * r for d, r in zip(dirs, rad)])
    # mantle: drape over the shoulders down to a ragged hem; radius never shrinks going down
    prev = [((p - axis) * Vector((1, 1, 0))).length for p in rings[-1]]
    steps = 12
    for s_i in range(1, steps + 1):
        k = s_i / steps
        ring, rad = [], []
        zs = [1.455 + (hem_z(t) - 1.455) * k for t in thetas]
        for i, (t, d) in enumerate(zip(thetas, dirs)):
            o = axis + V(0, 0, zs[i])
            r = (fit.outermost(o, d, 0.5) or 0.0) + 0.020 + 0.012 * k
            rad.append(max(r, prev[i] + 0.004))
        rad = _smooth_ring(rad, 2)
        # loose folds that grow toward the hem
        rad = [r + 0.010 * k * (math.sin(9 * t + 1.3) + 0.6 * math.sin(4 * t)) for r, t in zip(rad, thetas)]
        prev = rad
        rings.append([axis + V(0, 0, z) + d * r for d, r, z in zip(dirs, rad, zs)])
    # tattered points on the hem
    for i, p in enumerate(rings[-1]):
        if i % 4 == 0:
            p.z -= 0.022 + 0.012 * math.sin(i * 1.7)
    bm, grid = sumi.loft(rings, closed=True, cap_start=True, u_scale=4.0, v_scale=3.0)
    # eye slit: remove faces across the face at eye height
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        t = math.atan2(c.x, -(c.y - axis.y))
        if abs(t) < math.radians(54) and 1.619 < c.z < 1.668:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    obj = sumi.mesh_object("Kage_Hood", bm, col)
    return _finish(obj, MAT["hood"], thickness=0.006)


def build_hood_knot_and_ties(col):
    parts = []
    # knot at the back of the head
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.034, 0.020, 0.026), verts=bm.verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-25), 3, "Y"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=V(0.004, 0.118, 1.612), verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    knot = sumi.mesh_object("Kage_TieKnot", bm, col)
    parts.append(_finish(knot, MAT["hood"]))
    for name, spec, width in (("L", ks.TIE_L, 0.066), ("R", ks.TIE_R, 0.058)):
        ctrl = ks.tie_chain(**spec)
        parts.append(ribbon(f"Kage_Tie_{name}", ctrl, width, 0.62, MAT["hood"], col, twist=0.9 * spec["side"],
                            seed=spec["segments"]))
    return parts


def ribbon(name, ctrl, width, taper, mat, col, twist=0.0, seed=1, samples=40, tatter=True):
    """Cloth strip along a chain; UV v runs along the length for brush-stroke shading."""
    pts = sumi.catmull(ctrl, 8)
    pts, tans = sumi.polyline_resample(pts, samples)
    rng = sumi.seeded(seed)
    rings = []
    side_ref = Vector((1, 0, 0))
    for i, (p, tg) in enumerate(zip(pts, tans)):
        t = i / (samples - 1)
        side = (side_ref - tg * side_ref.dot(tg)).normalized()
        side = Matrix.Rotation(twist * math.sin(t * math.pi), 3, tg) @ side
        normal = tg.cross(side)
        w = width * (1 - (1 - taper) * t)
        # soft cupping across the width so the strip catches light like cloth
        flutter = 0.010 * math.sin(t * 9 + seed) * t
        a = p + side * (w / 2) + normal * (0.004 + flutter)
        b = p - side * (w / 2) + normal * (0.004 - flutter)
        m = p - normal * 0.003
        rings.append([a, m, b])
    if tatter:  # ragged end: stagger the last ring
        last = rings[-1]
        last[0] = last[0] + (pts[-1] - pts[-2]).normalized() * width * 0.7
        last[2] = last[2] - (pts[-1] - pts[-2]).normalized() * width * 0.3
    bm, grid = sumi.loft(rings, closed=False, u_scale=1.0, v_scale=1.5)
    obj = sumi.mesh_object(name, bm, col)
    obj["chain_points"] = [list(p) for p in ctrl]
    return _finish(obj, mat, thickness=0.003, offset=0.0)


def build_hakama(col, fit):
    """Wide trousers ballooning to the knee and gathered into the shin wraps."""
    parts = []
    N = 40
    for side_name, s in (("L", 1), ("R", -1)):
        # (z, axis x, axis y, design radius)
        prof = [
            (1.035, 0.050, 0.008, 0.000),
            (0.990, 0.062, 0.006, 0.012),
            (0.920, 0.080, 0.003, 0.028),
            (0.840, 0.094, 0.000, 0.042),
            (0.740, 0.100, -0.006, 0.052),
            (0.640, 0.104, -0.010, 0.060),
            (0.545, 0.106, -0.012, 0.064),
            (0.470, 0.107, -0.006, 0.062),
            (0.410, 0.107, 0.002, 0.052),
            (0.355, 0.106, 0.010, 0.034),
            (0.315, 0.106, 0.014, 0.000),
        ]
        rings = []
        for li, (z, ax, ay, design) in enumerate(prof):
            c = V(ax * s, ay, z)
            rad = []
            for i in range(N):
                t = 2 * math.pi * i / N
                d = Vector((math.sin(t), -math.cos(t), 0))
                r_body = fit.outward(c, d, 0.4) or 0.06
                # inner side (toward the other leg) is clamped near the midline
                inward = -d.x * s
                if inward > 0.05:
                    r_mid = (abs(c.x) + 0.012) / max(inward, 1e-3)
                    design_i = min(design, r_mid)
                else:
                    design_i = design * (1.0 + 0.10 * max(0.0, d.x * s))
                gap = 0.010 if z > 0.33 else 0.004
                rad.append(r_body + max(gap, design_i))
            rad = _smooth_ring(rad, 2)
            # pleats: crisp at the waist front, loosening into soft folds lower down
            pl = []
            for i, r in enumerate(rad):
                t = 2 * math.pi * i / N
                fr = max(0.0, math.cos(t))
                pleat = 0.006 * fr * math.sin(10 * t) * (1.0 if z > 0.8 else 0.5)
                fold = 0.012 * math.sin(5 * t + 2.2 * li * 0.3 + s) * (1.0 - abs(z - 0.55) / 0.5)
                gather = 0.004 * math.sin(16 * t) if z < 0.42 else 0.0
                pl.append(r + pleat + max(fold, -0.004) + gather)
            rings.append([c + Vector((math.sin(2 * math.pi * i / N), -math.cos(2 * math.pi * i / N), 0)) * r
                          for i, r in enumerate(pl)])
        bm, _ = sumi.loft(rings, closed=True, u_scale=2.0, v_scale=2.0)
        obj = sumi.mesh_object(f"Kage_Hakama_{side_name}", bm, col)
        obj["side"] = s
        parts.append(_finish(obj, MAT["cloth"], thickness=0.004))
    return parts


def _limb_wrap(name, a, b, fit, mat, col, gap, ridge, count=28, rings_n=18, pitch=0.032, flare=0.0,
               up_hint=None):
    axis = b - a
    rings = []
    t_, b_, d_ = sumi.frame_from_dir(axis, up_hint or Vector((0, 0, 1)))
    for j in range(rings_n + 1):
        k = j / rings_n
        c = a.lerp(b, k)
        ring = []
        for i in range(count):
            th = 2 * math.pi * i / count
            d = (t_ * math.cos(th) + b_ * math.sin(th)).normalized()
            r = fit.outward(c, d, 0.25) or 0.04
            # spiral binding ridges
            phase = (k * axis.length / pitch + th / (2 * math.pi)) % 1.0
            rr = r + gap + flare * k + ridge * (1 - abs(phase - 0.5) * 2) ** 3
            ring.append(c + d * rr)
        rings.append(ring)
    bm, _ = sumi.loft(rings, closed=True, u_scale=1.0, v_scale=3.0)
    obj = sumi.mesh_object(name, bm, col)
    return _finish(obj, mat)


def build_wraps(col, fit):
    parts = []
    for side in ("L", "R"):
        knee, ankle = J[f"{side}_knee"], J[f"{side}_ankle"]
        a = knee.lerp(ankle, 0.40)
        b = ankle + V(0, -0.004, 0.022)
        parts.append(_limb_wrap(f"Kage_ShinWrap_{side}", b, a, fit, MAT["wrap"], col, gap=0.012, ridge=0.004,
                                count=30, rings_n=22))
        el, wr = J[f"{side}_elbow"], J[f"{side}_wrist"]
        a = el.lerp(wr, 0.18)
        b = wr.lerp(J[f"{side}_palm"], 0.35)
        parts.append(_limb_wrap(f"Kage_ArmGuard_{side}", a, b, fit, MAT["wrap"], col, gap=0.006, ridge=0.0035,
                                count=26, rings_n=16, pitch=0.045))
        parts.append(_hand_plate(side, col))
    return parts


def _hand_plate(side, col):
    """Tekko flap over the back of the hand."""
    s = 1 if side == "L" else -1
    d = ks.ARM_DIR.copy()
    d.x *= s
    n = ks.PALM_NORMAL.copy()
    n.x *= s
    back = -n
    w = J[f"{side}_wrist"]
    th = ks.THUMB_SIDE
    rows = []
    for j in range(6):
        k = j / 5
        c = w + d * (0.005 + 0.082 * k) + back * (0.021 + 0.004 * math.sin(k * math.pi))
        half = 0.030 + 0.006 * k
        row = []
        for i in range(5):
            u = i / 4 * 2 - 1
            row.append(c + th * (u * half) - back * (0.010 * u * u))
        rows.append(row)
    bm, _ = sumi.loft(rows, closed=False)
    obj = sumi.mesh_object(f"Kage_HandPlate_{side}", bm, col)
    return _finish(obj, MAT["wrap"], thickness=0.004, offset=-1.0)


def build_obi(col, fit):
    parts = []
    N = 48
    rings = []
    for z in (0.992, 1.012, 1.040, 1.068, 1.094, 1.110):
        c = V(0, 0.008, z)
        rad = []
        for i in range(N):
            t = 2 * math.pi * i / N
            d = Vector((math.sin(t), -math.cos(t), 0))
            rad.append((fit.outermost(c, d, 0.4) or 0.13) + 0.022)
        rad = _smooth_ring(rad, 4)
        rings.append([c + Vector((math.sin(2 * math.pi * i / N), -math.cos(2 * math.pi * i / N), 0)) * r
                      for i, r in enumerate(rad)])
    # bevel the top and bottom edges inward
    for p in rings[0] + rings[-1]:
        p.x *= 0.97
        p.y = (p.y - 0.008) * 0.97 + 0.008
    bm, _ = sumi.loft(rings, closed=True, u_scale=3.0, v_scale=3.0)
    obi = sumi.mesh_object("Kage_Obi", bm, col)
    parts.append(_finish(obi, MAT["sash"], thickness=0.006))
    # red cord around the middle of the obi, knotted at the front-left
    cord_ring = [p + (p - V(0, 0.008, p.z)).normalized() * 0.006 for p in rings[2]]
    parts.append(tube("Kage_Cord", [cord_ring[i] for i in range(N)] + [cord_ring[0]], 0.0045, MAT["red"], col,
                      closed=True))
    knot_c = cord_ring[N // 10]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.012)
    bmesh.ops.translate(bm, vec=knot_c, verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    parts.append(_finish(sumi.mesh_object("Kage_CordKnot", bm, col), MAT["red"]))
    for k, (dx, L) in enumerate(((0.012, 0.15), (-0.006, 0.11))):
        pts = [knot_c, knot_c + V(dx, -0.012, -L * 0.5), knot_c + V(dx * 1.6, -0.010, -L)]
        parts.append(tube(f"Kage_CordEnd_{k}", sumi.catmull(pts, 6), 0.0032, MAT["red"], col))
    # obi knot block at the back and its two hanging tails
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.11, 0.05, 0.075), verts=bm.verts)
    bmesh.ops.translate(bm, vec=V(0.0, 0.142, 1.045), verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    knot = sumi.mesh_object("Kage_ObiKnot", bm, col)
    sumi.add_modifier(knot, "BEVEL", width=0.012, segments=2)
    sumi.add_modifier(knot, "SUBSURF", levels=1)
    sumi.apply_modifiers(knot)
    parts.append(_finish(knot, MAT["sash"]))
    for name, spec, width in (("L", ks.SASH_L, 0.10), ("R", ks.SASH_R, 0.085)):
        parts.append(ribbon(f"Kage_SashTail_{name}", ks.sash_chain(**spec), width, 0.78, MAT["sash"], col,
                            twist=0.25 * spec["side"], seed=11 + spec["segments"]))
    return parts


def tube(name, pts, radius, mat, col, closed=False, sides=8):
    pts, tans = sumi.polyline_resample(pts, max(8, len(pts)))
    rings = []
    for p, tg in zip(pts, tans):
        rings.append(sumi.ring_around(p, tg, lambda th: radius, sides))
    bm, _ = sumi.loft(rings, closed=True, cap_start=not closed, cap_end=not closed, v_scale=4.0)
    obj = sumi.mesh_object(name, bm, col)
    return _finish(obj, mat)


def build_collar(col, fit):
    """Crossed kimono collar (left over right) projected onto the chest."""
    parts = []
    specs = (
        ("Kage_Collar_Top", [V(0.072, 0.03, 1.47), V(0.06, -0.075, 1.38), V(0.0, -0.118, 1.24), V(-0.085, -0.115, 1.085)], 0.042),
        ("Kage_Collar_Under", [V(-0.072, 0.03, 1.47), V(-0.058, -0.078, 1.38), V(-0.012, -0.112, 1.27), V(0.02, -0.116, 1.21)], 0.036),
    )
    for name, ctrl, width in specs:
        pts, tans = sumi.polyline_resample(sumi.catmull(ctrl, 10), 26)
        rings = []
        for p, tg in zip(pts, tans):
            out = Vector((p.x, p.y - 0.006, 0)).normalized()
            side = tg.cross(out).normalized()
            rings.append([p + side * width * 0.5, p - side * width * 0.5])
        bm, _ = sumi.loft(rings, closed=False)
        obj = sumi.mesh_object(name, bm, col)
        sw = sumi.add_modifier(obj, "SHRINKWRAP", target=FIT_TARGET, wrap_method="NEAREST_SURFACEPOINT",
                               offset=0.010 if "Top" in name else 0.007)
        sumi.apply_modifiers(obj)
        parts.append(_finish(obj, MAT["sash"] if "Top" in name else MAT["wrap"], thickness=0.004))
    return parts


FIT_TARGET = None


# ==========================================================================
# RIG — Godot SkeletonProfileHumanoid names, cloth chains, sockets, IK controls
# ==========================================================================
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
FINGER_SEG = {"Thumb": ("Metacarpal", "Proximal", "Distal"),
              "default": ("Proximal", "Intermediate", "Distal")}
SIDE_NAME = {"L": "Left", "R": "Right"}


def bone_specs(extra_chains=()):
    """(name, head, tail, parent, deform, roll_vector) for every bone."""
    b = []
    up = V(0, -1, 0)  # roll reference for the spine: bone Z faces forward
    b.append(("Root", J["root"], J["root"] + V(0, 0, 0.18), None, True, up))
    b.append(("Hips", J["pelvis"] + V(0, 0, 0.03), J["spine"], "Root", True, up))
    b.append(("Spine", J["spine"], J["chest"], "Hips", True, up))
    b.append(("Chest", J["chest"], J["upper_chest"], "Spine", True, up))
    b.append(("UpperChest", J["upper_chest"], V(0, 0.012, 1.430), "Chest", True, up))
    b.append(("Neck", V(0, 0.016, 1.450), V(0, 0.010, 1.555), "UpperChest", True, up))
    b.append(("Head", V(0, 0.010, 1.555), J["head_top"], "Neck", True, up))
    for side in ("L", "R"):
        S = SIDE_NAME[side]
        s = 1 if side == "L" else -1
        P = lambda k: J[f"{side}_{k}"]  # noqa: E731
        b.append((f"{S}Eye", P("eye"), P("eye") + V(0, -0.03, 0), "Head", True, V(0, 0, 1)))
        fwd = V(0, -1, 0)
        b.append((f"{S}Shoulder", P("clavicle"), P("shoulder"), "UpperChest", True, V(0, 0, 1)))
        b.append((f"{S}UpperArm", P("shoulder"), P("elbow"), f"{S}Shoulder", True, fwd))
        b.append((f"{S}LowerArm", P("elbow"), P("wrist"), f"{S}UpperArm", True, fwd))
        b.append((f"{S}Hand", P("wrist"), P("Middle0"), f"{S}LowerArm", True, fwd))
        back_of_hand = -ks.PALM_NORMAL * Vector((s, 1, 1))
        for f in FINGERS:
            segs = FINGER_SEG.get(f, FINGER_SEG["default"])
            parent = f"{S}Hand"
            for i, seg in enumerate(segs):
                name = f"{S}{f}{seg}"
                b.append((name, P(f"{f}{i}"), P(f"{f}{i + 1}"), parent, True, back_of_hand))
                parent = name
        # weapon socket: head at the fist centre, +Y along the grip (out of the thumb side),
        # +Z toward the knuckles. Weapons are modelled to the same frame.
        arm_dir = ks.ARM_DIR * Vector((s, 1, 1))
        g = P("grip")
        b.append((f"{S}HandWeapon", g, g + ks.THUMB_SIDE * 0.10, f"{S}Hand", True, arm_dir))
        b.append((f"{S}UpperLeg", P("hip"), P("knee"), "Hips", True, fwd))
        b.append((f"{S}LowerLeg", P("knee"), P("ankle"), f"{S}UpperLeg", True, fwd))
        b.append((f"{S}Foot", P("ankle"), P("ball"), f"{S}LowerLeg", True, V(0, 0, 1)))
        b.append((f"{S}Toes", P("ball"), P("toe"), f"{S}Foot", True, V(0, 0, 1)))
        # sheath socket on the lower back (daggers worn horizontally, hilts outward)
        sh = V(0.085 * s, 0.150, 0.985)
        b.append((f"{S}SheathBack", sh, sh + V(-0.10 * s, 0.0, -0.012), "Hips", True, V(0, 0, 1)))
    # cloth chains
    for prefix, chain_fn, spec, parent in (("TieL", ks.tie_chain, ks.TIE_L, "Head"),
                                           ("TieR", ks.tie_chain, ks.TIE_R, "Head"),
                                           ("SashL", ks.sash_chain, ks.SASH_L, "Hips"),
                                           ("SashR", ks.sash_chain, ks.SASH_R, "Hips")):
        pts = chain_fn(**spec)
        for i in range(len(pts) - 1):
            name = f"{prefix}_{i + 1:02d}"
            b.append((name, pts[i], pts[i + 1], parent, True, V(0, -1, 0)))
            parent = name
    # character-specific chains (capes etc.): (prefix, points, parent bone)
    for prefix, pts, parent in extra_chains:
        for i in range(len(pts) - 1):
            name = f"{prefix}_{i + 1:02d}"
            b.append((name, Vector(pts[i]), Vector(pts[i + 1]), parent, True, V(0, -1, 0)))
            parent = name
    return b


HUMANOID_ONLY = None  # filled by build_armature: bones used for heat weighting


def build_armature(col, extra_chains=(), name="Kage_Rig"):
    global HUMANOID_ONLY
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    sumi.link(arm, col)
    arm_data.display_type = "STICK"
    arm.show_in_front = True
    bpy.context.view_layer.objects.active = arm
    with sumi._override(arm):
        bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    specs = bone_specs(extra_chains)
    for name, head, tail, parent, deform, roll in specs:
        e = eb.new(name)
        e.head, e.tail = head, tail
        e.align_roll(roll)
        e.use_deform = deform
        if parent:
            e.parent = eb[parent]
            e.use_connect = False
    # IK / control bones (non-deforming, stripped at export)
    for side in ("L", "R"):
        S = SIDE_NAME[side]
        s = 1 if side == "L" else -1
        wr = J[f"{side}_wrist"]
        e = eb.new(f"CTRL_IK_Hand.{side}")
        e.head, e.tail = wr, wr + ks.ARM_DIR * Vector((s, 1, 1)) * 0.09
        e.parent = eb["Root"]
        e.use_deform = False
        e = eb.new(f"CTRL_Pole_Arm.{side}")
        e.head = J[f"{side}_elbow"] + V(0, 0.35, 0)
        e.tail = e.head + V(0, 0.05, 0)
        e.parent = eb["Root"]
        e.use_deform = False
        an = J[f"{side}_ankle"]
        e = eb.new(f"CTRL_IK_Foot.{side}")
        e.head, e.tail = V(an.x, an.y, 0.0), V(an.x, an.y - 0.16, 0.0)
        e.parent = eb["Root"]
        e.use_deform = False
        e = eb.new(f"CTRL_Pole_Leg.{side}")
        e.head = J[f"{side}_knee"] + V(0, -0.45, 0)
        e.tail = e.head + V(0, -0.05, 0)
        e.parent = eb["Root"]
        e.use_deform = False
    kage_rig.edit_bones(eb, J)  # torso control, IK hand frames, reverse-foot mechanism
    with sumi._override(arm):
        bpy.ops.object.mode_set(mode="POSE")
    pb = arm.pose.bones
    for side in ("L", "R"):
        S = SIDE_NAME[side]
        for chain, tip, target, pole, angle in (
                ("Arm", f"{S}LowerArm", f"CTRL_IK_Hand.{side}", f"CTRL_Pole_Arm.{side}", -90),
                ("Leg", f"{S}LowerLeg", f"CTRL_IK_Foot.{side}", f"CTRL_Pole_Leg.{side}", 90)):
            c = pb[tip].constraints.new("IK")
            c.name = f"IK_{chain}"
            c.target, c.subtarget = arm, target
            c.pole_target, c.pole_subtarget = arm, pole
            c.pole_angle = math.radians(angle)
            c.chain_count = 2
            c.influence = 0.0  # FK by default; animators blend via the custom property below
            fcurve = c.driver_add("influence")
            drv = fcurve.driver
            drv.type = "AVERAGE"
            var = drv.variables.new()
            var.targets[0].id = arm
            var.targets[0].data_path = f'["ik_{chain.lower()}_{side}"]'
            arm[f"ik_{chain.lower()}_{side}"] = 0.0
    # bone collections for the animator
    groups = {"Body": [], "Fingers": [], "Cloth": [], "Sockets": [], "Controls": []}
    for b in arm_data.bones:
        n = b.name
        if n.startswith(("CTRL_", "MCH_")):  # MCH_ moves to the hidden Mechanism collection
            groups["Controls"].append(b)
        elif n.endswith(("Weapon", "SheathBack")):
            groups["Sockets"].append(b)
        elif n.startswith(("Tie", "Sash", "Cape")):
            groups["Cloth"].append(b)
        elif any(f in n for f in FINGERS):
            groups["Fingers"].append(b)
        else:
            groups["Body"].append(b)
    for gname, bones in groups.items():
        bc = arm_data.collections.new(gname)
        for b in bones:
            bc.assign(b)
    kage_rig.pose_setup(arm)   # foot roll, hand/foot IK follow, torso Child Of
    kage_rig.appearance(arm)   # widgets, colours, Mechanism collection
    kage_rig.install_ui(arm)   # "Kage Rig" sidebar panel (IK/FK sliders + snapping)
    with sumi._override(arm):
        bpy.ops.object.mode_set(mode="OBJECT")
    HUMANOID_ONLY = [b.name for b in arm_data.bones if b in groups["Body"] or b in groups["Fingers"]]
    return arm


def heat_weights(proxy, arm):
    """Bone-heat weights from humanoid bones only (eyes/sockets/cloth excluded)."""
    saved = {b.name: b.use_deform for b in arm.data.bones}
    for b in arm.data.bones:
        b.use_deform = b.name in HUMANOID_ONLY and not b.name.endswith("Eye")
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[proxy, arm],
                                   selected_editable_objects=[proxy, arm]):
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for b in arm.data.bones:
        b.use_deform = saved[b.name]
    missing = sum(1 for v in proxy.data.vertices if not v.groups)
    sumi.log("heat weights: unweighted verts", missing)


def transfer_weights(obj, source):
    mod = obj.modifiers.new("WeightXfer", "DATA_TRANSFER")
    mod.object = source
    mod.use_vert_data = True
    mod.data_types_verts = {"VGROUP_WEIGHTS"}
    mod.vert_mapping = "POLYINTERP_NEAREST"
    mod.layers_vgroup_select_src = "ALL"
    mod.layers_vgroup_select_dst = "NAME"
    with sumi._override(obj):
        bpy.ops.object.datalayout_transfer(modifier=mod.name)
    sumi.apply_modifiers(obj)


def set_weights(obj, fn):
    """fn(vertex_co) -> {bone: weight}"""
    for v in obj.data.vertices:
        for bone, w in fn(v.co).items():
            if w <= 1e-4:
                continue
            vg = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
            vg.add([v.index], w, "REPLACE")


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def chain_weights(obj, prefix, ctrl, root_bone, root_blend=0.35):
    """Weights along a cloth chain by projecting each vertex onto the chain polyline."""
    pts = [Vector(p) for p in ctrl]
    seglens = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]

    def fn(co):
        best = (1e9, 0, 0.0)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ab = b - a
            t = max(0.0, min(1.0, (co - a).dot(ab) / ab.length_squared))
            d = (a + ab * t - co).length
            if d < best[0]:
                best = (d, i, t)
        _, i, t = best
        out = {}
        bone = f"{prefix}_{i + 1:02d}"
        # blend across joints: second half of segment i blends into i+1
        if t > 0.5 and i + 1 < len(seglens):
            k = (t - 0.5)
            out[bone] = 1 - k
            out[f"{prefix}_{i + 2:02d}"] = k
        elif t <= 0.5 and i > 0:
            k = (0.5 - t)
            out[bone] = 1 - k
            out[f"{prefix}_{i:02d}"] = k
        else:
            out[bone] = 1.0
        if i == 0:
            r = root_blend * (1 - t)
            out = {k: v * (1 - r) for k, v in out.items()}
            out[root_bone] = r
        return out

    set_weights(obj, fn)


def hakama_weights(obj):
    s = obj["side"]
    S = "Left" if s > 0 else "Right"

    def fn(co):
        z = co.z
        hips = 1 - smoothstep(0.78, 0.99, z) * 0 - smoothstep(0.80, 0.99, z) * 0
        up = smoothstep(0.50, 0.66, z) * (1 - smoothstep(0.80, 0.99, z))
        low = 1 - smoothstep(0.50, 0.66, z)
        hips = smoothstep(0.80, 0.99, z)
        # the inner panel near the crotch follows the hips more, preventing tearing
        inner = max(0.0, -co.x * s) / 0.1
        hips = min(1.0, hips + 0.25 * inner * (z > 0.75))
        tot = hips + up + low
        return {"Hips": hips / tot, f"{S}UpperLeg": up / tot, f"{S}LowerLeg": low / tot}

    set_weights(obj, fn)


def finalize_weights(obj, limit=4, floor=0.01):
    """Drop tiny weights, keep the strongest `limit` influences, renormalise.

    Done in Python rather than via vertex_group_* operators, which silently
    no-op without a full editor context in background mode.
    """
    groups = obj.vertex_groups
    for v in obj.data.vertices:
        ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > floor), reverse=True)[:limit]
        total = sum(w for w, _ in ws)
        keep = {gi for _, gi in ws}
        # copy indices first: VertexGroupElement refs go stale after a remove()
        for gi in [g.group for g in v.groups]:
            if gi not in keep:
                groups[gi].remove([v.index])
        if total > 0:
            for w, gi in ws:
                groups[gi].add([v.index], w / total, "REPLACE")


def bind(obj, arm):
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm


def rig_character(arm, body, body_ref, head, eyes, garments, prefix="Kage"):
    """Garments may carry custom props to pick their weighting:
    chain_prefix/chain_points/chain_root[/chain_root_blend] -> cloth chain,
    rigid_bone -> 100% one bone, side -> hakama-style leg blend, else transfer."""
    head_copy = head.copy()
    head_copy.data = head.data.copy()
    sumi.link(head_copy, sumi.collection(f"{prefix}_Reference"))
    proxy = sumi.join([body_ref, head_copy], f"{prefix}_WeightProxy")
    heat_weights(proxy, arm)
    proxy.modifiers.clear()
    proxy.parent = None
    # head and eyes are rigid
    set_weights(head, lambda co: {"Head": 1.0})
    for e, S in zip(eyes, ("Left", "Right")):
        set_weights(e, lambda co, S=S: {f"{S}Eye": 1.0})
    transfer_weights(body, proxy)
    for g in garments:
        n = g.name
        if "chain_prefix" in g:
            chain_weights(g, g["chain_prefix"], [Vector(p) for p in g["chain_points"]], g["chain_root"],
                          root_blend=g.get("chain_root_blend", 0.35))
        elif "rigid_bone" in g:
            set_weights(g, lambda co, b=g["rigid_bone"]: {b: 1.0})
        elif "side" in g:
            hakama_weights(g)
        elif n.startswith("Kage_Tie_"):
            side = n[-1]
            spec = ks.TIE_L if side == "L" else ks.TIE_R
            chain_weights(g, f"Tie{side}", ks.tie_chain(**spec), "Head")
        elif n.startswith("Kage_SashTail_"):
            side = n[-1]
            spec = ks.SASH_L if side == "L" else ks.SASH_R
            chain_weights(g, f"Sash{side}", ks.sash_chain(**spec), "Hips", root_blend=0.5)
        elif n.startswith("Kage_Hakama_"):
            hakama_weights(g)
        elif n in ("Kage_TieKnot",):
            set_weights(g, lambda co: {"Head": 1.0})
        elif n in ("Kage_ObiKnot",):
            set_weights(g, lambda co: {"Hips": 1.0})
        else:
            transfer_weights(g, proxy)
    for o in [body, head, *eyes, *garments]:
        finalize_weights(o)
        bind(o, arm)
    proxy.hide_render = True
    proxy.hide_set(True)
    return proxy


# ==========================================================================
# RIG-TEST ACTIONS — validate deformation in Blender and Godot.
# These are rig validation clips and a blocking stance, not final animation.
# ==========================================================================
def _local_axis(pb, world_axis):
    return (pb.bone.matrix_local.to_3x3().inverted() @ Vector(world_axis)).normalized()


def pose(arm, spec):
    """spec: {bone: [(world_axis, degrees), ...] or {"loc": (x,y,z) world offset}}"""
    from mathutils import Quaternion
    for pb in arm.pose.bones:
        if pb.name.startswith("MCH_"):  # mechanism: driven, never posed directly
            continue
        if pb.name.startswith("CTRL_IK_Foot"):
            pb["roll"] = 0.0
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for name, ops in spec.items():
        pb = arm.pose.bones[name]
        if isinstance(ops, dict) and "aim" in ops:
            bpy.context.view_layer.update()
            aim(arm, pb, Vector(ops["aim"]), ops.get("twist", 0.0))
            continue
        if isinstance(ops, dict):
            if "loc" in ops:
                pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(ops["loc"])
            ops = ops.get("rot", [])
        q = Quaternion()
        for axis, deg in ops:
            q = Quaternion(_local_axis(pb, axis), math.radians(deg)) @ q
        pb.rotation_quaternion = q


def aim(arm, pb, target_dir, twist_deg=0.0):
    """Rotate pb so its posed direction points along target_dir (armature space)."""
    from mathutils import Quaternion
    if pb.parent:
        m0 = pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
    else:
        m0 = pb.bone.matrix_local
    t_local = m0.to_3x3().inverted() @ target_dir.normalized()
    q = Vector((0, 1, 0)).rotation_difference(t_local.normalized())
    q = q @ Quaternion((0, 1, 0), math.radians(twist_deg))
    pb.rotation_quaternion = q


def key_all(arm, frame, props=None):
    for pb in arm.pose.bones:
        if pb.name.startswith("MCH_"):
            continue
        if pb.name.startswith("CTRL_IK_Foot"):
            pb.keyframe_insert('["roll"]', frame=frame)
        if pb.name.startswith("CTRL_"):
            pb.keyframe_insert("location", frame=frame)
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if pb.name in ("Hips", "Root"):
            pb.keyframe_insert("location", frame=frame)
    for k in ("ik_arm_L", "ik_arm_R", "ik_leg_L", "ik_leg_R"):
        arm[k] = (props or {}).get(k, 0.0)
        arm.keyframe_insert(f'["{k}"]', frame=frame)


def new_action(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    return act


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def fist(side, amount=1.0):
    S = SIDE_NAME[side]
    out = {}
    s = 1 if side == "L" else -1
    # curl axis: across the knuckles (thumb-side vector), sign per side
    axis = tuple(ks.THUMB_SIDE * (-s))
    for f in ("Index", "Middle", "Ring", "Little"):
        for i, seg in enumerate(FINGER_SEG["default"]):
            out[f"{S}{f}{seg}"] = [(axis, (70, 85, 60)[i] * amount)]
    out[f"{S}ThumbProximal"] = [(tuple(ks.ARM_DIR * Vector((s, 1, 1))), 25 * amount * s)]
    out[f"{S}ThumbDistal"] = [(axis, 40 * amount)]
    return out


def build_actions(arm):
    # --- range of motion: every major joint through a comfortable range -------
    new_action(arm, "RigTest_ROM")
    keys = [
        {},
        {"Spine": [(X, 18)], "Chest": [(X, 12)], "Neck": [(X, 20)]},
        {"Spine": [(Z, 25)], "Chest": [(Z, 15)], "Head": [(Z, 45)]},
        {"Spine": [(Y, -15)], "Chest": [(Y, -10)], "Head": [(Y, 15)]},
        {"LeftUpperArm": [(Y, -60)], "RightUpperArm": [(Y, 60)]},           # arms up to T and beyond
        {"LeftUpperArm": [(Y, 45)], "RightUpperArm": [(Y, -45)]},           # arms down to sides
        {"LeftUpperArm": [(X, -80)], "RightUpperArm": [(X, -80)],           # arms forward
         "LeftLowerArm": [(Z, 100)], "RightLowerArm": [(Z, -100)]},
        {**fist("L"), **fist("R")},
        {"LeftUpperLeg": [(X, -70)], "LeftLowerLeg": [(X, 90)], "RightUpperLeg": [(X, 25)]},
        {"RightUpperLeg": [(X, -70)], "RightLowerLeg": [(X, 90)], "LeftUpperLeg": [(Y, 30)]},
        {"Hips": {"loc": (0, 0, -0.30)}, "LeftUpperLeg": [(X, -75)], "RightUpperLeg": [(X, -75)],
         "LeftLowerLeg": [(X, 110)], "RightLowerLeg": [(X, 110)], "LeftFoot": [(X, -30)], "RightFoot": [(X, -30)],
         "Spine": [(X, 25)]},
        {},
    ]
    for i, k in enumerate(keys):
        pose(arm, k)
        key_all(arm, 1 + i * 12)

    # --- dual dagger guard (reverse grip) — blocking pose with breathing loop -
    new_action(arm, "Stance_DualDaggers_Idle")
    for f, breathe in ((1, 0.0), (31, 1.0), (61, 0.0)):
        b = breathe
        guard = {
            "Hips": {"loc": (0, 0.02, -0.10 - 0.008 * b), "rot": [(Z, -24), (X, -4)]},
            "Spine": [(X, 10 + 1.5 * b), (Z, 6)],
            "Chest": [(X, 6 + 1.5 * b), (Z, 6)],
            "UpperChest": [(X, 2 - 1.0 * b)],
            "Neck": [(X, -8), (Z, 6)],
            "Head": [(X, -6 - 1.5 * b), (Z, 5)],
            # lead (left) hand forward at chin height, blade lying back along the forearm
            "LeftShoulder": [(X, -8)],
            "LeftUpperArm": {"aim": (0.36, -0.62, -0.46 + 0.02 * b), "twist": -30},
            "LeftLowerArm": {"aim": (-0.38, -0.52, 0.62), "twist": 0},
            "LeftHand": {"aim": (-0.34, -0.62, 0.50), "twist": 20},
            # rear (right) hand cocked low by the hip, ready to strike
            "RightShoulder": [(X, 6)],
            "RightUpperArm": {"aim": (-0.34, 0.22, -0.90), "twist": 20},
            "RightLowerArm": {"aim": (0.22, -0.88, 0.22 + 0.02 * b)},
            "RightHand": {"aim": (0.30, -0.92, 0.05), "twist": -30},
            # legs: lead left foot forward, knees soft, rear heel lifted
            "LeftUpperLeg": {"aim": (0.16, -0.58, -0.80), "twist": 15},
            "LeftLowerLeg": {"aim": (0.04, 0.10, -0.995)},
            "LeftFoot": {"aim": (0.22, -0.95, -0.20)},
            "RightUpperLeg": {"aim": (-0.16, 0.36, -0.92), "twist": -10},
            "RightLowerLeg": {"aim": (-0.06, 0.50, -0.86)},
            "RightFoot": {"aim": (-0.30, -0.86, -0.42)},
            "TieL_01": [(X, -6 * b)], "TieR_01": [(X, -5 * b)],
        }
        guard.update(fist("L"))
        guard.update(fist("R"))
        pose(arm, guard)
        key_all(arm, f)
    build_halberd_stance(arm)
    import moves  # shared playable-slice moveset (tools/blender/lib/moves.py)
    global EVENTS
    EVENTS = moves.build(sys.modules[__name__], arm)
    for act in bpy.data.actions:
        act.frame_range = act.frame_range  # ensure stored
    arm.animation_data.action = bpy.data.actions["RigTest_ROM"]
    pose(arm, {})


def orient_socket(arm, hand, socket, y_dir, z_dir):
    """Rotate `hand` so its child `socket` bone ends up with +Y = y_dir, +Z ~ z_dir."""
    bpy.context.view_layer.update()
    pb, sb = arm.pose.bones[hand], arm.pose.bones[socket]
    y = Vector(y_dir).normalized()
    x = y.cross(Vector(z_dir)).normalized()
    z = x.cross(y)
    rs = Matrix((x, y, z)).transposed()
    rel = pb.bone.matrix_local.to_3x3().inverted() @ sb.bone.matrix_local.to_3x3()
    rh = rs @ rel.inverted()
    m0 = pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
    pb.rotation_quaternion = (m0.to_3x3().inverted() @ rh).to_quaternion()
    # in IK the hand copies CTRL_IK_Hand's rotation (same rest frame): orient it to match
    ctrl = arm.pose.bones.get(f"CTRL_IK_Hand.{hand[0]}")
    if ctrl is not None:
        ctrl.rotation_quaternion = (ctrl.bone.matrix_local.to_3x3().inverted() @ rh).to_quaternion()


def _wrist_target(arm, side, grip):
    sh = arm.pose.bones[f"{SIDE_NAME[side]}UpperArm"].head
    return grip + (sh - grip).normalized() * 0.065


def build_halberd_stance(arm):
    """Two-handed polearm guard (shared by every character on the common skeleton).

    Arms are solved with the rig's IK controls: the main (right) hand holds the
    shaft low by the hip, the left hand is placed on the *actual* shaft line after
    the right hand is oriented, so the weapon sits in both fists.
    """
    new_action(arm, "Stance_Halberd_Idle")
    shaft = Vector((0.42, -0.70, 0.50)).normalized()
    edge = Vector((0.0, 0.0, -1.0))
    edge = (edge - shaft * edge.dot(shaft)).normalized()
    for f, b in ((1, 0.0), (31, 1.0), (61, 0.0)):
        for k in ("ik_arm_L", "ik_arm_R"):
            arm[k] = 1.0
        grip_r = Vector((-0.17, -0.06, 0.90 - 0.008 * b))
        body = {
            "Hips": {"loc": (0, 0.03, -0.09 - 0.008 * b), "rot": [(Z, -18), (X, -3)]},
            "Spine": [(X, 6 + 1.5 * b), (Z, 4)],
            "Chest": [(X, 4 + 1.5 * b), (Z, 6)],
            "Neck": [(X, -6), (Z, 4)],
            "Head": [(X, -4 - 1.5 * b), (Z, 4)],
            "LeftUpperLeg": {"aim": (0.16, -0.50, -0.85), "twist": 12},
            "LeftLowerLeg": {"aim": (0.04, 0.12, -0.99)},
            "LeftFoot": {"aim": (0.25, -0.94, -0.22)},
            "RightUpperLeg": {"aim": (-0.18, 0.34, -0.92), "twist": -10},
            "RightLowerLeg": {"aim": (-0.06, 0.46, -0.89)},
            "RightFoot": {"aim": (-0.35, -0.84, -0.40)},
        }
        body.update(fist("L"))
        body.update(fist("R"))
        pose(arm, body)
        bpy.context.view_layer.update()
        pb = arm.pose.bones
        rest = lambda n: pb[n].bone.head_local  # noqa: E731
        pb["CTRL_IK_Hand.R"].location = pb["CTRL_IK_Hand.R"].bone.matrix_local.to_3x3().inverted() @ (
            _wrist_target(arm, "R", grip_r) - rest("CTRL_IK_Hand.R"))
        orient_socket(arm, "RightHand", "RightHandWeapon", shaft, edge)
        bpy.context.view_layer.update()
        # put the off hand on the real shaft line, 0.52 m up from the main grip
        s_m = arm.matrix_world.inverted() @ (arm.matrix_world @ pb["RightHandWeapon"].matrix)
        axis = s_m.to_3x3() @ Vector((0, 1, 0))
        grip_l = s_m.translation + axis.normalized() * 0.52
        pb["CTRL_IK_Hand.L"].location = pb["CTRL_IK_Hand.L"].bone.matrix_local.to_3x3().inverted() @ (
            _wrist_target(arm, "L", grip_l) - rest("CTRL_IK_Hand.L"))
        orient_socket(arm, "RightHand", "RightHandWeapon", shaft, edge)
        orient_socket(arm, "LeftHand", "LeftHandWeapon", axis, edge)
        key_all(arm, f, props={"ik_arm_L": 1.0, "ik_arm_R": 1.0})
    for k in ("ik_arm_L", "ik_arm_R"):
        arm[k] = 0.0


def preview(objs, name):
    sumi.setup_preview_render((900, 1200))
    tgt = V(0, 0, 0.95)
    paths = []
    for label, loc in (("front", (0, -6.0, 0.95)), ("side", (6.0, 0, 0.95)),
                       ("back", (0, 6.0, 0.95)), ("three_quarter", (3.6, -4.6, 1.4))):
        cam = sumi.look_at_camera("PreviewCam_" + label, loc, tgt, lens=85)
        paths.append(os.path.join(PREVIEW_DIR, f"{name}_{label}.png"))
        sumi.render_to(paths[-1], cam)
        bpy.data.objects.remove(cam)
    sumi.contact_sheet(paths, os.path.join(PREVIEW_DIR, f"{name}_sheet.png"))
    for p in paths:  # keep only the sheet
        os.remove(p)


PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
EVENTS = {}


def write_events(events):
    """Clip timing for the game and the pose site: hits, link (combo) windows,
    trails, root motion per frame, native locomotion speeds, pose metadata."""
    import json
    path = sumi.repo_path("game", "data", "clip_events.json")
    data = {"_comment": "Generated by tools/blender/build_kage.py (lib/daggers.py). Times in seconds; "
                        "root = forward metres per frame at 30 fps. Do not edit by hand.", "fps": 30}
    data.update(events)
    with open(path, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    sumi.log("clip events", os.path.relpath(path, sumi.repo_path()), len(events.get("clips", {})), "clips")


def main():
    sumi.reset_scene()
    make_materials()
    col = sumi.collection("Kage")
    body = build_body(col)
    body_ref = body.copy()
    body_ref.data = body.data.copy()
    body_ref.name = body_ref.data.name = "Kage_BodyRef"
    sumi.link(body_ref, sumi.collection("Kage_Reference"))
    if "--nocull" not in ARGS:
        region_materials_and_cull(body)
    head, eyes = build_head(col)
    global FIT_TARGET
    FIT_TARGET = body_ref
    fit = Fitter([body_ref, head])
    garments = [build_hood(col, fit)]
    garments += build_hood_knot_and_ties(col)
    garments += build_hakama(col, fit)
    garments += build_wraps(col, fit)
    garments += build_obi(col, fit)
    garments += build_collar(col, fit)
    body_ref.hide_render = True
    for o in [body, head, *eyes, *garments]:
        sumi.ensure_uv(o)
        sumi.bake_cavity_to_color(o)
    arm = build_armature(sumi.collection("Kage"))
    rig_character(arm, body, body_ref, head, eyes, garments)
    build_actions(arm)
    write_events(EVENTS)
    total = sum(sumi.tri_count(o) for o in [body, head, *eyes, *garments])
    sumi.log("body tris", sumi.tri_count(body), "total", total)
    if "--preview" in ARGS:
        arm.animation_data.action = None
        pose(arm, {})
        preview(None, "kage")
    if "--preview-pose" in ARGS:
        arm.animation_data.action = bpy.data.actions["Stance_DualDaggers_Idle"]
        bpy.context.scene.frame_set(1)
        preview(None, "kage_stance")
        arm.animation_data.action = bpy.data.actions["RigTest_ROM"]
        for fr in (49, 73, 85, 97, 121):
            bpy.context.scene.frame_set(fr)
            preview(None, f"kage_rom{fr:03d}")
        arm.animation_data.action = None
        pose(arm, {})
    sumi.save_blend(OUT)


if __name__ == "__main__":
    main()
