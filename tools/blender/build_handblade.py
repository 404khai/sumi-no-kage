"""Build the Kuzuri handblade, a katar-style punch dagger (docs/reference/weapons/handblade.png).

    blender -b --factory-startup --python tools/blender/build_handblade.py [-- --preview]

Output: assets_src/weapons/handblade/handblade.blend

Held like a saw handle turned sideways: the grip bar runs *through* the fist
(socket +Y) and the blade protrudes past the knuckles (socket +Z, Godot frame).
Authored on the shared weapon frame (see build_daggers.py), then rotated by
WEAPON_FRAME. Materials are shared with the halberd (M_Halberd_*).
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import sumi  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = sumi.repo_path("assets_src", "weapons", "handblade", "handblade.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
WEAPON_FRAME = Matrix.Rotation(math.radians(90), 4, "X")
MAT = {}

BAR_HALF = 0.052     # grip bar half-length (through the fist)
FRAME_START = -0.035  # side bars run back along the forearm a little
GUARD = 0.075        # knuckle guard plate (blade root)
TIP = 0.47


def materials():
    MAT["steel"] = sumi.material("M_Halberd_Steel", 0.86, roughness=0.3, metallic=0.7)
    MAT["wrap"] = sumi.material("M_Halberd_Wrap", 0.05)
    MAT["fittings"] = sumi.material("M_Halberd_Fittings", 0.30)
    MAT["red"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)


def loft_obj(name, rings, mat, col, caps=True, tip=None, smooth=35):
    bm, grid = sumi.loft(rings, closed=True, cap_start=caps, cap_end=caps and tip is None)
    if tip is not None:
        tv = bm.verts.new(tip)
        n = len(grid[-1])
        for i in range(n):
            bm.faces.new((grid[-1][i], grid[-1][(i + 1) % n], tv))
    sumi.orient_outward(bm)
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=smooth)
    return obj


def build(col):
    parts = []
    # blade along +Z: long diamond section with a raised spine ridge, tapering to a needle point
    rings = []
    for k in range(25):
        t = k / 24
        z = GUARD + (TIP - GUARD) * t
        w = 0.024 * (1 - t ** 1.35) + 0.0008         # half-width across the flat (Y)
        th = 0.0055 * (1 - 0.8 * t) + 0.0006          # half-thickness (X)
        rings.append([Vector((0, w, z)), Vector((th * 0.5, w * 0.5, z)), Vector((th, 0, z)),
                      Vector((th * 0.5, -w * 0.5, z)), Vector((0, -w, z)), Vector((-th * 0.5, -w * 0.5, z)),
                      Vector((-th, 0, z)), Vector((-th * 0.5, w * 0.5, z))])
    parts.append(loft_obj("Blade", rings, MAT["steel"], col, tip=Vector((0, 0, TIP + 0.012)), smooth=30))
    # knuckle guard: a thick plate the blade grows from, flaring into the side bars
    g = []
    for z, w, th in ((GUARD - 0.022, BAR_HALF + 0.012, 0.010), (GUARD - 0.008, BAR_HALF + 0.010, 0.012),
                     (GUARD, 0.034, 0.009), (GUARD + 0.012, 0.026, 0.006)):
        g.append([Vector((th, w, z)), Vector((-th, w, z)), Vector((-th, -w, z)), Vector((th, -w, z))])
    parts.append(loft_obj("Guard", g, MAT["fittings"], col, smooth=20))
    # side bars, running back along the forearm (the saw-handle frame)
    for s in (1, -1):
        y = s * (BAR_HALF + 0.008)
        prof = [Vector((0, y, z)) for z in (FRAME_START, FRAME_START + 0.02, GUARD - 0.02)]
        bar = []
        for p in prof:
            bar.append([p + Vector((0.009, 0.004, 0)), p + Vector((-0.009, 0.004, 0)), p + Vector((-0.009, -0.004, 0)),
                        p + Vector((0.009, -0.004, 0))])
        # taper the trailing end into a point along the forearm
        for v in bar[0]:
            v.x *= 0.4
        parts.append(loft_obj(f"SideBar{s}", bar, MAT["fittings"], col, smooth=20))
    # the grip bar through the fist, wrapped, with a vermilion binding at its centre
    def grip_ring(y, r):
        return [Vector((math.cos(a) * r, y, math.sin(a) * r)) for a in [2 * math.pi * i / 12 for i in range(12)]]
    wrap = []
    for k in range(31):
        y = -BAR_HALF + 2 * BAR_HALF * k / 30
        r = 0.0135 * (1 + 0.10 * (1 - abs(((y / 0.012) % 1.0) - 0.5) * 2) ** 2)
        wrap.append(grip_ring(y, r))
    parts.append(loft_obj("Grip", wrap, MAT["wrap"], col, smooth=60))
    parts.append(loft_obj("Binding", [grip_ring(-0.006, 0.0150), grip_ring(-0.004, 0.0158), grip_ring(0.004, 0.0158),
                                      grip_ring(0.006, 0.0150)], MAT["red"], col, smooth=60))
    return parts


def empty(name, loc, parent, col):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.04
    e.location = WEAPON_FRAME @ Vector(loc)
    e.rotation_euler = (math.radians(90), 0, 0)
    e.parent = parent
    sumi.link(e, col)


def main():
    sumi.reset_scene()
    materials()
    col = sumi.collection("Export_Handblade")
    parts = build(col)
    for p in parts:
        sumi.ensure_uv(p)
    hb = sumi.join(parts, "Kuzuri_Handblade")
    hb.data.transform(WEAPON_FRAME)
    sumi.bake_cavity_to_color(hb)
    empty("Socket_BladeBase", (0, 0, GUARD + 0.02), hb, col)
    empty("Socket_BladeTip", (0, 0, TIP), hb, col)
    sumi.log("handblade tris", sumi.tri_count(hb))
    if "--preview" in ARGS:
        sumi.setup_preview_render((1400, 700))
        # Blender frame after rotation: blade along -Y, grip bar along +Z
        cam = sumi.look_at_camera("Cam", (0.75, -0.22, 0.30), (0, -0.21, 0.0), lens=40)
        sumi.render_to(os.path.join(PREVIEW_DIR, "handblade_sheet.png"), cam)
        bpy.data.objects.remove(cam)
    sumi.save_blend(OUT)


main()
