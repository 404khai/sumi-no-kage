"""Build the greatsword, broadsword and naginata (docs/reference/weapons/).

    blender -b --factory-startup --python tools/blender/build_blades.py [-- --preview]

Output: assets_src/weapons/blades/blades.blend with collections
Export_Greatsword, Export_Broadsword, Export_Naginata (one glb each).

Shared weapon frame (see build_daggers.py): origin = main-hand grip, authored
along +Y with the edge toward +Z, then rotated by WEAPON_FRAME. Two-handed
weapons carry `Socket_OffHand`. Reference colours are translated to ink:
red/purple blades -> pale steel with hard ink facets, glow -> ink inlay, gems ->
the single vermilion accent (docs/weapon_design_language.md).
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

import build_halberd as H  # noqa: E402
import sumi  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = sumi.repo_path("assets_src", "weapons", "blades", "blades.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
MAT = H.MAT


def section_blade(name, y0, y1, width_fn, thick_fn, col, mat=None, steps=40, z_off=None):
    """Straight blade with a flattened-hexagon (diamond with flats) section."""
    rings = []
    for k in range(steps + 1):
        t = k / steps
        y = y0 + (y1 - y0) * t
        w, th = width_fn(t), thick_fn(t)
        zc = z_off(t) if z_off else 0.0
        rings.append([Vector((0, y, zc + w)), Vector((th * 0.6, y, zc + w * 0.55)), Vector((th, y, zc)),
                      Vector((th * 0.6, y, zc - w * 0.55)), Vector((0, y, zc - w)), Vector((-th * 0.6, y, zc - w * 0.55)),
                      Vector((-th, y, zc)), Vector((-th * 0.6, y, zc + w * 0.55))])
    bm, grid = sumi.loft(rings, closed=True, cap_start=True)
    tip = bm.verts.new(rings[-1][2].lerp(rings[-1][6], 0.5) + Vector((0, 0.01, 0)))
    for i in range(8):
        bm.faces.new((grid[-1][i], grid[-1][(i + 1) % 8], tip))
    sumi.orient_outward(bm)
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat or MAT["steel"])
    sumi.shade_smooth(obj, angle_deg=25)  # hard facets read as ink chamfers
    return obj


def box(name, size, center, mat, col):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    return obj


def wrapped_grip(name, y0, y1, r, col, pitch=0.03):
    def wrap(y, th):
        phase = (y / pitch + th / (2 * math.pi)) % 1.0
        return 1.0 + 0.12 * (1 - abs(phase - 0.5) * 2) ** 2
    prof = [(y0 + (y1 - y0) * k / 40, r) for k in range(41)]
    return H.lathe(name, prof, MAT["wrap"], col, sides=10, wrap=wrap)


# ------------------------------------------------------------------ greatsword
def greatsword(col):
    """Follows docs/reference/weapons/greatsword.png: a long, wide blade ending in an
    asymmetric chisel point, a raised central ridge, an angular flared ricasso block,
    a clawed crossguard whose prongs hook toward the blade, and a long segmented hilt
    with a spiked pommel. The reference's blood-red blade is kept as ink-red."""
    import armor_kit as ak
    parts = []
    # hilt: wrapped grip with three iron rings, spiked pommel
    parts.append(wrapped_grip("GS_Grip", -0.24, 0.20, 0.017, col, pitch=0.022))
    for y in (-0.10, 0.02, 0.14):
        parts.append(H.lathe(f"GS_Ring{y}", [(y - 0.012, 0.019), (y, 0.023), (y + 0.012, 0.019)], MAT["fittings"],
                             col, sides=8))
    parts.append(H.lathe("GS_Pommel", [(-0.33, 0.003), (-0.30, 0.020), (-0.265, 0.032), (-0.245, 0.022)],
                         MAT["fittings"], col, sides=6))
    for s in (1, -1):
        parts.append(ak.horn(f"GS_PommelSpike{s}", [Vector((0, -0.27, 0.025 * s)), Vector((0, -0.29, 0.06 * s)),
                                                    Vector((0, -0.27, 0.085 * s))], 0.010, MAT["fittings"], col,
                             sides=5))
    # crossguard: angular bar, prongs hooking forward toward the blade (claws)
    guard = [(0.205, -0.11), (0.25, -0.13), (0.255, 0.13), (0.205, 0.11), (0.19, 0.0)]
    gp = H.outline_plate("GS_Guard", guard, [], [], MAT["fittings"], col, thick=0.045, bevel=1.0)
    parts.append(gp)
    for s in (1, -1):
        parts.append(ak.horn(f"GS_Claw{s}", [Vector((0, 0.24, 0.12 * s)), Vector((0, 0.29, 0.16 * s)),
                                             Vector((0, 0.36, 0.15 * s)), Vector((0, 0.41, 0.115 * s))],
                             0.020, MAT["fittings"], col, sides=6))
    # ricasso block: flares into angular shoulders, then narrows into the blade
    ric = [(0.25, -0.045), (0.31, -0.080), (0.40, -0.068), (0.44, -0.050), (0.44, 0.050), (0.40, 0.068),
           (0.31, 0.080), (0.25, 0.045)]
    parts.append(H.outline_plate("GS_Ricasso", ric, [], [], MAT["fittings"], col, thick=0.032, bevel=1.0))
    # blade: one straight edge to the point, the other cut on a long diagonal (chisel tip)
    w = 0.060
    blade = [(0.43, -w), (1.42, -0.78 * w), (1.82, 0.45 * w), (1.80, 0.62 * w), (0.43, w)]
    parts.append(H.outline_plate("GS_Blade", blade, [], blade, MAT["gs_blade"], col, thick=0.016, bevel=0.03))
    # central ridge (the raised spine line in the reference), both faces
    for sx in (1, -1):
        ridge = [(0.46, -0.005), (1.55, -0.005), (1.70, 0.02), (1.70, 0.028), (1.55, 0.005), (0.46, 0.005)]
        r = H.outline_plate(f"GS_Ridge{sx}", ridge, [], [], MAT["wrap"], col, thick=0.002, bevel=1.0)
        for v in r.data.vertices:
            v.co.x += sx * 0.0081
        parts.append(r)
    return parts


# ------------------------------------------------------------------ broadsword
def broadsword(col):
    """The slab: a wide rectangular blade with a clipped tip and a vermilion triangle inlay."""
    parts = []
    parts.append(wrapped_grip("BS_Grip", -0.26, 0.18, 0.014, col, pitch=0.025))
    parts.append(H.lathe("BS_Pommel", [(-0.32, 0.006), (-0.31, 0.022), (-0.27, 0.022), (-0.255, 0.016)],
                         MAT["fittings"], col, sides=8))
    parts.append(box("BS_Guard", (0.05, 0.06, 0.22), (0, 0.21, 0), MAT["fittings"], col))
    w = 0.10  # half-width
    outline = [(0.24, -w), (1.30, -w), (1.45, w * 0.1), (1.40, w), (0.24, w)]  # clipped tip on the spine side
    parts.append(H.outline_plate("BS_Blade", outline, [], [(0.24, w), (1.40, w), (1.45, w * 0.1)], MAT["steel"],
                                 col, thick=0.022, bevel=0.03))
    # panel lines (ink strokes) and the triangle near the guard, both faces
    for sx in (1, -1):
        tri = [(0.30, -0.035), (0.30, 0.035), (0.38, 0.0)]
        t = H.outline_plate(f"BS_Tri{sx}", tri, [], [], MAT["red"], col, thick=0.002, bevel=1.0)
        for v in t.data.vertices:
            v.co.x += sx * 0.0115
        parts.append(t)
        for z in (-0.055, 0.055):
            strip = [(0.42, z - 0.004), (1.25, z - 0.004), (1.25, z + 0.004), (0.42, z + 0.004)]
            p = H.outline_plate(f"BS_Panel{sx}{z}", strip, [], [], MAT["wrap"], col, thick=0.002, bevel=1.0)
            for v in p.data.vertices:
                v.co.x += sx * 0.0112
            parts.append(p)
    return parts


# -------------------------------------------------------------------- naginata
def naginata(col):
    """Curved leaf blade with three spine notches, a ring cut-out and an ink channel;
    square tsuba; long shaft with a criss-cross wrapped lower half."""
    parts = []
    butt, top = -0.85, 1.06

    def wrap(y, th):
        if y > 0.25:
            return 1.0
        a = abs(((y / 0.05 + th / math.pi) % 1.0) - 0.5)
        b = abs(((y / 0.05 - th / math.pi) % 1.0) - 0.5)
        return 1.0 + 0.16 * max(0.0, 0.5 - min(a, b) * 2.5)
    parts.append(H.lathe("NG_Shaft", [(butt + 0.04 + (top - butt - 0.04) * k / 100, 0.016) for k in range(101)],
                         MAT["wrap"], col, sides=12, wrap=wrap))
    parts.append(H.lathe("NG_Butt", [(butt, 0.008), (butt + 0.01, 0.017), (butt + 0.05, 0.0175)], MAT["fittings"],
                         col))
    parts.append(H.lathe("NG_Collar", [(top - 0.05, 0.0165), (top - 0.045, 0.021), (top, 0.021)], MAT["fittings"], col))
    parts.append(box("NG_Tsuba", (0.012, 0.012, 0.11), (0, top + 0.006, 0.0), MAT["fittings"], col))
    parts[-1].scale = (1, 1, 1)
    tb = parts[-1]
    for v in tb.data.vertices:  # square plate: widen across X too
        v.co.x *= 6.0
    # blade (reference: wide leaf, big belly on the edge, stepped spine notches, ring, channel)
    y0, L = top + 0.012, 0.64
    n = 48

    def spine_z(t):
        return -0.042 + 0.010 * t + 0.045 * max(0.0, t - 0.55) ** 2 / 0.2

    def width(t):
        belly = 0.072 + 0.032 * math.sin(math.pi * min(t / 0.7, 1.0) * 0.85)
        fall = max(0.0, (t - 0.45) / 0.55)
        return belly * (1 - fall ** 1.7) ** 0.75 + 0.0005

    def notch(t):  # three rectangular steps cut into the spine
        if 0.07 < t < 0.31:
            f = ((t - 0.07) / 0.24 * 3) % 1.0
            return 0.012 if f > 0.45 else 0.0
        return 0.0

    spine, edge = [], []
    for k in range(n + 1):
        t = k / n
        y = y0 + L * t
        z0 = spine_z(t)
        spine.append((y, z0 + notch(t)))
        edge.append((y + 0.02 * (1 - t) ** 8, z0 + width(t)))  # angled heel at the base
    tip = (y0 + L + 0.015, spine_z(1.0) + 0.004)
    outline = spine + [tip] + list(reversed(edge))
    rc = (y0 + 0.36 * 0.0 + 0.085, spine_z(0.13) + 0.034)
    ring = [(rc[0] + 0.015 * math.cos(a), rc[1] + 0.015 * math.sin(a)) for a in
            [2 * math.pi * i / 16 for i in range(16)]]
    parts.append(H.outline_plate("NG_Blade", outline, [ring], edge + [tip], MAT["steel"], col, thick=0.011,
                                 bevel=0.04))
    # the reference's glowing channel -> a thin vermilion inlay running up the blade, both faces
    for sx in (1, -1):
        pts = []
        for k in range(15):
            t = 0.20 + 0.52 * k / 14
            pts.append((y0 + L * t, spine_z(t) + 0.026 + 0.012 * math.sin(math.pi * (t - 0.2) / 0.52)))
        strip = [(y, z - 0.0032) for y, z in pts] + [(y, z + 0.0032) for y, z in reversed(pts)]
        p = H.outline_plate(f"NG_Channel{sx}", strip, [], [], MAT["red"], col, thick=0.0015, bevel=1.0)
        for v in p.data.vertices:
            v.co.x += sx * 0.0058
        parts.append(p)
    parts.append(H.lathe("NG_RedCord", [(0.30, 0.0168), (0.305, 0.019), (0.335, 0.019), (0.34, 0.0168)], MAT["red"],
                         col))
    return parts


def finish(parts, name, col, base, tip, off_hand=None):
    for p in parts:
        sumi.ensure_uv(p)
    obj = sumi.join(parts, name)
    obj.data.transform(H.WEAPON_FRAME)
    sumi.bake_cavity_to_color(obj)
    H.empty("Socket_BladeBase", (0, base, 0.0), obj, col)
    H.empty("Socket_BladeTip", (0, tip, 0.0), obj, col)
    if off_hand is not None:
        H.empty("Socket_OffHand", (0, off_hand, 0.0), obj, col)
    sumi.log(name, "tris", sumi.tri_count(obj))
    return obj


WEAPONS = {  # id: (builder, object name, trail base, trail tip, off-hand grip)
    "greatsword": (greatsword, "Greatsword", 0.47, 1.80, 0.13),
    "broadsword": (broadsword, "Broadsword", 0.35, 1.42, 0.13),
    "naginata": (naginata, "Naginata", 1.12, 1.70, 0.52),
}


def main():
    """One .blend per weapon so socket empties keep their exact names."""
    objs = []
    for wid, (fn, name, base, tip, off) in WEAPONS.items():
        sumi.reset_scene()
        H.materials()
        MAT["gs_blade"] = sumi.material("M_Greatsword_Blade", rgb=(0.40, 0.12, 0.10), roughness=0.4)
        c = sumi.collection(f"Export_{name}")
        objs.append(finish(fn(c), name, c, base, tip, off_hand=off))
        if "--preview" in ARGS:
            preview(objs[-1], wid)
        sumi.save_blend(sumi.repo_path("assets_src", "weapons", wid, f"{wid}.blend"))


def preview(o, wid):
    if True:
        sumi.setup_preview_render((700, 1300))
        zs = [v.co.z for v in o.data.vertices]
        mid, span = (max(zs) + min(zs)) / 2, max(zs) - min(zs)
        cam = sumi.look_at_camera("Cam", (3.0, 0, mid), (0, 0, mid), ortho_scale=span * 1.05)
        sumi.render_to(os.path.join(PREVIEW_DIR, f"{wid}_sheet.png"), cam)
        bpy.data.objects.remove(cam)


main()
