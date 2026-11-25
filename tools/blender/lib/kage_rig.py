"""Control rig for the shared humanoid skeleton: IK/FK limbs, reverse-foot roll,
torso (centre of gravity) control, widgets, colours and the in-Blender rig panel.

Layering (nothing here is exported: CTRL_* and MCH_* bones are non-deforming and
the glTF exporter keeps deform bones only, baking constraint results by sampling):

    CTRL_Torso            moves/rotates Hips and everything above (Child Of)
    CTRL_IK_Hand.{L,R}    arm IK target; same rest frame as the hand, so in IK the
                          hand copies its rotation (influence = ik_arm_{side})
    CTRL_Pole_Arm.{L,R}   elbow direction
    CTRL_IK_Foot.{L,R}    ground-level foot control, custom property "roll" (deg):
                            roll > 0  heel lifts over the ball, past 45 deg over the toe
                            roll < 0  rocks back on the heel
      MCH_Heel -> MCH_Toe -> MCH_Ball -> MCH_FootTarget (ankle; leg IK target,
                                         foot copies its rotation)
                         \\-> MCH_ToesTarget (toes stay flat while the heel rolls)
    CTRL_Pole_Leg.{L,R}   knee direction

FK is the deform bones themselves. IK/FK blend per limb with the armature
properties ik_arm_L, ik_arm_R, ik_leg_L, ik_leg_R (0 = FK, 1 = IK). The rig panel
(View3D > Sidebar > Kage Rig, text block kage_rig_ui.py) has the sliders and
IK<->FK snapping; snap_* below are the same functions for build scripts.
"""

from __future__ import annotations

import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

SIDES = {"L": "Left", "R": "Right"}
IK_PROPS = ("ik_arm_L", "ik_arm_R", "ik_leg_L", "ik_leg_R")
ROLL_BALL_MAX = 45.0


def V(x, y, z):
    return Vector((x, y, z))


# ------------------------------------------------------------------ edit mode
def edit_bones(eb, J):
    """Create the control and mechanism bones. Called in edit mode, after the
    deform skeleton and the basic CTRL_IK/Pole bones exist."""
    up = V(0, 0, 1)
    t = eb.new("CTRL_Torso")
    t.head, t.tail = eb["Hips"].head.copy(), eb["Hips"].tail.copy()
    t.roll = eb["Hips"].roll
    t.parent = eb["Root"]
    t.use_deform = False
    for side, S in SIDES.items():
        # IK hand shares the hand's rest frame -> hand can copy its rotation 1:1
        c = eb[f"CTRL_IK_Hand.{side}"]
        h = eb[f"{S}Hand"]
        c.head, c.tail, c.roll = h.head.copy(), h.tail.copy(), h.roll
        foot, toes = eb[f"{S}Foot"], eb[f"{S}Toes"]
        ctrl = eb[f"CTRL_IK_Foot.{side}"]
        ctrl.align_roll(up)
        heel, ball, toe = J[f"{side}_heel"], J[f"{side}_ball"], J[f"{side}_toe"]

        def mch(name, head, parent, tail=None, like=None):
            b = eb.new(name)
            if like is not None:
                b.head, b.tail, b.roll = like.head.copy(), like.tail.copy(), like.roll
            else:
                b.head, b.tail = head, tail if tail is not None else head + V(0, -0.05, 0)
                b.align_roll(up)
            b.parent = eb[parent]
            b.use_deform = False
            return b

        mch(f"MCH_Heel.{side}", V(heel.x, heel.y, 0.0), f"CTRL_IK_Foot.{side}")
        mch(f"MCH_Toe.{side}", V(toe.x, toe.y, 0.0), f"MCH_Heel.{side}")
        mch(f"MCH_Ball.{side}", V(ball.x, ball.y, 0.0), f"MCH_Toe.{side}")
        mch(f"MCH_FootTarget.{side}", None, f"MCH_Ball.{side}", like=foot)
        mch(f"MCH_ToesTarget.{side}", None, f"MCH_Toe.{side}", like=toes)


# ------------------------------------------------------------------ pose mode
def _driver(owner, path, index, arm, var_path, expr="v"):
    fc = owner.driver_add(path, index) if index is not None else owner.driver_add(path)
    drv = fc.driver
    drv.type = "SCRIPTED"
    drv.expression = expr
    v = drv.variables.new()
    v.name = "v"
    v.targets[0].id = arm
    v.targets[0].data_path = var_path
    return fc


def pose_setup(arm):
    """Constraints, drivers, foot-roll properties. Called in pose mode."""
    pb = arm.pose.bones
    # torso: Hips follows CTRL_Torso; inverse = rest so the rest pose is untouched
    c = pb["Hips"].constraints.new("CHILD_OF")
    c.name = "Torso"
    c.target, c.subtarget = arm, "CTRL_Torso"
    c.inverse_matrix = arm.data.bones["CTRL_Torso"].matrix_local.inverted()
    for side, S in SIDES.items():
        # legs now aim the IK at the ankle (MCH_FootTarget), not the ground control
        ik = pb[f"{S}LowerLeg"].constraints["IK_Leg"]
        ik.subtarget = f"MCH_FootTarget.{side}"
        for bone, target, prop in ((f"{S}Foot", f"MCH_FootTarget.{side}", f"ik_leg_{side}"),
                                   (f"{S}Toes", f"MCH_ToesTarget.{side}", f"ik_leg_{side}"),
                                   (f"{S}Hand", f"CTRL_IK_Hand.{side}", f"ik_arm_{side}")):
            cr = pb[bone].constraints.new("COPY_ROTATION")
            cr.name = "IK_Follow"
            cr.target, cr.subtarget = arm, target
            cr.influence = 0.0
            _driver(cr, "influence", None, arm, f'["{prop}"]')
        ctrl = pb[f"CTRL_IK_Foot.{side}"]
        ctrl["roll"] = 0.0
        ui = ctrl.id_properties_ui("roll")
        ui.update(min=-60.0, max=110.0, soft_min=-45.0, soft_max=90.0, description="Foot roll (deg)")
        roll = f'pose.bones["CTRL_IK_Foot.{side}"]["roll"]'
        for name, expr in ((f"MCH_Ball.{side}", f"-radians(min(max(v, 0), {ROLL_BALL_MAX}))"),
                           (f"MCH_Toe.{side}", f"-radians(max(v - {ROLL_BALL_MAX}, 0))"),
                           (f"MCH_Heel.{side}", "radians(max(-v, 0))")):
            pb[name].rotation_mode = "XYZ"
            _driver(pb[name], "rotation_euler", 0, arm, roll, expr)
    for k in IK_PROPS:
        ui = arm.id_properties_ui(k)
        ui.update(min=0.0, max=1.0, description="0 = FK, 1 = IK")


# ---------------------------------------------------------------- appearance
WIDGET_COL = "Rig_Widgets"


def _widget(name, verts, edges):
    full = f"WGT_{name}"
    if full in bpy.data.objects:
        return bpy.data.objects[full]
    me = bpy.data.meshes.new(full)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    obj = bpy.data.objects.new(full, me)
    col = bpy.data.collections.get(WIDGET_COL)
    if col is None:
        col = bpy.data.collections.new(WIDGET_COL)
        bpy.context.scene.collection.children.link(col)
    col.objects.link(obj)
    obj.hide_render = True
    obj.hide_viewport = True
    return obj


def _ring(r, n=24, y=0.0, plane="XZ"):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        u, w = r * math.cos(a), r * math.sin(a)
        pts.append(V(u, y, w) if plane == "XZ" else V(u, w, y))
    return pts, [(i, (i + 1) % n) for i in range(n)]


def widgets():
    """Wire shapes in bone space (+Y runs along the bone)."""
    W = {}
    v, e = _ring(1.0)
    W["circle"] = _widget("Circle", v, e)
    # cube
    c = [V(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    ce = [(0, 1), (0, 2), (1, 3), (2, 3), (4, 5), (4, 6), (5, 7), (6, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    W["cube"] = _widget("Cube", c, ce)
    # diamond (octahedron) for poles
    d = [V(1, 0, 0), V(-1, 0, 0), V(0, 1, 0), V(0, -1, 0), V(0, 0, 1), V(0, 0, -1)]
    de = [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 4), (4, 3), (3, 5), (5, 2)]
    W["diamond"] = _widget("Diamond", d, de)
    # foot: flat rounded rectangle on the ground, toes along +Y of the control
    f = [V(-0.055, -0.07, 0), V(0.055, -0.07, 0), V(0.065, 0.10, 0), V(0.045, 0.24, 0),
         V(-0.045, 0.24, 0), V(-0.065, 0.10, 0)]
    W["foot"] = _widget("Foot", f, [(i, (i + 1) % len(f)) for i in range(len(f))])
    # torso: wide square around the pelvis with a forward tick
    s = [V(-1, 0, -1), V(1, 0, -1), V(1, 0, 1), V(-1, 0, 1), V(0, 0, -1), V(0, 0, -1.4)]
    W["torso"] = _widget("Torso", s, [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5)])
    # root: big ring with an arrow pointing forward (-Y in the armature = +Y of a
    # bone pointing up is irrelevant; Root points up, its local -Z is forward)
    v, e = _ring(1.0, 32)
    n = len(v)
    v += [V(0, 0, -1.0), V(0, 0, -1.35), V(-0.12, 0, -1.2), V(0.12, 0, -1.2)]
    e += [(n, n + 1), (n + 1, n + 2), (n + 1, n + 3)]
    W["root"] = _widget("Root", v, e)
    return W


FK_BODY = ("Hips", "Spine", "Chest", "UpperChest", "Neck", "Head")
FK_LIMB = ("Shoulder", "UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot", "Toes")


def _color(pb, palette):
    pb.color.palette = palette
    pb.bone.color.palette = palette


def appearance(arm):
    W = widgets()
    pb = arm.pose.bones
    data = arm.data

    def shape(name, wgt, scale, offset=(0, 0, 0), rot=(0, 0, 0), palette="THEME09"):
        b = pb[name]
        b.custom_shape = W[wgt]
        b.use_custom_shape_bone_size = False
        b.custom_shape_scale_xyz = scale
        b.custom_shape_translation = offset
        b.custom_shape_rotation_euler = rot
        _color(b, palette)

    shape("Root", "root", (0.55, 0.55, 0.55), palette="THEME09")
    shape("CTRL_Torso", "torso", (0.24, 0.24, 0.20), palette="THEME09")
    for n in FK_BODY:
        L = data.bones[n].length
        shape(n, "circle", (0.16 if n in ("Hips", "Spine", "Chest", "UpperChest") else 0.08,) * 3,
              offset=(0, L * 0.5, 0), palette="THEME09")
    for side, S in SIDES.items():
        pal = "THEME04" if side == "L" else "THEME01"   # left blue, right red (Rigify convention)
        for part in FK_LIMB:
            n = S + part
            L = data.bones[n].length
            r = {"Shoulder": 0.05, "UpperArm": 0.06, "LowerArm": 0.05, "Hand": 0.045,
                 "UpperLeg": 0.09, "LowerLeg": 0.07, "Foot": 0.05, "Toes": 0.04}[part]
            shape(n, "circle", (r, r, r), offset=(0, L * 0.5, 0), palette=pal)
        shape(f"CTRL_IK_Hand.{side}", "cube", (0.05, 0.05, 0.05), offset=(0, 0.04, 0), palette="THEME02")
        shape(f"CTRL_IK_Foot.{side}", "foot", (1, 1, 1), offset=(0, 0.07, 0), palette="THEME02")
        shape(f"CTRL_Pole_Arm.{side}", "diamond", (0.035,) * 3, palette="THEME02")
        shape(f"CTRL_Pole_Leg.{side}", "diamond", (0.035,) * 3, palette="THEME02")
    # bone collections: MCH hidden, controls on top
    mech = data.collections.new("Mechanism")
    for b in data.bones:
        if b.name.startswith("MCH_"):
            for col in list(b.collections):
                col.unassign(b)
            mech.assign(b)
        if b.name == "CTRL_Torso":
            for col in list(b.collections):
                col.unassign(b)
            data.collections["Controls"].assign(b)
    mech.is_visible = False
    data.collections["Sockets"].is_visible = False
    data.display_type = "OCTAHEDRAL"


def install_ui(arm):
    """Ship the rig panel inside the .blend (Text block registered as a module:
    runs on open when 'Auto Run Python Scripts' is enabled; or press Run Script)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kage_rig_ui.py")
    name = "kage_rig_ui.py"
    txt = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    txt.clear()
    txt.write(open(path).read())
    txt.use_module = True
    arm.data["rig_ui"] = name


def build(arm, eb_stage, J):
    """Convenience for build scripts: eb_stage is 'edit' or 'pose'."""
    if eb_stage == "edit":
        edit_bones(arm.data.edit_bones, J)
    else:
        pose_setup(arm)
        appearance(arm)
        install_ui(arm)


# ------------------------------------------------------- authoring utilities
def _rest(arm, name):
    return arm.data.bones[name].matrix_local


def set_bone_world(arm, name, m_world: Matrix):
    """Pose a parent-is-unposed control (Root children) to an armature-space matrix."""
    pb = arm.pose.bones[name]
    pb.matrix = m_world


def set_foot(arm, side, ground_pos, yaw_deg=0.0, roll_deg=0.0, pitch_deg=0.0):
    """Plant the IK foot: ground_pos = point on the floor under the ankle (armature
    space), yaw about +Z (degrees, + turns the toes toward character-left), roll
    as on the control, pitch tilts the whole foot (+ toes up)."""
    name = f"CTRL_IK_Foot.{side}"
    rest = _rest(arm, name)
    q = Quaternion((0, 0, 1), math.radians(yaw_deg)) @ Quaternion((1, 0, 0), math.radians(pitch_deg))
    m = Matrix.Translation(Vector(ground_pos)) @ q.to_matrix().to_4x4() @ rest.to_3x3().to_4x4()
    set_bone_world(arm, name, m)
    arm.pose.bones[name]["roll"] = float(roll_deg)


def set_point(arm, name, pos):
    rest = _rest(arm, name)
    m = rest.copy()
    m.translation = Vector(pos)
    set_bone_world(arm, name, m)


def snap_ik_to_fk(arm, limb, side):
    """Move the IK controls onto the current FK pose (call with IK at 0)."""
    S = SIDES[side]
    pb = arm.pose.bones
    bpy.context.view_layer.update()
    if limb == "arm":
        hand = pb[f"{S}Hand"].matrix.copy()
        upper, lower = pb[f"{S}UpperArm"], pb[f"{S}LowerArm"]
        set_bone_world(arm, f"CTRL_IK_Hand.{side}", hand)
        mid = (upper.head + hand.translation) * 0.5
        set_point(arm, f"CTRL_Pole_Arm.{side}", lower.head + (lower.head - mid).normalized() * 0.4)
    else:
        foot = pb[f"{S}Foot"].matrix.copy()
        upper, lower = pb[f"{S}UpperLeg"], pb[f"{S}LowerLeg"]
        tgt_rest = _rest(arm, f"MCH_FootTarget.{side}")
        ctrl_rest = _rest(arm, f"CTRL_IK_Foot.{side}")
        pb[f"CTRL_IK_Foot.{side}"]["roll"] = 0.0
        set_bone_world(arm, f"CTRL_IK_Foot.{side}", foot @ tgt_rest.inverted() @ ctrl_rest)
        mid = (upper.head + foot.translation) * 0.5
        set_point(arm, f"CTRL_Pole_Leg.{side}", lower.head + (lower.head - mid).normalized() * 0.5)
    bpy.context.view_layer.update()


def snap_fk_to_ik(arm, limb, side):
    """Copy the IK-solved result onto the FK bones (call with IK at 1)."""
    S = SIDES[side]
    chain = (f"{S}UpperArm", f"{S}LowerArm", f"{S}Hand") if limb == "arm" else \
        (f"{S}UpperLeg", f"{S}LowerLeg", f"{S}Foot", f"{S}Toes")
    bpy.context.view_layer.update()
    visual = {n: arm.pose.bones[n].matrix.copy() for n in chain}
    prop = f"ik_{limb}_{side}"
    saved = arm[prop]
    arm[prop] = 0.0
    for n in chain:
        bpy.context.view_layer.update()
        arm.pose.bones[n].matrix = visual[n]
    arm[prop] = saved
    bpy.context.view_layer.update()
