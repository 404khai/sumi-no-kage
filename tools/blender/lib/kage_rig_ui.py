"""Kage Rig panel: View3D > Sidebar (N) > Kage Rig.

Shipped inside every character .blend as the text block "kage_rig_ui.py" (registered
as a module, so it loads on open when Preferences > Save & Load > Auto Run Python
Scripts is on; otherwise open the Scripting tab and press Run Script once).

Per limb: IK/FK blend slider, snap buttons (match IK to FK, match FK to IK) and,
for legs, foot roll. Snapping keeps the visual pose, so you can switch modes
mid-shot without a pop: snap first, then key the slider.
"""

import bpy

SIDES = {"L": "Left", "R": "Right"}
LIMBS = (("arm", "L", "Left arm"), ("arm", "R", "Right arm"), ("leg", "L", "Left leg"), ("leg", "R", "Right leg"))


def _is_rig(obj):
    return obj is not None and obj.type == "ARMATURE" and "ik_arm_L" in obj.keys()


def _set_world(pb, m):
    pb.matrix = m
    bpy.context.view_layer.update()


def snap_ik_to_fk(arm, limb, side):
    S = SIDES[side]
    pb = arm.pose.bones
    bpy.context.view_layer.update()
    if limb == "arm":
        hand = pb[f"{S}Hand"].matrix.copy()
        _set_world(pb[f"CTRL_IK_Hand.{side}"], hand)
        upper, lower = pb[f"{S}UpperArm"], pb[f"{S}LowerArm"]
        pole = pb[f"CTRL_Pole_Arm.{side}"]
        mid = (upper.head + hand.translation) * 0.5
        m = pole.matrix.copy()
        m.translation = lower.head + (lower.head - mid).normalized() * 0.4
        _set_world(pole, m)
    else:
        foot = pb[f"{S}Foot"].matrix.copy()
        bones = arm.data.bones
        ctrl = pb[f"CTRL_IK_Foot.{side}"]
        ctrl["roll"] = 0.0
        _set_world(ctrl, foot @ bones[f"MCH_FootTarget.{side}"].matrix_local.inverted()
                   @ bones[f"CTRL_IK_Foot.{side}"].matrix_local)
        upper, lower = pb[f"{S}UpperLeg"], pb[f"{S}LowerLeg"]
        pole = pb[f"CTRL_Pole_Leg.{side}"]
        mid = (upper.head + foot.translation) * 0.5
        m = pole.matrix.copy()
        m.translation = lower.head + (lower.head - mid).normalized() * 0.5
        _set_world(pole, m)


def snap_fk_to_ik(arm, limb, side):
    S = SIDES[side]
    chain = (f"{S}UpperArm", f"{S}LowerArm", f"{S}Hand") if limb == "arm" else \
        (f"{S}UpperLeg", f"{S}LowerLeg", f"{S}Foot", f"{S}Toes")
    bpy.context.view_layer.update()
    visual = {n: arm.pose.bones[n].matrix.copy() for n in chain}
    prop = f"ik_{limb}_{side}"
    saved = arm[prop]
    arm[prop] = 0.0
    for n in chain:
        _set_world(arm.pose.bones[n], visual[n])
    arm[prop] = saved
    bpy.context.view_layer.update()


class KAGE_OT_snap(bpy.types.Operator):
    """Snap one limb between IK and FK without changing the visual pose"""
    bl_idname = "kage.snap"
    bl_label = "Snap"
    bl_options = {"REGISTER", "UNDO"}

    limb: bpy.props.StringProperty()
    side: bpy.props.StringProperty()
    to: bpy.props.EnumProperty(items=(("IK", "To IK", "Match IK controls to FK, switch to IK"),
                                      ("FK", "To FK", "Match FK bones to IK, switch to FK")))

    @classmethod
    def poll(cls, context):
        return _is_rig(context.object) and context.mode == "POSE"

    def execute(self, context):
        arm = context.object
        prop = f"ik_{self.limb}_{self.side}"
        if self.to == "IK":
            arm[prop] = 0.0
            snap_ik_to_fk(arm, self.limb, self.side)
            arm[prop] = 1.0
        else:
            arm[prop] = 1.0
            snap_fk_to_ik(arm, self.limb, self.side)
            arm[prop] = 0.0
        arm.update_tag()
        return {"FINISHED"}


class KAGE_PT_rig(bpy.types.Panel):
    bl_label = "Kage Rig"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Kage Rig"

    @classmethod
    def poll(cls, context):
        return _is_rig(context.object)

    def draw(self, context):
        arm = context.object
        col = self.layout.column(align=True)
        for limb, side, label in LIMBS:
            box = col.box()
            row = box.row(align=True)
            row.prop(arm, f'["ik_{limb}_{side}"]', text=f"{label} IK", slider=True)
            row = box.row(align=True)
            op = row.operator("kage.snap", text="FK → IK")
            op.limb, op.side, op.to = limb, side, "IK"
            op = row.operator("kage.snap", text="IK → FK")
            op.limb, op.side, op.to = limb, side, "FK"
            if limb == "leg":
                box.prop(arm.pose.bones[f"CTRL_IK_Foot.{side}"], '["roll"]', text="Foot roll", slider=True)
        self.layout.label(text="Torso: CTRL_Torso moves the upper body; IK feet stay planted.")


CLASSES = (KAGE_OT_snap, KAGE_PT_rig)


def register():
    for c in CLASSES:
        if not hasattr(bpy.types, c.__name__):
            bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        if hasattr(bpy.types, c.__name__):
            bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
else:
    register()
