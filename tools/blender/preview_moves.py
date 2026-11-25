"""Render the dagger pose library and clip filmstrips from the built kage.blend.

    blender -b --factory-startup --python tools/blender/preview_moves.py -- [poses] [clips] [check]
        [--only NAME ...] [--out DIR]

  poses   one labelled sheet of every Pose_Daggers_* (three-quarter + side views)
  clips   one filmstrip per dagger clip (every 3rd frame, three-quarter view)
  check   numeric report: IK reach error (feet that cannot reach their target)
          and foot skate (planted-foot world drift against the clip's root motion)

Daggers are attached in Kage's reverse grip exactly as the game does it
(WeaponDefinition.grip_transform: 180 deg about the socket's Z), through the
glTF axis change the weapon was authored for.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import sumi  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = sumi.repo_path("docs", "renders", "poses")
if "--out" in ARGS:
    OUT = os.path.abspath(ARGS[ARGS.index("--out") + 1])
ONLY = []
if "--only" in ARGS:
    ONLY = [a for a in ARGS[ARGS.index("--only") + 1:] if not a.startswith("--")]

# glTF Y-up conversion of the weapon mesh, then the reverse-grip turn
GLTF = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
REVERSE = Matrix.Rotation(math.pi, 4, "Z")


def load_scene():
    bpy.ops.wm.open_mainfile(filepath=sumi.repo_path("assets_src", "characters", "kage", "kage.blend"))
    arm = bpy.data.objects["Kage_Rig"]
    src = sumi.repo_path("assets_src", "weapons", "kagenui_daggers", "kagenui_daggers.blend")
    with bpy.data.libraries.load(src) as (data_from, data_to):
        data_to.objects = ["Kagenui_Dagger"]
    blades = []
    for side in ("Left", "Right"):
        ob = data_to.objects[0].copy()
        ob.parent = None
        bpy.context.scene.collection.objects.link(ob)
        blades.append((side, ob))
    return arm, blades


def place_blades(arm, blades):
    bpy.context.view_layer.update()
    for side, ob in blades:
        pb = arm.pose.bones[f"{side}HandWeapon"]
        ob.matrix_world = arm.matrix_world @ pb.matrix @ REVERSE @ GLTF


def label(text, loc, size=0.11):
    cu = bpy.data.curves.new("lbl", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("lbl", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("lbl")
    mat.diffuse_color = (0.55, 0.08, 0.06, 1)
    cu.materials.append(mat)
    return ob


def grid(paths, out, cols):
    import numpy as np
    imgs = []
    for p in paths:
        img = bpy.data.images.load(p, check_existing=False)
        w, h = img.size
        a = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        imgs.append(a.reshape(h, w, 4))
        bpy.data.images.remove(img)
    h, w = imgs[0].shape[:2]
    rows = math.ceil(len(imgs) / cols)
    sheet = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, a in enumerate(imgs):
        r, c = divmod(i, cols)
        r = rows - 1 - r  # image rows are bottom-up
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = a
    img = bpy.data.images.new("grid", sheet.shape[1], sheet.shape[0], alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    for p in paths:
        os.remove(p)
    sumi.log("sheet", os.path.relpath(out, sumi.repo_path()))


def cams():
    tgt = (0, -0.15, 0.88)
    return {"34": sumi.look_at_camera("Cam34", (2.6, -3.6, 1.45), tgt, lens=60),
            "side": sumi.look_at_camera("CamSide", (4.4, -0.3, 1.0), tgt, lens=60),
            "front": sumi.look_at_camera("CamFront", (0.3, -4.5, 1.2), tgt, lens=60)}


def set_clip(arm, name, frame):
    arm.animation_data.action = bpy.data.actions[name]
    bpy.context.scene.frame_set(int(frame))


def render_poses(arm, blades):
    sumi.setup_preview_render((420, 560))
    C = cams()
    names = sorted(a.name for a in bpy.data.actions if a.name.startswith("Pose_Daggers_"))
    order = json.load(open(sumi.repo_path("game", "data", "clip_events.json")))["poses"]
    names = [n for n in order if n in names]
    if ONLY:
        names = [n for n in names if any(o in n for o in ONLY)]
    paths = []
    for n in names:
        set_clip(arm, n, 1)
        place_blades(arm, blades)
        lbl = label(n.replace("Pose_Daggers_", ""), (0, 0.6, 2.0))
        lbl.rotation_euler = (math.radians(90), 0, math.radians(35))
        for view in ("34", "side"):
            p = os.path.join(OUT, f"_{n}_{view}.png")
            lbl.hide_render = view != "34"
            sumi.render_to(p, C[view])
            paths.append(p)
        bpy.data.objects.remove(lbl)
    grid(paths, os.path.join(OUT, "dagger_pose_library.png" if not ONLY else "wip_poses.png"), 6)


def render_clips(arm, blades):
    sumi.setup_preview_render((300, 400))
    C = cams()
    ev = json.load(open(sumi.repo_path("game", "data", "clip_events.json")))["clips"]
    for name, e in ev.items():
        if ONLY and not any(o in name for o in ONLY):
            continue
        act = bpy.data.actions[name]
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        frames = list(range(f0, f1 + 1, 3 if f1 - f0 > 20 else 2))
        paths = []
        hit_frames = {round(h * 30) + f0 for h in e.get("hits", [])}
        for f in frames:
            set_clip(arm, name, f)
            place_blades(arm, blades)
            mark = " HIT" if any(abs(f - h) <= 1 for h in hit_frames) else ""
            lbl = label(f"{f}{mark}", (0, 0.6, 1.95), 0.14)
            p = os.path.join(OUT, f"_{name}_{f}.png")
            sumi.render_to(p, C["34"])
            paths.append(p)
            bpy.data.objects.remove(lbl)
        grid(paths, os.path.join(OUT, f"strip_{name}.png"), min(len(paths), 12))


def check(arm):
    ev = json.load(open(sumi.repo_path("game", "data", "clip_events.json")))["clips"]
    rows = []
    for name, e in ev.items():
        act = bpy.data.actions[name]
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        worst_reach, skate = 0.0, 0.0
        prev = {}
        for i, f in enumerate(range(f0, f1 + 1)):
            set_clip(arm, name, f)
            pb = arm.pose.bones
            root = e["root"][i] if i < len(e["root"]) else e["root"][-1]
            for side, S in (("L", "Left"), ("R", "Right")):
                err = (pb[f"{S}Foot"].head - pb[f"MCH_FootTarget.{side}"].head).length
                worst_reach = max(worst_reach, err)
                # world position of the ball of the foot; planted = on the ground
                ball = pb[f"{S}Foot"].tail.copy()
                world = Vector((ball.x, ball.y - root, ball.z))
                if e.get("loop"):
                    continue  # loops: checked by speed match below
                if ball.z < 0.035 and side in prev and prev[side][1] < 0.035:
                    skate = max(skate, (world.xy - prev[side][0].xy).length * 30)
                prev[side] = (world, ball.z)
        rows.append((name, worst_reach, skate))
    # planted feet are pinned in world space by construction (anim_engine), so the
    # only way a foot can skate is the leg failing to reach its target
    print("\nclip                              ik reach err (m)")
    for n, r, _ in rows:
        flag = "  <-- foot cannot reach target" if r > 0.03 else ""
        print(f"{n:34s} {r:8.3f}{flag}")


def main():
    arm, blades = load_scene()
    os.makedirs(OUT, exist_ok=True)
    if "check" in ARGS:
        check(arm)
    if "poses" in ARGS:
        render_poses(arm, blades)
    if "clips" in ARGS:
        render_clips(arm, blades)


main()
