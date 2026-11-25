"""Build the katana and its saya (docs/reference/weapons/katana.jpeg).

    blender -b --factory-startup --python tools/blender/build_katana.py [-- --preview]

Output: assets_src/weapons/katana/katana.blend with collections Export_Katana and
Export_KatanaSaya (one glb each, like the daggers and their saya).

Shared weapon frame (build_daggers.py): origin = main-hand grip, authored along +Y
with the edge toward +Z, rotated by WEAPON_FRAME. The katana plays the two-handed
sword moveset (Greatsword family), whose clips put the off hand 0.13 m up the grip,
so the main hand sits low on the tsuka and the off hand under the tsuba.

Reference -> ink: white lacquer saya and white same stay pale paper tones, black
ito wrap stays sumi, the gold fittings become a warm tan bronze (the only warm
tone on the weapon), the blade is pale steel with a darker hamon band.
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
OUT = sumi.repo_path("assets_src", "weapons", "katana", "katana.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
M = {}

# stations along +Y (metres)
KASHIRA = (-0.125, -0.105)
TSUKA = (-0.105, 0.165)
TSUBA = (0.165, 0.175)
HABAKI = (0.175, 0.205)
BLADE = (0.175, 0.905)
SORI = 0.022          # curvature depth at the middle of the blade


def materials():
    M["steel"] = sumi.material("M_Katana_Blade", 0.84, roughness=0.3, metallic=0.7)
    M["hamon"] = sumi.material("M_Katana_Hamon", 0.95, roughness=0.25, metallic=0.6)
    M["ito"] = sumi.material("M_Katana_Ito", 0.07)
    M["same"] = sumi.material("M_Katana_Same", 0.90)
    M["fittings"] = sumi.material("M_Katana_Fittings", rgb=(0.58, 0.45, 0.28), roughness=0.5, metallic=0.5)
    M["saya"] = sumi.material("M_Katana_Saya", 0.88, roughness=0.35)
    M["band"] = sumi.material("M_Katana_Band", 0.06)


def curve_z(y):
    """Back-to-edge offset of the blade's centre line: a torii-zori arc over the blade."""
    if y <= BLADE[0]:
        return 0.0
    t = (y - BLADE[0]) / (BLADE[1] - BLADE[0])
    return -SORI * 4 * t * (1 - t) - SORI * 0.6 * t * t   # bows back, tip lifts slightly


def blade():
    """Shinogi-zukuri section (ridge line, flat ji, sharp ha) with a kissaki."""
    rings_steel, rings_hamon = [], []
    steps = 60
    y0, y1 = BLADE
    for k in range(steps + 1):
        t = k / steps
        y = y0 + (y1 - y0) * t
        z0 = curve_z(y)
        w = 0.0165 - 0.0045 * t                       # half width (mune to ha)
        th = 0.0036 - 0.0012 * t                      # half thickness at the shinogi
        if t > 0.9:                                   # kissaki: the edge sweeps up to the point
            u = (t - 0.9) / 0.1
            w *= math.sqrt(max(1 - u * u, 0.0)) * 0.9 + 0.1 * (1 - u)
            th *= 1 - 0.8 * u
        mune, shinogi, ha = z0 - w, z0 + w * 0.15, z0 + w
        hamon = z0 + w * (0.55 + 0.08 * math.sin(t * 38))   # wavy temper line
        rings_steel.append([Vector((0, y, mune)), Vector((th * 0.7, y, mune + 0.002)), Vector((th, y, shinogi)),
                            Vector((th * 0.55, y, hamon)), Vector((-th * 0.55, y, hamon)),
                            Vector((-th, y, shinogi)), Vector((-th * 0.7, y, mune + 0.002))])
        rings_hamon.append([Vector((th * 0.55, y, hamon)), Vector((0, y, ha)), Vector((-th * 0.55, y, hamon))])
    parts = []
    for name, rings, mat in (("Katana_Ji", rings_steel, M["steel"]), ("Katana_Ha", rings_hamon, M["hamon"])):
        bm, grid = sumi.loft(rings, closed=(name == "Katana_Ji"), cap_start=True)
        tip = bm.verts.new(Vector((0, y1 + 0.004, curve_z(y1) + 0.002)))
        n = len(rings[-1])
        for i in range(n if name == "Katana_Ji" else n - 1):
            bm.faces.new((grid[-1][i], grid[-1][(i + 1) % n], tip))
        sumi.orient_outward(bm)
        obj = sumi.mesh_object(name, bm, None)
        obj.data.materials.append(mat)
        sumi.shade_smooth(obj, angle_deg=28)
        parts.append(obj)
    return parts


def helix(name, y0, y1, r, turns, phase, hand, mat, width=0.006):
    """Flat cord spiralling around the grip; two opposite helices cross into the
    diamond (hishigami) pattern of tsuka-ito."""
    rings = []
    n = 160
    for k in range(n + 1):
        t = k / n
        y = y0 + (y1 - y0) * t
        a = phase + hand * 2 * math.pi * turns * t
        c = Vector((math.cos(a) * r, y, math.sin(a) * r * 0.82))   # oval tsuka
        out = Vector((math.cos(a), 0, math.sin(a) * 0.82)).normalized()
        side = Vector((0, 1, 0)) * width
        rings.append([c - side, c + out * 0.0025 - side * 0.3, c + out * 0.0025 + side * 0.3, c + side,
                      c - out * 0.001])
    bm, _ = sumi.loft(rings, closed=True)
    obj = sumi.mesh_object(name, bm, None)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=60)
    return obj


def oval_lathe(name, profile, mat, sides=16, squash=0.82, bend=False):
    rings = []
    for y, r in profile:
        z0 = curve_z(y) if bend else 0.0
        rings.append([Vector((math.cos(2 * math.pi * i / sides) * r, y,
                              z0 + math.sin(2 * math.pi * i / sides) * r * squash)) for i in range(sides)])
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True, v_scale=3.0)
    obj = sumi.mesh_object(name, bm, None)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj, angle_deg=50)
    return obj


def katana():
    parts = blade()
    parts.append(oval_lathe("Habaki", [(HABAKI[0], 0.0095), (HABAKI[1] - 0.004, 0.0085), (HABAKI[1], 0.006)],
                            M["fittings"], squash=1.9))
    # tsuba: round guard with a raised rim, eight openwork notches suggested by scallops
    prof, rim = [], 0.040
    for i in range(48):
        a = 2 * math.pi * i / 48
        prof.append(rim * (1 - 0.06 * max(0.0, math.cos(8 * a)) ** 6))
    bm = bmesh.new()
    top, bot = [], []
    for i, r in enumerate(prof):
        a = 2 * math.pi * i / 48
        top.append(bm.verts.new((math.cos(a) * r, TSUBA[1], math.sin(a) * r)))
        bot.append(bm.verts.new((math.cos(a) * r, TSUBA[0], math.sin(a) * r)))
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(48):
        j = (i + 1) % 48
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    sumi.orient_outward(bm)
    bm.loops.layers.uv.new("UVMap")
    tsuba = sumi.mesh_object("Tsuba", bm, None)
    tsuba.data.materials.append(M["fittings"])
    parts.append(tsuba)
    parts.append(oval_lathe("Fuchi", [(TSUKA[1] - 0.018, 0.0150), (TSUKA[1], 0.0160)], M["fittings"]))
    parts.append(oval_lathe("Same", [(TSUKA[0], 0.0140), ((TSUKA[0] + TSUKA[1]) / 2, 0.0148),
                                     (TSUKA[1] - 0.018, 0.0142)], M["same"]))
    for hand in (1, -1):
        parts.append(helix(f"Ito_{hand}", TSUKA[0] + 0.004, TSUKA[1] - 0.02, 0.0150, 5.5, 0.0, hand, M["ito"]))
    parts.append(oval_lathe("Kashira", [(KASHIRA[0], 0.010), (KASHIRA[0] + 0.004, 0.0145),
                                        (KASHIRA[1], 0.0152)], M["fittings"]))
    return parts


def saya():
    """White lacquer scabbard following the blade's curve, black kurikata band, tan kojiri."""
    prof = []
    y0, y1 = TSUBA[1] + 0.002, BLADE[1] + 0.03
    for k in range(41):
        t = k / 40
        prof.append((y0 + (y1 - y0) * t, 0.0150 - 0.003 * t))
    parts = [oval_lathe("Saya", prof, M["saya"], squash=1.75, bend=True)]
    parts.append(oval_lathe("Koiguchi", [(y0, 0.0160), (y0 + 0.012, 0.0160)], M["fittings"], squash=1.75, bend=True))
    yb = y0 + 0.13
    parts.append(oval_lathe("Kurikata", [(yb, 0.0161), (yb + 0.035, 0.0161)], M["band"], squash=1.8, bend=True))
    parts.append(oval_lathe("Kojiri", [(y1 - 0.055, 0.0124), (y1 - 0.004, 0.0122), (y1, 0.009)], M["fittings"],
                            squash=1.75, bend=True))
    return parts


def finish(parts, name, col, sockets):
    for p in parts:
        sumi.ensure_uv(p)
    obj = sumi.join(parts, name)
    obj.data.transform(H.WEAPON_FRAME)
    sumi.bake_cavity_to_color(obj)
    for sname, y in sockets:
        H.empty(sname, (0, y, curve_z(y)), obj, col)
    sumi.log(name, "tris", sumi.tri_count(obj))
    return obj


def move_to(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def preview(objs):
    sumi.setup_preview_render((1600, 700))
    # lay both pieces out side by side, like the reference sheet
    for o, x in zip(objs, (0.08, -0.08)):
        o.location.y = x
    cam = sumi.look_at_camera("Cam", (2.4, 0, 0.40), (0, 0, 0.40), ortho_scale=1.15)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 700, 1500
    sumi.render_to(os.path.join(PREVIEW_DIR, "katana_sheet.png"), cam)
    bpy.data.objects.remove(cam)
    for o in objs:
        o.location.y = 0


def main():
    sumi.reset_scene()
    materials()
    kc = sumi.collection("Export_Katana")
    sc = sumi.collection("Export_KatanaSaya")
    k = katana()
    for p in k:
        move_to(p, kc)
    kat = finish(k, "Katana", kc, [("Socket_BladeBase", 0.26), ("Socket_BladeTip", 0.89), ("Socket_OffHand", 0.13)])
    s = saya()
    for p in s:
        move_to(p, sc)
    sy = finish(s, "Katana_Saya", sc, [])
    if "--preview" in ARGS:
        preview([kat, sy])
    sumi.save_blend(OUT)


main()
