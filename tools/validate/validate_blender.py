"""Source-side validation of every asset in tools/asset_manifest.json.

    blender -b --factory-startup --python tools/validate/validate_blender.py

Checks what Godot cannot see: applied transforms, UVs, n-gons, loose geometry,
material naming, skin-weight hygiene on the *source* rig, CTRL bones not
deforming, blockout tagging. Writes build/reports/validation_blender.json;
exit code 1 on errors.
"""

import json
import os
import sys

import bmesh
import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Report:
    def __init__(self):
        self.errors, self.warnings, self.assets = [], [], {}

    def err(self, aid, msg):
        self.errors.append(f"{aid}: {msg}")

    def warn(self, aid, msg):
        self.warnings.append(f"{aid}: {msg}")


def collection_objects(name):
    col = bpy.data.collections.get(name)
    return list(col.all_objects) if col else None


def check_mesh(rep, aid, obj, info):
    me = obj.data
    if any(abs(s - 1.0) > 1e-4 for s in obj.scale):
        rep.err(aid, f"{obj.name}: unapplied scale {tuple(obj.scale)}")
    if not me.uv_layers:
        rep.err(aid, f"{obj.name}: no UVs")
    for m in me.materials:
        if m is None:
            rep.err(aid, f"{obj.name}: empty material slot")
        elif not m.name.startswith("M_"):
            rep.err(aid, f"{obj.name}: material '{m.name}' breaks the M_<Asset>_<Part> naming contract")
    bm = bmesh.new()
    bm.from_mesh(me)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    bm.free()
    if loose:
        rep.err(aid, f"{obj.name}: {loose} loose vertices")
    if degenerate:
        rep.warn(aid, f"{obj.name}: {degenerate} zero-area faces")
    if ngons:
        info.setdefault("ngons", {})[obj.name] = ngons
    if "Color" not in me.color_attributes:
        rep.warn(aid, f"{obj.name}: no ink cavity vertex colours")
    return sum(len(p.vertices) - 2 for p in me.polygons)


def check_skinning(rep, aid, obj, arm, limit):
    deform = {b.name for b in arm.data.bones if b.use_deform}
    names = {g.index: g.name for g in obj.vertex_groups}
    stray = {g.name for g in obj.vertex_groups} - deform
    if stray:
        rep.err(aid, f"{obj.name}: vertex groups without deform bones {sorted(stray)[:5]}")
    unweighted = over = unnorm = 0
    for v in obj.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-5 and names.get(g.group) in deform]
        if not ws:
            unweighted += 1
        if len(ws) > limit:
            over += 1
        if ws and abs(sum(ws) - 1.0) > 0.01:
            unnorm += 1
    if unweighted:
        rep.err(aid, f"{obj.name}: {unweighted} unweighted vertices")
    if over:
        rep.err(aid, f"{obj.name}: {over} vertices over {limit} influences")
    if unnorm:
        rep.err(aid, f"{obj.name}: {unnorm} vertices with non-normalised weights")


def validate(rep, asset):
    aid = asset["id"]
    info = rep.assets.setdefault(aid, {"status": asset["status"]})
    path = os.path.join(ROOT, asset["source"])
    if not os.path.exists(path):
        rep.err(aid, f"source missing: {asset['source']} (run {asset['build']})")
        return
    bpy.ops.wm.open_mainfile(filepath=path)
    objs = collection_objects(asset["collection"])
    if objs is None:
        rep.err(aid, f"collection {asset['collection']} missing")
        return
    meshes = [o for o in objs if o.type == "MESH" and not o.name.endswith("-colonly")]
    tris = sum(check_mesh(rep, aid, o, info) for o in meshes)
    mats = {m.name for o in meshes for m in o.data.materials if m}
    info.update(tris=tris, meshes=len(meshes), materials=sorted(mats))
    b = asset.get("budget", {})
    if tris > b.get("tris", 1 << 30):
        rep.err(aid, f"triangle budget {tris} > {b['tris']}")
    if len(mats) > b.get("materials", 99):
        rep.err(aid, f"{len(mats)} materials > budget {b['materials']}")
    arms = [o for o in objs if o.type == "ARMATURE"]
    if asset["kind"] == "character":
        if len(arms) != 1:
            rep.err(aid, f"expected one armature, found {len(arms)}")
            return
        arm = arms[0]
        deform = [bn for bn in arm.data.bones if bn.use_deform]
        info["deform_bones"] = len(deform)
        info["control_bones"] = len(arm.data.bones) - len(deform)
        if len(deform) > b.get("bones", 999):
            rep.err(aid, f"{len(deform)} deform bones > budget")
        for bn in arm.data.bones:
            if bn.name.startswith("CTRL_") and bn.use_deform:
                rep.err(aid, f"control bone {bn.name} is deforming")
        for s in asset["expect"].get("sockets", []):
            if s not in arm.data.bones:
                rep.err(aid, f"socket bone {s} missing")
        for o in meshes:
            if not any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers):
                rep.err(aid, f"{o.name}: not bound to {arm.name}")
            check_skinning(rep, aid, o, arm, b.get("max_influences", 4))
        actions = [a.name for a in bpy.data.actions]
        info["actions"] = actions
        for a in asset["expect"].get("actions", []):
            if a not in actions:
                rep.err(aid, f"action {a} missing")
        zmax = max((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
        info["height"] = round(zmax, 3)
        lo, hi = asset["expect"]["height"]
        if not lo <= zmax <= hi:
            rep.err(aid, f"height {zmax:.3f} outside {lo}-{hi}")
    if asset["status"] == "blockout":
        untagged = [o.name for o in objs if o.get("sumi_status") != "blockout"]
        if untagged:
            rep.err(aid, f"blockout objects missing sumi_status tag: {untagged[:5]}")
        cols = [o.name for o in objs if o.name.split("-")[-1] in ("col", "colonly", "convcol", "convcolonly")]
        info["collision_objects"] = len(cols)
    for n in asset.get("expect", {}).get("nodes", []):
        if n not in [o.name for o in objs]:
            rep.err(aid, f"node {n} missing")


def main():
    manifest = json.load(open(os.path.join(ROOT, "tools", "asset_manifest.json")))
    rep = Report()
    for asset in manifest["assets"]:
        validate(rep, asset)
    out = os.path.join(ROOT, "build", "reports", "validation_blender.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"assets": rep.assets, "errors": rep.errors, "warnings": rep.warnings}, open(out, "w"), indent=2)
    for w in rep.warnings:
        print("[validate-blender] WARN ", w)
    for e in rep.errors:
        print("[validate-blender] ERROR", e)
    print(f"[validate-blender] {len(rep.assets)} assets, {len(rep.errors)} errors, {len(rep.warnings)} warnings")
    sys.stdout.flush()
    os._exit(1 if rep.errors else 0)


main()
