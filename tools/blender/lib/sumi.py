"""Shared helpers for the Sumi no Kage procedural asset scripts.

All asset scripts run inside Blender in background mode, e.g.

    blender -b --factory-startup --python tools/blender/build_kage.py

Conventions (see docs/asset_pipeline.md):
  * Blender units are metres, Z up, characters face -Y.
  * glTF export converts to Godot's Y-up / +Z model-front automatically.
  * Material names are the contract with Godot: `M_<Asset>_<Part>` maps to
    `res://materials/<name>.tres` in the post-import script.
"""

from __future__ import annotations

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# --------------------------------------------------------------------------
# Palette — the five ink tones of sumi-e plus paper and vermilion.
# Values are *display* (sRGB) greys; see docs/art_bible.md.
# --------------------------------------------------------------------------
INK_TONES = {
    "sho": 0.035,   # 焦 burnt ink, deepest black
    "no": 0.10,     # 濃 thick ink
    "ju": 0.22,     # 重 heavy ink
    "tan": 0.52,    # 淡 light ink
    "sei": 0.80,    # 清 clear ink
    "paper": 0.92,  # washi paper
}
SHU_RED = (0.62, 0.11, 0.08)  # 朱 vermilion accent (sRGB)


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def log(*args):
    print("[sumi]", *args)
    sys.stdout.flush()


def repo_path(*parts) -> str:
    return os.path.join(REPO_ROOT, *parts)


# --------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 30
    return scene


def collection(name: str, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in parent.children:
        parent.children.link(col)
    return col


def link(obj, col=None):
    (col or bpy.context.scene.collection).objects.link(obj)
    return obj


def save_blend(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    # Blender leaves a .blend1 backup next to the file; we keep sources in VCS.
    bak = path + "1"
    if os.path.exists(bak):
        os.remove(bak)
    log("saved", os.path.relpath(path, REPO_ROOT))


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------
def material(name: str, tone=None, rgb=None, roughness=0.9, metallic=0.0):
    """Preview material. Godot replaces it with the ink material of the same name."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if rgb is None:
        rgb = (tone, tone, tone)
    lin = tuple(srgb_to_linear(c) for c in rgb)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*lin, 1.0)  # workbench / viewport colour
    mat["sumi_tone"] = rgb[0] if tone is None else tone
    return mat


def assign_material(obj, mat, face_filter=None):
    mats = obj.data.materials
    if mat.name not in [m.name for m in mats if m]:
        mats.append(mat)
    idx = [m.name for m in mats].index(mat.name)
    if face_filter is not None:
        for poly in obj.data.polygons:
            if face_filter(poly):
                poly.material_index = idx
    return idx


# --------------------------------------------------------------------------
# Mesh construction
# --------------------------------------------------------------------------
def mesh_object(name: str, bm: bmesh.types.BMesh, col=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    link(obj, col)
    return obj


def loft(rings, closed=True, cap_start=False, cap_end=False, u_scale=1.0, v_scale=1.0,
         bm=None, uv_name="UVMap"):
    """Bridge a list of equal-length point rings into a quad surface with UVs.

    u runs around each ring (0..1 * u_scale), v runs along the ring list.
    Returns (bm, verts_grid).
    """
    own = bm is None
    bm = bm or bmesh.new()
    uv = bm.loops.layers.uv.get(uv_name) or bm.loops.layers.uv.new(uv_name)
    n = len(rings[0])
    grid = [[bm.verts.new(p) for p in ring] for ring in rings]
    # accumulate v by actual arc length so textures don't stretch
    vlen = [0.0]
    for j in range(1, len(rings)):
        d = sum((Vector(rings[j][i]) - Vector(rings[j - 1][i])).length for i in range(n)) / n
        vlen.append(vlen[-1] + d)
    total = vlen[-1] or 1.0
    cols = n if closed else n - 1
    for j in range(len(rings) - 1):
        for i in range(cols):
            i2 = (i + 1) % n
            f = bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
            u0 = i / cols * u_scale
            u1 = (i + 1) / cols * u_scale
            v0 = vlen[j] * v_scale
            v1 = vlen[j + 1] * v_scale
            for loop, (u, v) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                loop[uv].uv = (u, v)
    if cap_start and closed:
        f = bm.faces.new(list(reversed(grid[0])))
        _planar_uv(f, uv)
    if cap_end and closed:
        f = bm.faces.new(grid[-1])
        _planar_uv(f, uv)
    if closed:
        orient_outward(bm)
    bm.normal_update()
    return bm, grid


def orient_outward(bm):
    """Make winding consistent and outward-facing.

    Back-face culling and inverted-hull outlines in Godot depend on this, and
    Blender's workbench preview would never show the problem.
    """
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if not bm.faces:
        return
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    # recalc can still pick "all inward" on open tubes; vote by area against the centroid
    score = sum(f.normal.dot(f.calc_center_median() - c) * f.calc_area() for f in bm.faces)
    if score < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()


def _planar_uv(face, uv):
    c = face.calc_center_median()
    for loop in face.loops:
        d = loop.vert.co - c
        loop[uv].uv = (0.5 + d.x * 2, 0.5 + d.y * 2)


def frame_from_dir(direction: Vector, up_hint=Vector((0, 0, 1))):
    """Orthonormal (tangent, bitangent, direction) frame around `direction`."""
    d = direction.normalized()
    if abs(d.dot(up_hint)) > 0.95:
        up_hint = Vector((0, 1, 0))
    t = d.cross(up_hint).normalized()
    b = t.cross(d).normalized()
    return t, b, d


def ring_around(center: Vector, direction: Vector, radius_fn, count: int, up_hint=None):
    """Ring of `count` points around an axis. radius_fn(theta) -> radius."""
    t, b, _ = frame_from_dir(direction, up_hint or Vector((0, 0, 1)))
    pts = []
    for i in range(count):
        th = 2 * math.pi * i / count
        r = radius_fn(th)
        pts.append(center + (t * math.cos(th) + b * math.sin(th)) * r)
    return pts


def polyline_resample(points, count):
    """Resample a polyline into `count` evenly spaced points (with tangents)."""
    pts = [Vector(p) for p in points]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for k in range(count):
        s = total * k / (count - 1)
        acc = 0.0
        for i, L in enumerate(seg):
            if acc + L >= s - 1e-9 or i == len(seg) - 1:
                t = 0.0 if L == 0 else (s - acc) / L
                out.append(pts[i].lerp(pts[i + 1], min(max(t, 0.0), 1.0)))
                break
            acc += L
    tangents = []
    for k in range(count):
        a = out[max(k - 1, 0)]
        b = out[min(k + 1, count - 1)]
        tangents.append((b - a).normalized())
    return out, tangents


def catmull(points, samples_per_seg=8):
    """Catmull-Rom smoothing for a list of control points."""
    pts = [Vector(p) for p in points]
    pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-2])
    return out


def fbm(p: Vector, octaves=3):
    return noise.fractal(p, 0.5, 2.0, octaves, noise_basis="PERLIN_ORIGINAL")


# --------------------------------------------------------------------------
# Object operations (background-safe)
# --------------------------------------------------------------------------
def _override(obj, selected=None):
    sel = selected if selected is not None else [obj]
    return bpy.context.temp_override(object=obj, active_object=obj, selected_objects=sel,
                                     selected_editable_objects=sel)


def apply_modifiers(obj):
    for mod in list(obj.modifiers):
        with _override(obj):
            bpy.ops.object.modifier_apply(modifier=mod.name)


def add_modifier(obj, kind, name=None, **props):
    mod = obj.modifiers.new(name or kind.title(), kind)
    for k, v in props.items():
        setattr(mod, k, v)
    return mod


def shade_smooth(obj, angle_deg=None):
    me = obj.data
    me.shade_smooth()
    if angle_deg is not None:
        me.set_sharp_from_angle(angle=math.radians(angle_deg))


def smart_uv(obj, angle=66.0, margin=0.01):
    bpy.context.view_layer.objects.active = obj
    with _override(obj):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")


def join(objs, name):
    target = objs[0]
    with bpy.context.temp_override(active_object=target, object=target, selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    target.name = name
    target.data.name = name
    return target


def apply_transforms(obj):
    with _override(obj):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tri_count(obj) -> int:
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def bake_cavity_to_color(obj, attr="Color", strength=1.0, blur=2):
    """Cheap ink-pooling mask in vertex colour R: 1 = exposed, 0 = crevice.

    G stores a normalised height gradient (used for wash fades); B stays 1.
    Computed from mesh connectivity so it is deterministic and editor-free.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    conc = []
    for v in bm.verts:
        if not v.link_edges:
            conc.append(0.0)
            continue
        acc = 0.0
        for e in v.link_edges:
            o = e.other_vert(v)
            d = o.co - v.co
            L = d.length
            if L > 1e-9:
                acc += v.normal.dot(d / L)
        conc.append(acc / len(v.link_edges))  # >0 concave (neighbours above normal)
    for _ in range(blur):
        conc = [
            (conc[v.index] + sum(conc[e.other_vert(v).index] for e in v.link_edges))
            / (1 + len(v.link_edges)) if v.link_edges else conc[v.index]
            for v in bm.verts
        ]
    zs = [v.co.z for v in bm.verts] or [0.0]
    zmin, zmax = min(zs), max(zs)
    bm.free()

    if attr in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[attr])
    ca = me.color_attributes.new(attr, "BYTE_COLOR", "POINT")
    for i, v in enumerate(me.vertices):
        c = max(0.0, min(1.0, 1.0 - max(conc[i], 0.0) * 4.0 * strength))
        h = (v.co.z - zmin) / max(zmax - zmin, 1e-6)
        ca.data[i].color = (c, h, 1.0, 1.0)
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.find(attr)


# --------------------------------------------------------------------------
# Preview rendering (Workbench — cheap and deterministic)
# --------------------------------------------------------------------------
def setup_preview_render(res=(1024, 1024), engine="BLENDER_WORKBENCH"):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    if engine == "BLENDER_WORKBENCH":
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.color_type = "MATERIAL"
        shading.show_cavity = True
        shading.cavity_type = "BOTH"
        shading.show_object_outline = True
        shading.object_outline_color = (0.02, 0.02, 0.02)
        shading.background_type = "VIEWPORT"
        shading.background_color = (0.82, 0.80, 0.75)
        scene.display.render_aa = "8"
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    return scene


def look_at_camera(name, location, target, lens=50.0, ortho_scale=None):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(location)
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if ortho_scale:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.lens = lens
    cam_data.clip_end = 500
    return cam


def render_to(path, camera):
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    log("render", os.path.relpath(path, REPO_ROOT))


def seeded(seed: int):
    random.seed(seed)
    return random.Random(seed)


def contact_sheet(paths, out_path, max_width=2400):
    """Concatenate renders horizontally into one PNG (numpy, no external tools)."""
    import numpy as np
    arrays = []
    for p in paths:
        img = bpy.data.images.load(p, check_existing=False)
        w, h = img.size
        a = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        arrays.append(a.reshape(h, w, 4))
        bpy.data.images.remove(img)
    hmax = max(a.shape[0] for a in arrays)
    arrays = [np.pad(a, ((hmax - a.shape[0], 0), (0, 0), (0, 0)), constant_values=1.0) for a in arrays]
    sheet = np.concatenate(arrays, axis=1)
    h, w = sheet.shape[:2]
    step = max(1, int(math.ceil(w / max_width)))
    sheet = sheet[::step, ::step]
    h, w = sheet.shape[:2]
    out = bpy.data.images.new("contact_sheet", w, h, alpha=True)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    log("sheet", out_path)


def ensure_uv(obj):
    """Smart-project UVs if the mesh has none (or only a degenerate layer)."""
    me = obj.data
    if me.uv_layers:
        import numpy as np
        a = np.empty(len(me.loops) * 2, dtype=np.float32)
        me.uv_layers[0].data.foreach_get("uv", a)
        if a.size and (a.max() - a.min()) > 1e-4:
            return False
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    smart_uv(obj)
    return True
