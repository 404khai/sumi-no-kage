"""Build the Kagenui (影縫 "shadow-stitch") dual daggers and their saya.

    blender -b --factory-startup --python tools/blender/build_daggers.py [-- --preview]

Output: assets_src/weapons/kagenui_daggers/kagenui_daggers.blend

Weapon frame (shared by every one-handed weapon, matches the rig's *HandWeapon
sockets once in Godot): origin = centre of the grip.
  Godot:   +Y = blade direction (out of the thumb side of a forward grip), +Z = edge
  Blender: +Z = blade direction, -Y = edge   (glTF Y-up conversion maps these onto
           the Godot frame; bone axes are NOT converted, which is why the weapon is
           authored "standing up").
Geometry below is authored along +Y for readability and rotated into the Blender
frame by WEAPON_FRAME at the end. Reverse grip is a stance transform applied in
Godot (WeaponDefinition.grip_mode), not a different mesh.
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
OUT = sumi.repo_path("assets_src", "weapons", "kagenui_daggers", "kagenui_daggers.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))

# Key stations along +Y (metres)
KASHIRA_END = -0.070
TSUKA_START = -0.060
TSUKA_END = 0.054
TSUBA_Y = (0.054, 0.060)
HABAKI = (0.060, 0.080)
BLADE_START = 0.060
BLADE_TIP = 0.292
BLADE_LEN = BLADE_TIP - BLADE_START

MAT = {}
WEAPON_FRAME = Matrix.Rotation(math.radians(90), 4, "X")  # authoring +Y -> Blender +Z, +Z -> -Y


def materials():
    MAT["blade"] = sumi.material("M_Dagger_Blade", 0.82, roughness=0.35, metallic=0.6)
    MAT["wrap"] = sumi.material("M_Dagger_Wrap", 0.07)
    MAT["fittings"] = sumi.material("M_Dagger_Fittings", 0.24, roughness=0.5, metallic=0.4)
    MAT["saya"] = sumi.material("M_Dagger_Saya", 0.045, roughness=0.25)
    MAT["red"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)


def blade_profile(k):
    """k: 0 at the habaki, 1 at the tip -> (spine_z, width, thickness)."""
    sori = 0.0048 * k * k                                 # koshi-zori: tip bends toward the spine
    spine_z = -0.011 - sori
    width = 0.025 - 0.006 * k                             # spine -> edge
    thick = 0.0058 - 0.0028 * k
    # fukura: the edge sweeps up to the spine over the last 22%
    if k > 0.78:
        f = (k - 0.78) / 0.22
        width *= math.sqrt(max(0.0, 1 - f * f)) * 0.98 + 0.0002
        thick *= 1 - 0.85 * f
        spine_z += 0.0035 * f * f
    return spine_z, width, thick


def spine_notch(k):
    """Three back-cut notches on the spine near the base — the family mark shared with
    the naginata reference (docs/reference/naginata.jpg). Returns depth toward the edge."""
    a, b = 0.07, 0.29
    if not (a <= k <= b):
        return 0.0
    f = ((k - a) / (b - a) * 3.0) % 1.0
    return 0.0034 * (1.0 - f) ** 1.5  # sheer wall facing the tip, ramp back toward the hilt


def build_blade(col):
    rings = []
    steps = 96
    for j in range(steps + 1):
        k = j / steps
        y = BLADE_START + BLADE_LEN * k
        zs, w, t = blade_profile(k)
        # hira-zukuri: flat-ish sides that taper to the edge, small mune ridge on the spine
        sec = [
            (0.0, zs - 0.0012),         # mune ridge
            (t / 2, zs + 0.0005),
            (t * 0.47, zs + w * 0.55),   # widest point of the side
            (t * 0.12, zs + w * 0.93),   # edge bevel
            (0.0, zs + w),               # cutting edge (+Z)
            (-t * 0.12, zs + w * 0.93),
            (-t * 0.47, zs + w * 0.55),
            (-t / 2, zs + 0.0005),
        ]
        nd = spine_notch(k)
        for idx in (0, 1, 7):  # spine-side points move toward the edge inside a notch
            x, z = sec[idx]
            sec[idx] = (x * (1 - 0.25 * nd / 0.0034), z + nd)
        rings.append([Vector((x, y, z)) for x, z in sec])
    tip = Vector((0.0, BLADE_TIP + 0.002, rings[-1][4].z - 0.001))
    bm, grid = sumi.loft(rings, closed=True, u_scale=1.0, v_scale=4.0)
    tv = bm.verts.new(tip)
    for i in range(8):
        bm.faces.new((grid[-1][i], grid[-1][(i + 1) % 8], tv))
    bm.faces.new(list(reversed(grid[0])))
    sumi.orient_outward(bm)
    # UV2-style mapping the shader uses for the hamon: u = spine->edge, v = along blade
    uv = bm.loops.layers.uv["UVMap"]
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            k = max(0.0, min(1.0, (co.y - BLADE_START) / BLADE_LEN))
            zs, w, _ = blade_profile(min(k, 0.999))
            loop[uv].uv = ((co.z - zs) / max(w, 1e-4), k)
    obj = sumi.mesh_object("Blade", bm, col)
    obj.data.materials.append(MAT["blade"])
    sumi.shade_smooth(obj, angle_deg=35)
    return obj


def build_habaki(col):
    zs, w, t = blade_profile(0.0)
    rings = []
    for y, grow in ((HABAKI[0], 0.0028), (HABAKI[1] - 0.004, 0.0022), (HABAKI[1], 0.0012)):
        sec = [(0, zs - 0.002 - grow), (t / 2 + grow, zs), (t / 2 + grow * 0.8, zs + w * 0.7),
               (0.0, zs + w * 0.98 + grow * 0.6), (-t / 2 - grow * 0.8, zs + w * 0.7), (-t / 2 - grow, zs)]
        rings.append([Vector((x, y, z)) for x, z in sec])
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True)
    obj = sumi.mesh_object("Habaki", bm, col)
    obj.data.materials.append(MAT["fittings"])
    sumi.shade_smooth(obj, angle_deg=40)
    return obj


def build_tsuba(col):
    """Ink-blot guard: irregular outline like a drop of sumi on washi."""
    n = 48
    rng = sumi.seeded(23)
    phases = [rng.uniform(0, 6.28) for _ in range(3)]

    def r_at(th):
        return 0.024 * (1 + 0.10 * math.sin(3 * th + phases[0]) + 0.06 * math.sin(5 * th + phases[1])
                        + 0.035 * math.sin(9 * th + phases[2]))

    rings = []
    for y, s in ((TSUBA_Y[0], 0.96), (TSUBA_Y[0] + 0.0012, 1.0), (TSUBA_Y[1] - 0.0012, 1.0), (TSUBA_Y[1], 0.96)):
        ring = []
        for i in range(n):
            th = 2 * math.pi * i / n
            r = r_at(th) * s
            ring.append(Vector((math.cos(th) * r * 0.82, y, math.sin(th) * r - 0.001)))
        rings.append(ring)
    bm, grid = sumi.loft(rings, closed=True, cap_start=True, cap_end=True, u_scale=2.0)
    obj = sumi.mesh_object("Tsuba", bm, col)
    obj.data.materials.append(MAT["fittings"])
    sumi.shade_smooth(obj, angle_deg=50)
    return obj


def build_tsuka(col):
    """Oval grip with a raised diamond (hishigami) wrap pattern in the geometry."""
    n, steps = 32, 48
    rings = []
    for j in range(steps + 1):
        k = j / steps
        y = TSUKA_START + (TSUKA_END - TSUKA_START) * k
        ax = 0.0115 * (1 + 0.06 * math.sin(k * math.pi))  # slight waist-to-belly swell
        az = 0.0145 * (1 + 0.06 * math.sin(k * math.pi))
        ring = []
        for i in range(n):
            th = 2 * math.pi * i / n
            u = i / n
            # diamond lattice: two crossing helices of cord
            a = abs(((k * 6 + u * 2) % 1.0) - 0.5)
            b = abs(((k * 6 - u * 2) % 1.0) - 0.5)
            cord = min(1.0, max(0.0, 0.55 - min(a, b) * 2.2) * 2.0)
            r = 1.0 + 0.11 * cord
            ring.append(Vector((math.cos(th) * ax * r, y, math.sin(th) * az * r - 0.001)))
        rings.append(ring)
    bm, _ = sumi.loft(rings, closed=True, u_scale=2.0, v_scale=8.0)
    obj = sumi.mesh_object("Tsuka", bm, col)
    obj.data.materials.append(MAT["wrap"])
    sumi.shade_smooth(obj)
    return obj


def build_kashira(col):
    rings = []
    n = 24
    for y, s in ((TSUKA_START + 0.002, 1.04), (TSUKA_START - 0.002, 1.06), (KASHIRA_END + 0.004, 0.96),
                 (KASHIRA_END + 0.001, 0.70), (KASHIRA_END, 0.30)):
        rings.append([Vector((math.cos(2 * math.pi * i / n) * 0.0118 * s, y,
                              math.sin(2 * math.pi * i / n) * 0.0148 * s - 0.001)) for i in range(n)])
    bm, grid = sumi.loft(rings, closed=True, cap_end=True)
    obj = sumi.mesh_object("Kashira", bm, col)
    obj.data.materials.append(MAT["fittings"])
    sumi.shade_smooth(obj, angle_deg=45)
    return obj


def tube(name, pts, radius, mat, col, sides=8, taper=0.0):
    pts, tans = sumi.polyline_resample(pts, max(10, len(pts)))
    rings = []
    for i, (p, tg) in enumerate(zip(pts, tans)):
        r = radius * (1 - taper * i / (len(pts) - 1))
        rings.append(sumi.ring_around(p, tg, lambda th, r=r: r, sides, up_hint=Vector((1, 0, 0))))
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True, v_scale=6.0)
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj)
    return obj


def build_tassel(col):
    """Vermilion cord loop through the kashira and a short tassel — the accent."""
    parts = []
    c = Vector((0, KASHIRA_END - 0.002, -0.001))
    loop = [c + Vector((math.cos(a) * 0.0055, 0.003 - math.sin(a) * 0.012, 0)) for a in
            [math.pi * i / 10 for i in range(11)]]
    parts.append(tube("TasselLoop", loop, 0.0017, MAT["red"], col))
    knot = c + Vector((0, -0.013, 0))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.0042)
    bmesh.ops.translate(bm, vec=knot, verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    k = sumi.mesh_object("TasselKnot", bm, col)
    k.data.materials.append(MAT["red"])
    sumi.shade_smooth(k)
    parts.append(k)
    for i in range(5):
        a = 2 * math.pi * i / 5
        off = Vector((math.cos(a) * 0.002, 0, math.sin(a) * 0.002))
        pts = [knot + off, knot + off * 1.6 + Vector((0, -0.022, -0.004)),
               knot + off * 2.2 + Vector((0, -0.044, -0.012))]
        parts.append(tube(f"TasselThread{i}", sumi.catmull(pts, 4), 0.0011, MAT["red"], col, sides=5, taper=0.5))
    return parts


def build_saya(col):
    """Lacquered scabbard following the blade, with mouth ring, end cap and red sageo."""
    n, steps = 16, 30
    rings = []
    start, end = TSUBA_Y[1] + 0.001, BLADE_TIP + 0.016
    for j in range(steps + 1):
        k = j / steps
        y = start + (end - start) * k
        kb = min(0.999, max(0.0, (y - BLADE_START) / BLADE_LEN))
        zs, w, t = blade_profile(min(kb, 0.75))
        cz = zs + w * 0.5
        hw, hz = t / 2 + 0.0042, w / 2 + 0.0042
        if k > 0.9:  # rounded kojiri end
            f = (k - 0.9) / 0.1
            s = math.sqrt(max(0.0, 1 - f * f)) * 0.9 + 0.1
            hw *= s
            hz *= s
        ring = []
        for i in range(n):
            th = 2 * math.pi * i / n
            ring.append(Vector((math.cos(th) * hw, y, cz + math.sin(th) * hz)))
        rings.append(ring)
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True, v_scale=4.0)
    saya = sumi.mesh_object("Saya", bm, col)
    saya.data.materials.append(MAT["saya"])
    sumi.shade_smooth(saya)
    parts = [saya]
    # koiguchi (mouth) ring
    zs, w, t = blade_profile(0.0)
    ring_pts = []
    for i in range(17):
        th = 2 * math.pi * i / 16
        ring_pts.append(Vector((math.cos(th) * (t / 2 + 0.0055), start + 0.004, zs + w / 2 + math.sin(th) * (w / 2 + 0.0055))))
    parts.append(tube("Koiguchi", ring_pts, 0.0016, MAT["fittings"], col, sides=6))
    # sageo cord wrapped around the saya near the mouth
    for r_i, y in enumerate((start + 0.030, start + 0.037)):
        pts = []
        for i in range(17):
            th = 2 * math.pi * i / 16
            pts.append(Vector((math.cos(th) * (t / 2 + 0.0058), y, zs + w / 2 + math.sin(th) * (w / 2 + 0.0058))))
        parts.append(tube(f"Sageo{r_i}", pts, 0.0017, MAT["red"], col, sides=6))
    return parts


def empty(name, loc, parent, col):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SINGLE_ARROW"
    e.empty_display_size = 0.03
    e.location = loc
    e.parent = parent
    sumi.link(e, col)
    return e


def main():
    sumi.reset_scene()
    materials()
    dcol = sumi.collection("Export_Dagger")
    scol = sumi.collection("Export_Saya")

    pieces = [build_blade(dcol), build_habaki(dcol), build_tsuba(dcol), build_tsuka(dcol), build_kashira(dcol)]
    pieces += build_tassel(dcol)
    for p in pieces:
        sumi.ensure_uv(p)
    dagger = sumi.join(pieces, "Kagenui_Dagger")
    sumi.bake_cavity_to_color(dagger)
    # VFX sockets: weapon trails sample between these
    empty("Socket_BladeBase", (0, BLADE_START + 0.02, 0.0), dagger, dcol)
    empty("Socket_BladeTip", (0, BLADE_TIP, -0.006), dagger, dcol)

    saya_parts = build_saya(scol)
    for p in saya_parts:
        sumi.ensure_uv(p)
    saya = sumi.join(saya_parts, "Kagenui_Saya")
    sumi.bake_cavity_to_color(saya)

    for obj in (dagger, saya):
        obj.data.transform(WEAPON_FRAME)
    for e in dagger.children:
        e.location = WEAPON_FRAME @ e.location
        e.rotation_euler = (math.radians(90), 0, 0)
    sumi.log("dagger tris", sumi.tri_count(dagger), "saya tris", sumi.tri_count(saya))

    if "--preview" in ARGS:
        sumi.setup_preview_render((1400, 700))
        saya.location = (0, 0.09, 0)
        cam = sumi.look_at_camera("Cam", (0.55, -0.12, 0.05), (0, 0.035, 0.11), lens=60)
        sumi.render_to(os.path.join(PREVIEW_DIR, "daggers_side.png"), cam)
        cam2 = sumi.look_at_camera("Cam2", (0.16, -0.10, -0.12), (0, 0.0, -0.03), lens=60)
        sumi.render_to(os.path.join(PREVIEW_DIR, "daggers_hilt.png"), cam2)
        sumi.contact_sheet([os.path.join(PREVIEW_DIR, "daggers_side.png"),
                            os.path.join(PREVIEW_DIR, "daggers_hilt.png")],
                           os.path.join(PREVIEW_DIR, "daggers_sheet.png"))
        for n in ("daggers_side.png", "daggers_hilt.png"):
            os.remove(os.path.join(PREVIEW_DIR, n))
        for c in (cam, cam2):
            bpy.data.objects.remove(c)
        saya.location = (0, 0, 0)
    sumi.save_blend(OUT)


main()
