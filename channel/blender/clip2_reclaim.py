"""Clip 2 (escape): a master-recording vinyl locked in a cage of bars breaks free and rises in gold light. Jay-Z own-the-master."""
import bpy, math, random, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import *
random.seed(11)
sc = reset()
G = gold(); steel = mat("Steel", (.07, .065, .06, 1), 1, .28)
floor(mat("Floor", (0.02, 0.018, 0.018, 1), 0.7, 0.12))
# vinyl, lying flat and hovering
bpy.ops.mesh.primitive_cylinder_add(radius=1.7, depth=0.05, vertices=96, location=(0, 0, 1.0))
vinyl = bpy.context.object; put(vinyl, mat("Vinyl", (.01, .01, .012, 1), 0.3, 0.12)); smooth(vinyl)
for i in range(14):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.7 + i * 0.062, minor_radius=0.006, major_segments=96, minor_segments=6, location=(0, 0, 1.026))
    t = bpy.context.object; put(t, mat("Groove", (.03, .03, .03, 1), 0.9, 0.2)); t.parent = vinyl; t.matrix_parent_inverse = vinyl.matrix_world.inverted()
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=0.06, vertices=64, location=(0, 0, 1.03)); lab = bpy.context.object
put(lab, G); lab.parent = vinyl; lab.matrix_parent_inverse = vinyl.matrix_world.inverted(); smooth(lab)
bpy.ops.mesh.primitive_torus_add(major_radius=1.7, minor_radius=0.03, major_segments=96, location=(0, 0, 1.0)); rimg = bpy.context.object
put(rimg, glow(0)); rimg.parent = vinyl; rimg.matrix_parent_inverse = vinyl.matrix_world.inverted()
em = next(n for n in rimg.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"]
em.default_value = 0; em.keyframe_insert("default_value", frame=IMPACT - 2)
em.default_value = 5; em.keyframe_insert("default_value", frame=IMPACT + 8)
# spin: slow, then accelerates
vinyl.rotation_euler.z = 0; vinyl.keyframe_insert("rotation_euler", frame=1)
vinyl.rotation_euler.z = math.radians(300); vinyl.keyframe_insert("rotation_euler", frame=IMPACT)
vinyl.rotation_euler.z = math.radians(300 + 900); vinyl.keyframe_insert("rotation_euler", frame=FRAMES)
vinyl.location.z = 1.0; vinyl.keyframe_insert("location", frame=IMPACT - 1)
vinyl.location.z = 2.6; vinyl.keyframe_insert("location", frame=FRAMES)
# the cage
bars = []
N = 18
for i in range(N):
    a = i / N * math.tau
    x, y = math.cos(a) * 2.2, math.sin(a) * 2.2
    bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=2.6, vertices=16, location=(x, y, 1.35)); b = bpy.context.object
    put(b, steel); smooth(b); bars.append((b, a))
for z in (0.05, 2.65):
    bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.1, major_segments=64, location=(0, 0, z)); r = bpy.context.object
    put(r, steel); smooth(r); bars.append((r, None))
for b, a in bars:
    p0, r0 = b.location.copy(), b.rotation_euler.copy()
    b.keyframe_insert("location", frame=1); b.keyframe_insert("rotation_euler", frame=1)
    # tension: tiny rattle building up
    for f in range(100, IMPACT, 4):
        amp = 0.004 + (f - 100) / 44 * 0.03
        b.location = p0 + Vector((random.uniform(-amp, amp), random.uniform(-amp, amp), 0)); b.keyframe_insert("location", frame=f)
    b.location = p0; b.keyframe_insert("location", frame=IMPACT - 1)
    b.rotation_euler = r0; b.keyframe_insert("rotation_euler", frame=IMPACT - 1)
    # burst
    d = Vector((math.cos(a), math.sin(a), 0)) if a is not None else Vector((0, 0, 0))
    far = p0 + d * random.uniform(5, 9) + Vector((0, 0, random.uniform(-0.3, 2) if a is not None else (4 if p0.z > 2 else -0.0)))
    if a is None and p0.z > 2: far = p0 + Vector((random.uniform(-3, 3), 6, 1))
    b.location = far; b.keyframe_insert("location", frame=IMPACT + 22)
    b.rotation_euler = (r0[0] + random.uniform(-3, 3), r0[1] + random.uniform(-3, 3), r0[2] + random.uniform(-3, 3)); b.keyframe_insert("rotation_euler", frame=IMPACT + 22)
# sparks rising
for i in range(70):
    a = random.random() * math.tau; r = random.random() * 2.0
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.012, 0.03), subdivisions=1, location=(math.cos(a) * r, math.sin(a) * r, 1.0)); s = bpy.context.object
    put(s, glow(5)); s.hide_render = True; s.keyframe_insert("hide_render", frame=IMPACT - 1)
    s.hide_render = False; s.keyframe_insert("hide_render", frame=IMPACT)
    s.location.z = 1.0; s.keyframe_insert("location", frame=IMPACT)
    s.location = (math.cos(a) * r * 1.6, math.sin(a) * r * 1.6, random.uniform(5, 9)); s.keyframe_insert("location", frame=FRAMES)
softbox((-6, -3, 4), 5, 9, target=(0, 0, 1.5)); softbox((6, 3, 3), 5, 6, target=(0, 0, 1.5))
light("AREA", (-4, -4, 5), 1500, (1, .7, .35), 3, target=(0, 0, 1.2))
light("AREA", (4, 5, 4), 1100, (1, .6, .25), 3, target=(0, 0, 1.2))
fl = light("POINT", (0, 0, 2.2), 0, (1, .7, .3), 1)
fl.data.energy = 0; fl.data.keyframe_insert("energy", frame=IMPACT - 1)
fl.data.energy = 9000; fl.data.keyframe_insert("energy", frame=IMPACT + 3)
fl.data.energy = 1500; fl.data.keyframe_insert("energy", frame=FRAMES)
cam, tgt = camera((1.5, -9, 7.5), (0, 0, 1.3), lens=48, fstop=2.4)
cam.keyframe_insert("location", frame=1)
cam.location = (-1.0, -7.8, 6.0); cam.keyframe_insert("location", frame=IMPACT)
cam.location = (0, -6.8, 4.2); cam.keyframe_insert("location", frame=FRAMES)
tgt.location = (0, 0, 1.2); tgt.keyframe_insert("location", frame=1)
tgt.location = (0, 0, 1.4); tgt.keyframe_insert("location", frame=IMPACT)
tgt.location = (0, 0, 2.6); tgt.keyframe_insert("location", frame=FRAMES)
for f in range(IMPACT, IMPACT + 10): shake(cam, f, 0.07 * (1 - (f - IMPACT) / 10))
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = "BEZIER"
        except Exception: pass
bpy.ops.wm.save_as_mainfile(filepath=__file__.rsplit("/", 1)[0] + "/vinyl-reclaimed.blend")
