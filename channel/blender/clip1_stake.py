"""Clip 1 (story): an ownership stake grows from a single coin into a vault. LeBron/Blaze equity-over-wages."""
import bpy, math, random, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import *
random.seed(7)
sc = reset()
G = gold()
floor()
# the single seed coin
def coin(loc, r=0.5, t=0.09):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=t, vertices=48, location=loc)
    o = bpy.context.object; put(o, G)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = t * 0.35; bv.segments = 3
    return o
seed = coin((0, 0, 0.6), 0.55); seed.rotation_euler = (math.radians(90), 0, 0)
key(seed, 1, rotation_euler=(math.radians(90), 0, 0), scale=(1, 1, 1))
# gentle spin
seed.rotation_euler = (math.radians(90), 0, math.radians(360 * 2)); seed.keyframe_insert("rotation_euler", frame=70)
for fc in seed.animation_data.action.fcurves if hasattr(seed.animation_data.action, "fcurves") else []:
    pass
# grows from the seed: spiral of coin stacks (the stake compounding) from frame 40 to 130
stacks = []
ring = [(0, 0)]
n = 0
for ringi, (rad, cnt) in enumerate([(1.4, 6), (2.6, 11), (3.8, 16)]):
    for i in range(cnt):
        a = i / cnt * math.tau + ringi * 0.4
        x, y = math.cos(a) * rad, math.sin(a) * rad
        h = int(3 + (3 - ringi) * 2 + random.random() * 3)
        t0 = 30 + ringi * 28 + i * 2
        for k in range(h):
            c = coin((x, y, 0.045 + k * 0.1), 0.42)
            c.rotation_euler.z = random.random()
            c.scale = (0, 0, 0); c.keyframe_insert("scale", frame=t0 + k * 2)
            c.scale = (1, 1, 1); c.keyframe_insert("scale", frame=t0 + k * 2 + 5)
            c.location.z += 0.4; # drop in
            z = 0.045 + k * 0.1
            c.location.z = z + 1.2; c.keyframe_insert("location", frame=t0 + k * 2)
            c.location.z = z; c.keyframe_insert("location", frame=t0 + k * 2 + 6)
            n += 1
# the vault: heavy ring door rises in the background at the impact
bpy.ops.mesh.primitive_torus_add(major_radius=3.2, minor_radius=0.35, major_segments=64, minor_segments=24, location=(0, 10, 3.2))
door = bpy.context.object; door.rotation_euler = (math.radians(90), 0, 0); put(door, mat("Steel", (.05, .045, .04, 1), 1, .3)); smooth(door)
bpy.ops.mesh.primitive_cylinder_add(radius=3.0, depth=0.5, vertices=64, location=(0, 10.3, 3.2))
disk = bpy.context.object; disk.rotation_euler = (math.radians(90), 0, 0); put(disk, mat("Steel2", (.08, .065, .04, 1), 1, .35)); smooth(disk)
bpy.ops.mesh.primitive_torus_add(major_radius=1.4, minor_radius=0.12, location=(0, 9.98, 3.2)); hub = bpy.context.object
hub.rotation_euler = (math.radians(90), 0, 0); put(hub, G); smooth(hub)
spokes = []
for i in range(6):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 6.95, 3.6)); s = bpy.context.object
    s.scale = (1.4, 0.07, 0.07); s.rotation_euler = (0, math.radians(i * 30), 0); s.rotation_euler.rotate_axis("X", 0); put(s, G); s.parent = hub; 
    s.matrix_parent_inverse = hub.matrix_world.inverted()
spk = [door, disk, hub]
for o in spk: o.scale = (0.62, 0.62, 0.62)
for o in spk:
    o.location.y += 8; o.keyframe_insert("location", frame=1)
    o.location.y -= 8; o.keyframe_insert("location", frame=IMPACT)
hub.rotation_euler.y = 0; hub.keyframe_insert("rotation_euler", frame=IMPACT)
hub.rotation_euler.y = math.radians(180); hub.keyframe_insert("rotation_euler", frame=FRAMES)
softbox((-7, -3, 4), 5, 10, target=(0, 0, 1)); softbox((7, 2, 3), 6, 6, target=(0, 1, 1))
# seed coin flies to become the vault hub
seed.location = (0, 0, 0.6); seed.keyframe_insert("location", frame=60)
seed.scale = (1, 1, 1); seed.keyframe_insert("scale", frame=60)
seed.location = (0, 9.6, 3.2); seed.keyframe_insert("location", frame=IMPACT)
seed.scale = (0.45, 0.45, 0.45); seed.keyframe_insert("scale", frame=IMPACT)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 10.8, 5), rotation=(math.radians(90), 0, 0)); wall = bpy.context.object
put(wall, mat("Wall", (.03, .026, .022, 1), 0.3, 0.8))
# lights
light("AREA", (-5, -2, 5), 1400, (1, .7, .35), 3, target=(0, 0, 0.5))      # warm rim
light("AREA", (5, 4, 5), 900, (1, .6, .25), 3, target=(0, 1, 1))
rim = light("AREA", (0, 14, 7), 3000, (1, .75, .4), 5, target=(0, 10, 3.2))
rim.data.energy = 0; rim.data.keyframe_insert("energy", frame=IMPACT - 2)
rim.data.energy = 9000; rim.data.keyframe_insert("energy", frame=IMPACT + 6)
rim.data.energy = 4000; rim.data.keyframe_insert("energy", frame=FRAMES)
# shockwave ring at impact
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.04, major_segments=96, location=(0, 0, 0.1)); sw = bpy.context.object
put(sw, glow(2.5)); sw.scale = (0.01, 0.01, 0.01); sw.keyframe_insert("scale", frame=IMPACT - 1)
sw.scale = (9, 9, 9); sw.keyframe_insert("scale", frame=IMPACT + 22)
sw.hide_render = True; sw.keyframe_insert("hide_render", frame=IMPACT - 2)
sw.hide_render = False; sw.keyframe_insert("hide_render", frame=IMPACT - 1)
sw.hide_render = True; sw.keyframe_insert("hide_render", frame=IMPACT + 23)
# camera: slow low dolly in, then push + shake at impact
cam, tgt = camera((2.0, -9, 2.2), (0, 0, 1.0), lens=60, fstop=2.0)
cam.keyframe_insert("location", frame=1)
cam.location = (-0.8, -6.2, 1.4); cam.keyframe_insert("location", frame=IMPACT)
cam.location = (0, -5.2, 1.7); cam.keyframe_insert("location", frame=FRAMES)
tgt.location = (0, 0, 0.6); tgt.keyframe_insert("location", frame=1)
tgt.location = (0, 3, 1.3); tgt.keyframe_insert("location", frame=IMPACT)
tgt.location = (0, 10, 2.8); tgt.keyframe_insert("location", frame=FRAMES)
for f in range(IMPACT, IMPACT + 10): shake(cam, f, 0.06 * (1 - (f - IMPACT) / 10))
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = "BEZIER"
        except Exception: pass
sc.camera = cam
bpy.ops.wm.save_as_mainfile(filepath=__file__.rsplit("/", 1)[0] + "/stake-to-vault.blend")
print("coins", n)
