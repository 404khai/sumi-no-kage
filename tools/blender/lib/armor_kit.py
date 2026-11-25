"""Shared construction kit for the armoured / heavy characters (knight, viking).

Everything sits on Kage's skeleton (kage_skeleton.py), so all characters share
one rig layout, the Godot humanoid profile and every animation clip.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import kage_skeleton as ks
import sumi

V = ks.V


def chain(start, d0, d1, segments, length):
    """Control points from `start`, direction blending d0 -> d1 along the chain."""
    pts = [Vector(start)]
    for i in range(segments):
        t = i / max(segments - 1, 1)
        d = Vector(d0).lerp(Vector(d1), t).normalized()
        pts.append(pts[-1] + d * (length / segments))
    return pts


def torso_shell(K, name, fit, levels, mat, col, gap=0.03, keel=0.0, n=40, flare=None, thick=0.007,
                center_y=0.006):
    """Rigid shell around the trunk, fitted from inside the body outward.
    levels: z values top->bottom; flare(z) adds radius; keel adds a front ridge."""
    rings = []
    for z in levels:
        c = V(0, center_y, z)
        rad = []
        for i in range(n):
            th = 2 * math.pi * i / n
            d = Vector((math.sin(th), -math.cos(th), 0))
            r = fit.outward(c, d, 0.35) or 0.15
            fr = max(0.0, math.cos(th))
            rad.append(r + gap + keel * fr ** 8 + (flare(z) if flare else 0.0))
        rad = K._smooth_ring(rad, 3)
        rings.append([V(0, center_y, z) + Vector((math.sin(2 * math.pi * i / n), -math.cos(2 * math.pi * i / n), 0)) * r
                      for i, r in enumerate(rad)])
    bm, _ = sumi.loft(rings, closed=True, u_scale=2.0, v_scale=2.0)
    obj = sumi.mesh_object(name, bm, col)
    return K._finish(obj, mat, thickness=thick)


def dome(name, center, axis, radii, mat, col, cut=0.0, segs=(20, 10), lames=0, rigid_bone=None, flat=None):
    """Ellipsoidal cap around `axis` (pauldrons, helmet parts, fur clumps).
    cut: keep the part with local z >= cut (in unit-sphere space). lames: stepped bands."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1] * 2, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut - 1e-4], context="VERTS")
    for v in bm.verts:
        if lames:
            band = math.floor((1 - v.co.z) * lames / max(1e-3, 1 - cut))
            v.co *= 1.0 + 0.06 * band
        if flat:
            v.co = flat(v.co)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix()
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    bm.loops.layers.uv.new("UVMap")
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.add_modifier(obj, "SOLIDIFY", thickness=0.006, offset=-1.0)
    sumi.apply_modifiers(obj)
    sumi.shade_smooth(obj, angle_deg=40)
    if rigid_bone:
        obj["rigid_bone"] = rigid_bone
    return obj


def horn(name, pts, r0, mat, col, sides=10, r1=0.0006, rigid_bone=None, ridges=0.0):
    pts, tans = sumi.polyline_resample(sumi.catmull(pts, 6), 24)
    rings = []
    for i, (p, t) in enumerate(zip(pts, tans)):
        k = i / (len(pts) - 1)
        r = r0 * (1 - k) ** 1.1 + r1
        rr = lambda th, r=r, k=k: r * (1 + ridges * math.sin(k * 40))  # noqa: E731
        rings.append(sumi.ring_around(p, t, rr, sides))
    bm, grid = sumi.loft(rings, closed=True, cap_start=True, cap_end=True)
    obj = sumi.mesh_object(name, bm, col)
    obj.data.materials.append(mat)
    sumi.shade_smooth(obj)
    if rigid_bone:
        obj["rigid_bone"] = rigid_bone
    return obj


def strips(K, prefix, chains, widths, mat, col, root, taper=0.7, seed=1, twist=0.2):
    """Tattered cloth strips, each riding its own cloth-bone chain."""
    out = []
    for i, ((cname, pts), w) in enumerate(zip(chains, widths)):
        r = K.ribbon(f"{prefix}_{cname}", pts, w, taper, mat, col, twist=twist * (1 if i % 2 else -1), seed=seed + i)
        r["chain_prefix"] = cname
        r["chain_points"] = [list(p) for p in pts]
        r["chain_root"] = root
        r["chain_root_blend"] = 0.5
        out.append(r)
    return out


def tube_path(K, name, pts, radius, mat, col, flat=1.0):
    obj = K.tube(name, pts, radius, mat, col)
    if flat != 1.0:
        pass
    return obj


def cull_faces(obj, pred):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if pred(f.calc_center_median())], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


def region_materials(obj, mats, region):
    """region(center) -> key in mats."""
    me = obj.data
    keys = list(mats)
    for k in keys:
        me.materials.append(mats[k])
    for poly in me.polygons:
        poly.material_index = keys.index(region(poly.center))


def hands_and_feet(p):
    s = 1 if p.x > 0 else -1
    w = ks.joints()["L_wrist" if s > 0 else "R_wrist"]
    d = ks.ARM_DIR if s > 0 else Vector((-ks.ARM_DIR.x, ks.ARM_DIR.y, ks.ARM_DIR.z))
    if abs(p.x) > 0.45 and (p - w).dot(d) > -0.012:
        return "hand"
    if p.z < 0.118:
        return "foot"
    return None


def preview(K, name, actions=("Stance_Halberd_Idle",)):
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.animation_data.action = None
    K.pose(arm, {})
    K.preview(None, name)
    for a in actions:
        arm.animation_data.action = bpy.data.actions[a]
        bpy.context.scene.frame_set(1)
        K.preview(None, f"{name}_{a.lower()}")
    arm.animation_data.action = None
    K.pose(arm, {})
