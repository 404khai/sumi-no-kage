"""Export every asset in tools/asset_manifest.json to glTF binary for Godot.

    blender -b --factory-startup --python tools/blender/export_assets.py [-- <asset_id> ...]

Exports from the saved .blend sources (never from a live session) so builds are
reproducible. Only deform bones are exported; CTRL_* IK/pole bones stay in the
source rig. Constraint and driver results are baked by sampling.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import bpy  # noqa: E402

import sumi  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def find_layer_collection(layer, name):
    if layer.collection.name == name:
        return layer
    for child in layer.children:
        found = find_layer_collection(child, name)
        if found:
            return found
    return None


def export(asset):
    src = sumi.repo_path(asset["source"])
    out = sumi.repo_path(asset["output"])
    bpy.ops.wm.open_mainfile(filepath=src)
    lc = find_layer_collection(bpy.context.view_layer.layer_collection, asset["collection"])
    if lc is None:
        raise RuntimeError(f"{asset['id']}: collection {asset['collection']} missing in {src}")
    bpy.context.view_layer.active_layer_collection = lc
    # rest pose for the bind; actions are exported separately
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            if obj.animation_data:
                obj.animation_data.action = None
            for pb in obj.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    anim = asset.get("animations", False)
    bpy.ops.export_scene.gltf(
        filepath=out,
        export_format="GLB",
        use_active_collection=True,
        use_active_collection_with_nested=True,
        export_yup=True,
        export_apply=False,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_image_format="NONE",
        export_vertex_color="ACTIVE",
        export_all_vertex_colors=False,
        export_extras=True,
        export_skins=True,
        export_def_bones=True,
        export_influence_nb=4,
        export_morph=False,
        export_animations=anim,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_frame_step=1,
        export_optimize_animation_size=True,
        export_reset_pose_bones=True,
        export_rest_position_armature=True,
        export_anim_single_armature=True,
        export_leaf_bone=False,
    )
    sumi.log("exported", asset["id"], "->", asset["output"], f"{os.path.getsize(out) / 1024:.0f} KiB")


def main():
    manifest = json.load(open(sumi.repo_path("tools", "asset_manifest.json")))
    for asset in manifest["assets"]:
        if ARGS and asset["id"] not in ARGS:
            continue
        export(asset)


main()
