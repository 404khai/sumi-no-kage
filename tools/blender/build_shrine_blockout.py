"""Kurogane Shrine — first environment BLOCKOUT.

    blender -b --factory-startup --python tools/blender/build_shrine_blockout.py [-- --preview]

Output: assets_src/environments/kurogane_shrine/kurogane_shrine_blockout.blend

THIS IS BLOCKOUT GEOMETRY. It establishes gameplay scale, routes, sight lines
and the layered-depth composition from docs/environment_kurogane_shrine.md.
It is not final art; every mesh carries the custom property `sumi_status =
"blockout"`, which the validator and the asset register report.

Godot import hints in object names:
  `-col`      -> mesh + generated static collision (trimesh)
  `-colonly`  -> collision only, mesh discarded
  `-convcolonly` -> convex collision only
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
OUT = sumi.repo_path("assets_src", "environments", "kurogane_shrine", "kurogane_shrine_blockout.blend")
PREVIEW_DIR = os.environ.get("SUMI_PREVIEW_DIR", sumi.repo_path("docs", "renders", "wip"))
MAT = {}


def materials():
    MAT["ground"] = sumi.material("M_Env_Ground", 0.78)
    MAT["stone"] = sumi.material("M_Env_Stone", 0.55)
    MAT["wood"] = sumi.material("M_Env_Wood", 0.22)
    MAT["roof"] = sumi.material("M_Env_Roof", 0.12)
    MAT["foliage"] = sumi.material("M_Env_Foliage", 0.16)
    MAT["bamboo"] = sumi.material("M_Env_Bamboo", 0.40)
    MAT["torii"] = sumi.material("M_Ink_AccentRed", rgb=sumi.SHU_RED)
    MAT["cliff"] = sumi.material("M_Env_Cliff", 0.35)


def tag(obj, mat=None, smooth=False):
    obj["sumi_status"] = "blockout"
    if mat is not None:
        obj.data.materials.append(mat)
    if smooth:
        sumi.shade_smooth(obj)
    return obj


def box(name, size, loc, mat, col, rot_z=0.0, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, "Z"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    obj = sumi.mesh_object(name, bm, col)
    if bevel:
        sumi.add_modifier(obj, "BEVEL", width=bevel, segments=1)
        sumi.apply_modifiers(obj)
    return tag(obj, mat)


def cyl(name, r, h, loc, mat, col, segs=12, r_top=None, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r_top is None else r_top,
                          depth=h)
    if rot is not None:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc) + Vector((0, 0, h / 2 if rot is None else 0)), verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    return tag(sumi.mesh_object(name, bm, col), mat)


def terrain(col):
    """Ground plateau with a ravine on the east side and a rising slope to the hall."""
    n = 64
    size = 90.0
    bm = bmesh.new()
    grid = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x = -size / 2 + size * i / n
            y = -size / 2 + size * j / n
            z = 0.0
            # hall terrace rises to the north (+Y in Blender = away from the player's start)
            z += 3.0 * sumi_smooth(11.5, 15.0, y)
            # ravine cutting north-south on the east side
            z -= 14.0 * math.exp(-((x - 22.0) / 4.5) ** 2)
            # gentle broken ground
            z += 0.35 * sumi.fbm(Vector((x * 0.08, y * 0.08, 0.0)))
            # mountains wall the far edges
            edge = max(abs(x), abs(y)) / (size / 2)
            z += 18.0 * sumi_smooth(0.72, 1.0, edge) * (1.0 if x < 15 else 0.4)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / 8.0, b / 8.0)
    obj = sumi.mesh_object("Terrain-col", bm, col)
    tag(obj, MAT["ground"], smooth=True)
    return obj


def sumi_smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def torii(col, loc, rot_z=0.0, scale=1.0):
    """Ryōbu-style gate silhouette — the one strong red mark in the courtyard."""
    parts = []
    s = scale
    for sx in (-1, 1):
        parts.append(cyl(f"ToriiPillar{sx}", 0.22 * s, 5.2 * s, (sx * 2.2 * s, 0, 0), MAT["torii"], col, r_top=0.19 * s))
    kasagi = box("ToriiKasagi", (6.4 * s, 0.45 * s, 0.38 * s), (0, 0, 5.25 * s), MAT["roof"], col)
    # upswept ends of the top beam (sori)
    for v in kasagi.data.vertices:
        v.co.z += 0.18 * s * (abs(v.co.x) / (3.2 * s)) ** 3
    parts.append(kasagi)
    parts.append(box("ToriiShimaki", (5.9 * s, 0.38 * s, 0.22 * s), (0, 0, 4.92 * s), MAT["torii"], col))
    parts.append(box("ToriiNuki", (5.4 * s, 0.22 * s, 0.30 * s), (0, 0, 4.05 * s), MAT["torii"], col))
    parts.append(box("ToriiGakuzuka", (0.26 * s, 0.18 * s, 0.75 * s), (0, 0, 4.48 * s), MAT["torii"], col))
    gate = sumi.join(parts, "Torii-col")
    gate.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(rot_z, 4, "Z")
    sumi.apply_transforms(gate)
    return tag(gate)


def stone_lantern(col, name, loc):
    parts = [
        cyl(name + "_base", 0.35, 0.25, (0, 0, 0), MAT["stone"], col, segs=6),
        cyl(name + "_post", 0.14, 0.95, (0, 0, 0.25), MAT["stone"], col, segs=8),
        box(name + "_light", (0.55, 0.55, 0.42), (0, 0, 1.41), MAT["stone"], col),
        cyl(name + "_roof", 0.55, 0.32, (0, 0, 1.62), MAT["stone"], col, segs=6, r_top=0.08),
    ]
    lantern = sumi.join(parts, name + "-convcol")
    lantern.location = loc
    sumi.apply_transforms(lantern)
    return tag(lantern)


def shrine_hall(col, loc):
    """Main hall (haiden) massing: raised floor, posts, heavy curved roof."""
    parts = [box("HallPlatform", (12.0, 9.0, 1.1), (0, 0, 0.55), MAT["stone"], col)]
    for sx in (-5.2, -1.75, 1.75, 5.2):
        for sy in (-3.8, 3.8):
            parts.append(cyl("HallPost", 0.22, 3.6, (sx, sy, 1.1), MAT["wood"], col, segs=8))
    parts.append(box("HallWalls", (9.0, 6.4, 3.2), (0, 0.4, 2.7), MAT["wood"], col))
    # irimoya-style roof: a wide slab whose eaves sweep upward at the corners
    roof = box("HallRoof", (15.5, 12.0, 1.0), (0, 0, 5.4), MAT["roof"], col)
    bm = bmesh.new()
    bm.from_mesh(roof.data)
    for v in bm.verts:
        cx, cy = v.co.x / 7.75, (v.co.y) / 6.0
        if v.co.z > 5.4:
            v.co.x *= 0.62
            v.co.y *= 0.30
            v.co.z += 2.0
        v.co.z += 0.9 * (abs(cx) ** 4 + abs(cy) ** 4) * 0.5  # corner upsweep
    bm.to_mesh(roof.data)
    bm.free()
    parts.append(roof)
    # steps up to the platform
    for k in range(5):
        parts.append(box("HallStep", (3.6, 0.45, 0.22 * (k + 1)), (0, -4.5 - 0.45 * (5 - k) + 0.22, 0.11 * (k + 1)),
                         MAT["stone"], col))
    hall = sumi.join(parts, "ShrineHall-col")
    hall.location = loc
    sumi.apply_transforms(hall)
    return tag(hall)


def stairs(col, start, count, step=(4.0, 0.42, 0.20), name="StoneStairs"):
    parts = []
    for k in range(count):
        parts.append(box(f"{name}{k}", (step[0], step[1], step[2] * (k + 1)),
                         (start[0], start[1] + step[1] * k, start[2] + step[2] * (k + 1) / 2), MAT["stone"], col))
    obj = sumi.join(parts, name + "-col")
    return tag(obj)


def bridge(col, a, b, width=2.2):
    d = (b - a)
    L = d.length
    ang = math.atan2(d.y, d.x)
    parts = []
    deck = box("BridgeDeck", (L, width, 0.25), (0, 0, 0), MAT["wood"], col)
    for v in deck.data.vertices:  # arched deck (taikobashi)
        v.co.z += 1.2 * (1 - (2 * v.co.x / L) ** 2)
    parts.append(deck)
    for sy in (-1, 1):
        rail = box("BridgeRail", (L, 0.12, 0.10), (0, sy * (width / 2 - 0.06), 0.95), MAT["torii"], col)
        for v in rail.data.vertices:
            v.co.z += 1.2 * (1 - (2 * v.co.x / L) ** 2)
        parts.append(rail)
        for k in range(7):
            x = -L / 2 + L * k / 6
            h = 1.2 * (1 - (2 * x / L) ** 2)
            parts.append(box("BridgePost", (0.14, 0.14, 0.95), (x, sy * (width / 2 - 0.06), h + 0.47), MAT["wood"], col))
    obj = sumi.join(parts, "Bridge-col")
    obj.matrix_world = Matrix.Translation((a + b) / 2) @ Matrix.Rotation(ang, 4, "Z")
    sumi.apply_transforms(obj)
    return tag(obj)


def pine(col, name, loc, height, lean, seed):
    """Ink-painting pine: leaning twisted trunk with flat cloud-pads of needles."""
    rng = sumi.seeded(seed)
    pts = [Vector(loc)]
    d = Vector((lean[0], lean[1], 1.0)).normalized()
    for k in range(6):
        d = (d + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.15))).normalized()
        pts.append(pts[-1] + d * height / 6)
    pts_s, tans = sumi.polyline_resample(sumi.catmull(pts, 4), 18)
    rings = []
    for i, (p, t) in enumerate(zip(pts_s, tans)):
        r = 0.42 * (1 - 0.7 * i / 17) * height / 9
        rings.append(sumi.ring_around(p, t, lambda th, r=r: r * (1 + 0.12 * math.sin(3 * th + i)), 8))
    bm, _ = sumi.loft(rings, closed=True, cap_start=True, cap_end=True)
    trunk = tag(sumi.mesh_object(name + "_trunk", bm, col), MAT["wood"], smooth=True)
    pads = []
    for k in range(8):
        base = pts_s[rng.randint(7, 17)]
        off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * rng.uniform(0.6, 2.2) * height / 9
        c = base + off + Vector((0, 0, rng.uniform(-0.2, 0.6)))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=1.0)
        sx = rng.uniform(0.9, 1.6) * height / 9
        bmesh.ops.scale(bm, vec=(sx, sx * rng.uniform(0.6, 0.9), 0.42 * height / 9), verts=bm.verts)
        for v in bm.verts:
            if v.co.z < 0:
                v.co.z *= 0.35  # flat underside like a brush-pressed pad
        bmesh.ops.translate(bm, vec=c, verts=bm.verts)
        bm.loops.layers.uv.new("UVMap")
        pads.append(tag(sumi.mesh_object(f"{name}_pad{k}", bm, col), MAT["foliage"], smooth=True))
    tree = sumi.join([trunk, *pads], name)
    return tag(tree)


def bamboo_grove(col, center, radius, count, seed):
    rng = sumi.seeded(seed)
    parts = []
    for k in range(count):
        a = rng.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rng.random())
        p = Vector(center) + Vector((math.cos(a) * r, math.sin(a) * r, -0.2))
        h = rng.uniform(7, 11)
        tilt = Matrix.Rotation(rng.uniform(-0.08, 0.08), 3, "X") @ Matrix.Rotation(rng.uniform(-0.08, 0.08), 3, "Y")
        parts.append(cyl(f"Bamboo{k}", rng.uniform(0.05, 0.09), h, p, MAT["bamboo"], col, segs=6, rot=tilt.to_4x4()))
        parts[-1].location = (0, 0, 0)
    grove = sumi.join(parts, "BambooGrove")
    return tag(grove)


def collision_volumes(col):
    """Invisible blockers: the ravine edge and the play-space boundary."""
    out = []
    out.append(box("RavineFence-colonly", (0.5, 60.0, 3.0), (17.5, 0, 1.0), None, col))
    for name, size, loc in (("BoundN-colonly", (80, 1, 12), (0, 38, 6)), ("BoundS-colonly", (80, 1, 12), (0, -38, 6)),
                            ("BoundW-colonly", (1, 80, 12), (-38, 0, 6)), ("BoundE-colonly", (1, 80, 12), (38, 0, 6))):
        out.append(box(name, size, loc, None, col))
    return out


def spawn_markers(col):
    """Empties exported as Node3D markers for gameplay hookup (player start, enemy posts)."""
    out = []
    for name, loc in (("Marker_PlayerStart", (0, -26, 0.2)), ("Marker_Patrol_A", (-8, 4, 0.2)),
                      ("Marker_Patrol_B", (6, 8, 0.2)), ("Marker_Sentry_Hall", (0, 16.2, 3.2)),
                      ("Marker_Ambush_Bridge", (22, -6, 1.6)), ("Marker_Camera_Concept", (-9, -31, 4.6))):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.location = loc
        e["sumi_status"] = "blockout"
        sumi.link(e, col)
        out.append(e)
    return out


def main():
    sumi.reset_scene()
    materials()
    col = sumi.collection("Export_ShrineBlockout")
    terrain(col)
    torii(col, Vector((0, -16, 0.0)))
    stairs(col, (0, 9.1, 0.0), 14, step=(4.0, 0.42, 0.215))
    shrine_hall(col, Vector((0, 21.0, 3.0)))
    for i, (x, y) in enumerate(((-3.5, -10), (3.5, -10), (-3.5, 2), (3.5, 2), (-3.2, 16.5), (3.2, 16.5))):
        z = 3.0 if y > 12 else 0.0
        stone_lantern(col, f"Lantern{i}", Vector((x, y, z)))
    # stepping-stone path from the gate to the stairs
    rng = sumi.seeded(5)
    path = []
    for k in range(16):
        y = -24 + k * 2.0
        x = 0.6 * math.sin(k * 0.7)
        path.append(box(f"PathStone{k}", (rng.uniform(1.4, 1.9), rng.uniform(0.9, 1.3), 0.25), (x, y, 0.02),
                        MAT["stone"], col, rot_z=rng.uniform(-0.3, 0.3)))
    tag(sumi.join(path, "PathStones-col"))
    bridge(col, Vector((16.0, -6.0, 0.0)), Vector((28.0, -6.0, 0.0)))
    pine(col, "PineGateWest-col", (-7.0, -17.5, 0.0), 9.0, (0.45, 0.1), 3)
    pine(col, "PineHallEast-col", (9.0, 16.0, 3.0), 11.0, (-0.25, 0.3), 9)
    pine(col, "PineRavine-col", (18.5, -14.0, 0.0), 8.0, (0.7, -0.2), 21)
    bamboo_grove(col, (-14.0, 4.0, 0.0), 6.0, 60, 4)
    # cliff massing behind the hall, the backdrop for the layered ink-wash mountains
    for k, (x, w, h) in enumerate(((-18, 14, 22), (-2, 18, 30), (16, 12, 24))):
        c = box(f"Cliff{k}", (w, 6, h), (x, 34, h / 2 - 1), MAT["cliff"], col, rot_z=0.15 * (k - 1))
        c.name = f"Cliff{k}-col"
    collision_volumes(col)
    spawn_markers(col)
    meshes = [o for o in col.objects if o.type == "MESH"]
    for o in meshes:
        sumi.ensure_uv(o)
        if not o.name.endswith("-colonly"):
            sumi.bake_cavity_to_color(o, blur=1)
    sumi.log("blockout objects", len(meshes), "tris", sum(sumi.tri_count(o) for o in meshes))

    if "--preview" in ARGS:
        sumi.setup_preview_render((1600, 900))
        for o in meshes:
            if o.name.endswith("-colonly"):
                o.hide_render = True
        cam = sumi.look_at_camera("Concept", (-9, -31, 4.6), (2, 10, 4), lens=28)
        sumi.render_to(os.path.join(PREVIEW_DIR, "shrine_blockout_concept_cam.png"), cam)
        top = sumi.look_at_camera("Top", (0, 0, 120), (0, 0.01, 0), ortho_scale=92)
        sumi.render_to(os.path.join(PREVIEW_DIR, "shrine_blockout_top.png"), top)
        for c in (cam, top):
            bpy.data.objects.remove(c)
        for o in meshes:
            o.hide_render = False
    sumi.save_blend(OUT)


main()
