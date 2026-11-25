"""Pose-to-pose animation engine: key poses + timing in, dense baked actions out.

Why not Blender keyframes on a handful of poses: sparse keys with auto handles
stop at every key (robotic), and a code-driven lunge never matches the feet
(skating). Here every clip is evaluated per frame in Python:

  * Body: each FK bone is a cubic Hermite spline through its key quaternions
    (C1 continuous, per-key tension: 0 flows through, 1 settles into the key).
    Limbs lag the torso by a few frames (overlap/drag), so a slash leads with the
    hips, then chest, shoulder, elbow, wrist.
  * Root motion: a monotone curve of forward distance (metres) per frame. It is
    exported to game/data/clip_events.json and the game moves the body by exactly
    this curve, so animation and travel agree.
  * Footwork: its own track. A foot is planted in world space between steps
    (its local position slides against the root curve, so it never skates) and
    travels along a lifted arc during a step, with heel-off/heel-strike roll.
    Legs are solved by the rig's leg IK (exported baked).

Coordinates: armature space, character faces -Y, left = +X, metres. "Forward
distance" d moves the root to y = -d.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector

FPS = 30
SIDES = {"L": "Left", "R": "Right"}

# frames each bone trails the hips by (scaled per clip by Clip.drag)
LAG = {"Hips": 0.0, "Spine": 0.3, "Chest": 0.6, "UpperChest": 0.9, "Neck": 0.6, "Head": 0.3,
       "Shoulder": 1.0, "UpperArm": 1.2, "LowerArm": 1.8, "Hand": 2.4}


def _lag(name, drag):
    for side in ("Left", "Right"):
        if name.startswith(side):
            part = name[len(side):]
            if part in LAG:
                return LAG[part] * drag
            if any(f in part for f in ("Thumb", "Index", "Middle", "Ring", "Little")):
                return LAG["Hand"] * drag
            return 0.0
    return LAG.get(name, 0.0) * drag


# ------------------------------------------------------------------- poses
@dataclass
class Foot:
    x: float                 # ground point under the ankle, armature space (local to the root)
    y: float
    yaw: float = 0.0         # degrees, + turns toes toward character-left
    roll: float = 0.0        # foot-roll control (deg): + heel up, - toes up
    z: float = 0.0           # lift off the ground (jumps)


@dataclass
class Pose:
    name: str
    rot: dict                # bone -> Quaternion (pose basis)
    hips_loc: Vector
    feet: dict               # "L"/"R" -> Foot (local)
    meta: dict = field(default_factory=dict)


def resolve(K, arm, name, body, feet, meta=None):
    """Resolve an FK body spec (build_kage.pose syntax) into local quaternions."""
    spec = dict(body)
    spec.update(K.fist("L"))
    spec.update(K.fist("R"))
    K.pose(arm, spec)
    bpy.context.view_layer.update()
    rot, hips = {}, Vector()
    for pb in arm.pose.bones:
        if pb.name.startswith(("CTRL_", "MCH_")):
            continue
        rot[pb.name] = pb.rotation_quaternion.copy()
    hips = arm.pose.bones["Hips"].location.copy()
    return Pose(name, rot, hips, {s: Foot(*f) if not isinstance(f, Foot) else f for s, f in feet.items()},
                meta or {})


# ------------------------------------------------------------------ splines
def _hermite(p0, p1, m0, m1, t):
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)


def _spline(times, values, tensions, t, loop_len=None):
    """Cubic Hermite through (times, values) with finite-difference tangents.
    values: list of floats/Vectors (same type). loop_len: wrap for cycles."""
    n = len(times)
    if loop_len:
        t = (t - times[0]) % loop_len + times[0]
    if t <= times[0] and not loop_len:
        return values[0]
    if t >= times[-1] and not loop_len:
        return values[-1]

    def at(i):
        if loop_len:
            k, r = divmod(i, n - 1)  # last key duplicates the first
            return times[r] + k * loop_len, values[r], tensions[r]
        i = min(max(i, 0), n - 1)
        return times[i], values[i], tensions[i]

    i = 0
    while i < n - 1 and times[i + 1] <= t:
        i += 1
    if i >= n - 1:
        i = n - 2

    def tangent(j):
        tj, vj, tens = at(j)
        if not loop_len and (j <= 0 or j >= n - 1):
            return vj * 0.0
        ta, va, _ = at(j - 1)
        tb, vb, _ = at(j + 1)
        return (vb - va) / (tb - ta) * (1.0 - tens)

    t0, v0, _ = at(i)
    t1, v1, _ = at(i + 1)
    h = t1 - t0
    u = (t - t0) / h
    return _hermite(v0, v1, tangent(i) * h, tangent(i + 1) * h, u)


def _monotone(times, values, t):
    """Monotone cubic (Fritsch-Carlson): root motion never runs backwards."""
    n = len(times)
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    d = [(values[i + 1] - values[i]) / (times[i + 1] - times[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                k = 3 / math.sqrt(s)
                m[i], m[i + 1] = k * a * d[i], k * b * d[i]
    i = 0
    while times[i + 1] < t:
        i += 1
    h = times[i + 1] - times[i]
    return _hermite(values[i], values[i + 1], m[i] * h, m[i + 1] * h, (t - times[i]) / h)


def _align(quats):
    out = [quats[0].copy()]
    for q in quats[1:]:
        q = q.copy()
        if out[-1].dot(q) < 0:
            q.negate()
        out.append(q)
    return out


# ------------------------------------------------------------------- clips
@dataclass
class Step:
    side: str
    start: float             # frames
    end: float
    to: Foot                 # landing position, local to the root at `end`
    lift: float = 0.07       # arc height (m)
    drag: bool = False       # sliding shuffle: no lift, toes stay down


@dataclass
class Clip:
    name: str
    keys: list               # [(frame, Pose, tension)]
    root: list = field(default_factory=lambda: [(1, 0.0)])     # [(frame, forward distance m)]
    steps: list = field(default_factory=list)
    drag: float = 1.0
    loop: bool = False
    hits: list = field(default_factory=list)       # frames
    link: float | None = None                      # frame from which the next attack may start
    trails: dict = field(default_factory=dict)     # "L"/"R" -> (start, end) frames
    meta: dict = field(default_factory=dict)
    hold_end: int | None = None                    # frames holding the last key so lagging limbs settle
    feet_fn: object = None                         # loops: f -> {side: (local pos, yaw, roll)}

    def __post_init__(self):
        if self.hold_end is None:
            self.hold_end = 0 if self.loop else int(math.ceil(LAG["Hand"] * self.drag))

    @property
    def first(self):
        return self.keys[0][0]

    @property
    def last(self):
        return self.keys[-1][0] + self.hold_end


def _root_at(clip, f):
    if clip.loop:
        # constant speed loop: distance per cycle from the two root keys
        (f0, d0), (f1, d1) = clip.root[0], clip.root[-1]
        return d0 + (d1 - d0) * (f - f0) / (f1 - f0)
    return _monotone([k[0] for k in clip.root], [k[1] for k in clip.root], f)


def _feet_at(clip, f):
    """Local (root-relative) foot targets at frame f: {side: (pos, yaw, roll)}.

    Between steps a foot is pinned in world space, so its local position moves
    against the root curve; during a step it follows an eased, lifted arc."""
    if clip.feet_fn is not None:
        return clip.feet_fn(f)
    d = _root_at(clip, f)
    key_t = [k[0] for k in clip.keys]
    key_tens = [k[2] for k in clip.keys]
    out = {}
    for side in ("L", "R"):
        start = clip.keys[0][1].feet[side]
        world = Vector((start.x, start.y - _root_at(clip, clip.first), start.z))
        yaw = start.yaw
        active = None
        for st in sorted((s for s in clip.steps if s.side == side), key=lambda s: s.start):
            land = Vector((st.to.x, st.to.y - _root_at(clip, st.end), st.to.z))
            if f >= st.end:
                world, yaw = land, st.to.yaw
                continue
            if f > st.start:
                active = (st, world.copy(), yaw, land)
            break
        # planted roll follows the body keys (e.g. the rear heel lifts in guard)
        roll = _spline(key_t, [k[1].feet[side].roll for k in clip.keys], key_tens, f)
        if active is not None:
            st, w0, y0, w1 = active
            u = (f - st.start) / (st.end - st.start)
            e = u * u * (3 - 2 * u)
            world = w0.lerp(w1, e)
            yaw = y0 + (st.to.yaw - y0) * e
            if st.drag:
                roll = roll + 12 * math.sin(math.pi * u)
            else:
                world.z += st.lift * math.sin(math.pi * u)
                # heel-off, toes trail, heel strike, flat
                prof = 32 * math.sin(math.pi * u / 0.35) if u < 0.35 else -14 * math.sin(math.pi * (u - 0.35) / 0.65)
                roll = roll * (1 - math.sin(math.pi * u)) + prof
        out[side] = (Vector((world.x, world.y + d, world.z)), yaw, roll)
    return out


def _ctrl_foot_basis(arm, side, pos, yaw):
    name = f"CTRL_IK_Foot.{side}"
    rest = arm.data.bones[name].matrix_local
    q = Quaternion((0, 0, 1), math.radians(yaw))
    m = Matrix.Translation(pos) @ q.to_matrix().to_4x4() @ rest.to_3x3().to_4x4()
    basis = rest.inverted() @ m   # parent (Root) is never posed
    return basis.to_translation(), basis.to_quaternion()


def _pole(arm, side, pos, yaw):
    """Knee target: in front of the foot at knee height, slightly outward."""
    s = 1 if side == "L" else -1
    out_yaw = math.radians(yaw + 8 * s)
    fwd = Vector((-math.sin(out_yaw), -math.cos(out_yaw), 0))
    p = Vector((pos.x, pos.y, 0.5)) + fwd * 0.8
    name = f"CTRL_Pole_Leg.{side}"
    return arm.data.bones[name].matrix_local.inverted() @ p


# ------------------------------------------------------------------ baking
def _channelbag(arm, act):
    arm.animation_data_create()
    arm.animation_data.action = act
    if arm.animation_data.action_slot is None:
        slot = act.slots.new(id_type="OBJECT", name=arm.name)
        arm.animation_data.action_slot = slot
    return anim_utils.action_ensure_channelbag_for_slot(act, arm.animation_data.action_slot)


def _write(cb, path, index, frames, values):
    fc = cb.fcurves.new(path, index=index) if index is not None else cb.fcurves.new(path)
    fc.keyframe_points.add(len(frames))
    co = []
    for f, v in zip(frames, values):
        co += [f, v]
    fc.keyframe_points.foreach_set("co", co)
    fc.keyframe_points.foreach_set("interpolation", [0] * len(frames))  # CONSTANT->LINEAR below
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    fc.update()


def bake(arm, clip: Clip):
    """Evaluate the clip per frame and write a dense action. Returns event data."""
    frames = list(range(int(clip.first), int(clip.last) + 1))
    times = [k[0] for k in clip.keys]
    tens = [k[2] for k in clip.keys]
    loop_len = (clip.last - clip.first) if clip.loop else None
    bones = [pb.name for pb in arm.pose.bones if not pb.name.startswith(("CTRL_", "MCH_"))]
    cols = {}
    for b in bones:
        qs = _align([k[1].rot.get(b, Quaternion()) for k in clip.keys])
        vecs = [Vector(q) for q in qs]
        lag = 0.0 if clip.loop else _lag(b, clip.drag)
        vals = []
        for f in frames:
            t = f - lag
            if not clip.loop:
                t = max(t, clip.first)
            v = _spline(times, vecs, tens, t, loop_len)
            vals.append(Quaternion(v).normalized())
        cols[b] = vals
    hips = [_spline(times, [k[1].hips_loc for k in clip.keys], tens, f, loop_len) for f in frames]
    feet = {f: _feet_at(clip, f) for f in frames}

    act = bpy.data.actions.new(clip.name)
    act.use_fake_user = True
    cb = _channelbag(arm, act)
    for b, vals in cols.items():
        for i in range(4):
            _write(cb, f'pose.bones["{b}"].rotation_quaternion', i, frames, [q[i] for q in vals])
    for i in range(3):
        _write(cb, 'pose.bones["Hips"].location', i, frames, [h[i] for h in hips])
    for side in ("L", "R"):
        locs, rots, rolls, poles = [], [], [], []
        for f in frames:
            pos, yaw, roll = feet[f][side]
            loc, q = _ctrl_foot_basis(arm, side, pos, yaw)
            locs.append(loc)
            rots.append(q)
            rolls.append(roll)
            poles.append(_pole(arm, side, pos, yaw))
        rots = _align(rots)
        ctrl = f"CTRL_IK_Foot.{side}"
        for i in range(3):
            _write(cb, f'pose.bones["{ctrl}"].location', i, frames, [v[i] for v in locs])
            _write(cb, f'pose.bones["CTRL_Pole_Leg.{side}"].location', i, frames, [v[i] for v in poles])
        for i in range(4):
            _write(cb, f'pose.bones["{ctrl}"].rotation_quaternion', i, frames, [q[i] for q in rots])
        _write(cb, f'pose.bones["{ctrl}"]["roll"]', None, frames, rolls)
    for prop, v in (("ik_leg_L", 1.0), ("ik_leg_R", 1.0), ("ik_arm_L", 0.0), ("ik_arm_R", 0.0)):
        _write(cb, f'["{prop}"]', None, frames, [v] * len(frames))
    act.use_frame_range = True
    act.frame_start, act.frame_end = frames[0], frames[-1]
    if clip.loop:
        act.use_cyclic = True

    sec = lambda f: round((f - clip.first) / FPS, 4)  # noqa: E731
    ev = {"length": sec(frames[-1]), "loop": clip.loop,
          "root": [round(_root_at(clip, f) - _root_at(clip, clip.first), 4) for f in frames]}
    if clip.hits:
        ev["hits"] = [sec(h) for h in clip.hits]
    if clip.link is not None:
        ev["link"] = sec(clip.link)
    if clip.trails:
        ev["trails"] = {s: [sec(a), sec(b)] for s, (a, b) in clip.trails.items()}
    if clip.loop:
        d = clip.root[-1][1] - clip.root[0][1]
        ev["speed"] = round(d / (loop_len / FPS), 3)
    ev.update(clip.meta)
    return ev


def bake_pose(arm, pose: Pose, name):
    """A two-frame hold so the pose library travels in the glTF like any clip."""
    clip = Clip(name, [(1, pose, 1.0), (2, pose, 1.0)], meta={"pose": True})
    return bake(arm, clip)
