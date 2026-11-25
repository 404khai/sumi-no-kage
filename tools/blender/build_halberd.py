"""Build the Kurogane halberd (from docs/reference/weapons/halberd.jpeg).

    blender -b --factory-startup --python tools/blender/build_halberd.py [-- --preview]

Output: assets_src/weapons/halberd/halberd.blend

Two-handed polearm on the shared weapon frame (see build_daggers.py):
origin = main-hand grip; authored along +Y (shaft) with the axe edge toward +Z,
then rotated into the Blender export frame (blade +Z, edge -Y) by WEAPON_FRAME.
`Socket_OffHand` marks the second hand's grip for IK.
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
OUT = sumi.repo_path("assets_src", "weapons", "halberd", "halberd.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
WEAPON_FRAME = Matrix.Rotation(math.radians(90), 4, "X")

BUTT, SHAFT_TOP = -0.62, 1.40
OFF_HAND = 0.52
MAT = {}


def materials():
    MAT["steel"] = sumi.material("M_Halberd_Steel", 0.86, roughness=0.3, metallic=0.7)
    MAT["shaft"] = sumi.material("M_Halberd_Shaft", 0.11)
    MAT["wrap"] = sumi.material("M_Halberd_Wrap", 0.05)
    MAT["fittings"] = sumi.material("M_Halberd_Fittings", 0.30, roughness=0.5, metallic=0.5)
    MAT["red"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)


def lathe(name, profile, mat, col, sides=12, wrap=None):
    """profile: [(y, r)], wrap(y, theta) -> radius multiplier."""
    rings = []
    for y, r in profile:
        ring = []
        for i in range(sides):
            th = 2 * math.pi * i / sides
            rr = r * (wrap(y, th) if wrap else 1.0)
            ring.append(Vector((math.cos(th) * rr, y, math.sin(th) * rr)))
        rings.append(ring)
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True, v_scale=3.0)
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=50)
    return obj


def plate(name, y0, y1, z_in, z_out, holes, mat, col, thick=0.009, edge_taper=0.035, ny=40, nz=22):
    """A flat blade in the Y-Z plane between z_in(y) and z_out(y), with holes(y, z) cut out.
    Thickness tapers to a cutting edge along z_out."""
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        a, b = z_in(y), z_out(y)
        grid.append([bm.verts.new((0.0, y, a + (b - a) * i / nz)) for i in range(nz + 1)])
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(ny):
        for i in range(nz):
            q = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
            c = sum((v.co for v in q), Vector()) / 4
            if holes(c.y, c.z) or z_out(c.y) - z_in(c.y) < 0.004:
                continue
            f = bm.faces.new(q)
            for loop, (u, v) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (u / nz, v / ny)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    obj = sumi.mesh_object(name, bm, col)
    sumi.add_modifier(obj, "SOLIDIFY", thickness=thick, offset=0.0, use_even_offset=True)
    sumi.apply_modifiers(obj)
    for v in obj.data.vertices:  # bevel to an edge
        d = abs(z_out(v.co.y) - v.co.z)
        v.co.x *= max(0.08, min(1.0, d / edge_taper))
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=35)
    return obj


def outline_plate(name, outer, holes, edge_poly, mat, col, thick=0.01, bevel=0.06):
    """Flat blade from a 2D outline in the (y, z) plane with holes; the side along
    `edge_poly` is ground to a cutting edge (thickness falls to ~0 there)."""
    bm = bmesh.new()
    loops = []
    for loop in [outer] + holes:
        vs = [bm.verts.new((0.0, y, z)) for y, z in loop]
        es = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
        loops += es
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=loops)
    # scanfill fills holes too: drop faces whose centre lies inside a hole
    def inside(pt, poly):
        y, z = pt
        c = False
        for i in range(len(poly)):
            (y1, z1), (y2, z2) = poly[i], poly[(i + 1) % len(poly)]
            if (z1 > z) != (z2 > z) and y < (y2 - y1) * (z - z1) / (z2 - z1) + y1:
                c = not c
        return c
    kill = [f for f in bm.faces if any(inside((f.calc_center_median().y, f.calc_center_median().z), h)
                                        for h in holes)]
    bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.z * 3, lp.vert.co.y * 3)
    obj = sumi.mesh_object(name, bm, col)
    sumi.add_modifier(obj, "SOLIDIFY", thickness=thick, offset=0.0, use_even_offset=True)
    sumi.apply_modifiers(obj)

    def dist_edge(y, z):
        best = 9.0
        for (y1, z1), (y2, z2) in zip(edge_poly, edge_poly[1:]):
            a, b, p = Vector((y1, z1)), Vector((y2, z2)), Vector((y, z))
            t = max(0.0, min(1.0, (p - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
            best = min(best, (a + (b - a) * t - p).length)
        return best
    for v in obj.data.vertices:
        v.co.x *= max(0.06, min(1.0, dist_edge(v.co.y, v.co.z) / bevel))
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=30)
    return obj


def build(col):
    parts = []
    # shaft: wrapped grips (raised spiral) between bare stretches, iron rings
    def wrap(y, th):
        grip = (-0.12 < y < 0.12) or (OFF_HAND - 0.13 < y < OFF_HAND + 0.13) or (y < -0.30)
        if not grip:
            return 1.0
        phase = (y / 0.045 + th / (2 * math.pi)) % 1.0
        return 1.0 + 0.14 * (1 - abs(phase - 0.5) * 2) ** 2
    prof = [(BUTT + 0.05, 0.0165)] + [(BUTT + 0.05 + (SHAFT_TOP - BUTT - 0.05) * k / 120, 0.0165 - 0.002 * k / 120)
                                     for k in range(1, 121)]
    parts.append(lathe("Shaft", prof, MAT["wrap"], col, sides=12, wrap=wrap))
    for y in (-0.30, -0.13, 0.13, OFF_HAND - 0.14, OFF_HAND + 0.14):
        parts.append(lathe(f"Ring{y:.2f}", [(y - 0.012, 0.019), (y - 0.008, 0.021), (y + 0.008, 0.021),
                                            (y + 0.012, 0.019)], MAT["fittings"], col))
    parts.append(lathe("Ferrule", [(BUTT, 0.010), (BUTT + 0.01, 0.018), (BUTT + 0.07, 0.0185), (BUTT + 0.08, 0.017)],
                       MAT["fittings"], col))
    # socket + langets holding the head
    parts.append(lathe("Socket", [(1.16, 0.0165), (1.18, 0.021), (1.36, 0.022), (1.40, 0.026), (1.42, 0.020)],
                       MAT["fittings"], col, sides=8))
    # top spike: diamond section with a fuller line, tapering to a point
    rings = []
    for k in range(13):
        t = k / 12
        y = 1.41 + 0.32 * t
        w = 0.024 * (1 - t ** 1.6) + 0.0005
        th = 0.010 * (1 - t) + 0.0005
        rings.append([Vector((0, y, w)), Vector((th, y, 0)), Vector((0, y, -w)), Vector((-th, y, 0))])
    bm, grid = sumi.loft(rings, closed=True, cap_start=True)
    tip = bm.verts.new((0, 1.745, 0))
    for i in range(4):
        bm.faces.new((grid[-1][i], grid[-1][(i + 1) % 4], tip))
    sumi.orient_outward(bm)
    spike = sumi.mesh_object("Spike", bm, col)
    spike.data.materials.append(MAT["steel"])
    sumi.shade_smooth(spike, angle_deg=30)
    parts.append(spike)

    # crescent axe blade on +Z, with the triangular window from the reference
    edge = [(1.505, 0.21), (1.47, 0.25), (1.41, 0.284), (1.32, 0.300), (1.22, 0.290), (1.14, 0.262),
            (1.08, 0.218), (1.05, 0.172)]
    outer = [(1.40, 0.016), (1.425, 0.115), (1.465, 0.160)] + edge + [(1.10, 0.155), (1.16, 0.132), (1.20, 0.098),
                                                                     (1.22, 0.016)]
    edge = [tuple(p) for p in sumi.catmull([Vector(e) for e in edge], 5)]
    outer = [(1.40, 0.016), (1.425, 0.115), (1.465, 0.160)] + edge + [(1.10, 0.155), (1.16, 0.132), (1.20, 0.098),
                                                                     (1.22, 0.016)]
    hole = [(1.255, 0.045), (1.365, 0.045), (1.312, 0.138)]
    parts.append(outline_plate("AxeBlade", outer, [hole], edge, MAT["steel"], col, thick=0.010))
    # back fluke: a hook curling down toward the butt, sharpened on its lower edge
    f_edge = [(1.20, -0.215), (1.245, -0.17), (1.27, -0.10), (1.285, -0.016)]
    f_edge = [tuple(p) for p in sumi.catmull([Vector(e) for e in f_edge], 4)]
    f_outer = [(1.345, -0.016), (1.325, -0.09), (1.29, -0.155)] + f_edge
    parts.append(outline_plate("Fluke", f_outer, [], f_edge, MAT["steel"], col, thick=0.009))
    # a vermilion binding below the socket: the weapon's single red accent
    parts.append(lathe("RedBinding", [(1.12, 0.0175), (1.125, 0.0195), (1.155, 0.0195), (1.16, 0.0175)],
                       MAT["red"], col))
    return parts


def empty(name, loc, parent, col):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    e.location = WEAPON_FRAME @ Vector(loc)
    e.rotation_euler = (math.radians(90), 0, 0)
    e.parent = parent
    sumi.link(e, col)


def main():
    sumi.reset_scene()
    materials()
    col = sumi.collection("Export_Halberd")
    parts = build(col)
    for p in parts:
        sumi.ensure_uv(p)
    halberd = sumi.join(parts, "Kurogane_Halberd")
    halberd.data.transform(WEAPON_FRAME)
    sumi.bake_cavity_to_color(halberd)
    empty("Socket_BladeBase", (0, 1.05, 0.0), halberd, col)
    empty("Socket_BladeTip", (0, 1.74, 0.0), halberd, col)
    empty("Socket_OffHand", (0, OFF_HAND, 0.0), halberd, col)
    sumi.log("halberd tris", sumi.tri_count(halberd))
    if "--preview" in ARGS:
        sumi.setup_preview_render((700, 1400))
        cam = sumi.look_at_camera("Cam", (2.6, 0, 0.56), (0, 0, 0.56), ortho_scale=2.5)
        sumi.render_to(os.path.join(PREVIEW_DIR, "halberd_side.png"), cam)
        cam2 = sumi.look_at_camera("Cam2", (0.9, -0.5, 1.45), (0, -0.05, 1.32), lens=50)
        sumi.render_to(os.path.join(PREVIEW_DIR, "halberd_head.png"), cam2)
        sumi.contact_sheet([os.path.join(PREVIEW_DIR, n) for n in ("halberd_side.png", "halberd_head.png")],
                           os.path.join(PREVIEW_DIR, "halberd_sheet.png"))
        for n in ("halberd_side.png", "halberd_head.png"):
            os.remove(os.path.join(PREVIEW_DIR, n))
        for c in (cam, cam2):
            bpy.data.objects.remove(c)
    sumi.save_blend(OUT)


if __name__ == "__main__":
    main()
