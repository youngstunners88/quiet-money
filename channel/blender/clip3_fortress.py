"""Clip 3 (myth): the 'half-sold' asset. A sphere half gold, half dull grey (sold); the grey half shatters and is
reclaimed as gold, then a fortress of gold towers rises round it. Taylor Swift buy-back / 'you can't get it back' myth."""
import bpy, bmesh, math, random, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import *
random.seed(5)
sc = reset()
G = gold(0.18)
grey = mat("Sold", (.04, .04, .045, 1), 0.3, 0.7)
floor(mat("Floor", (0.02, 0.018, 0.018, 1), 0.7, 0.12))
R = 1.5; Z = 1.9
def half(sign):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=64, ring_count=32, location=(0, 0, Z))
    o = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=(sign > 0), clear_outer=(sign < 0))
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges)
    bm.to_mesh(o.data); bm.free(); smooth(o); return o
gh = half(1); put(gh, G)           # gold half (x>0)
sh = half(-1); put(sh, grey)       # sold half (x<0)
# sold half hairline tension: drifts away, trembles
sh.location.x = 0; sh.keyframe_insert("location", frame=1)
for f in range(96, IMPACT, 3):
    a = (f - 96) / 48 * 0.03
    sh.location = (-(f - 96) / 48 * 0.18 + random.uniform(-a, a), random.uniform(-a, a), Z + random.uniform(-a, a)); sh.keyframe_insert("location", frame=f)
sh.hide_render = False; sh.keyframe_insert("hide_render", frame=IMPACT - 1)
sh.hide_render = True; sh.keyframe_insert("hide_render", frame=IMPACT)
# shards fly at impact
for i in range(70):
    u, v = random.random() * 2 - 1, random.random() * math.tau   # point on the -x hemisphere
    s_ = math.sqrt(1 - u * u)
    p = Vector((-abs(u) * R, math.cos(v) * s_ * R, Z + math.sin(v) * s_ * R))
    p.x -= 0.18
    bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.15, 0.4), location=p); c = bpy.context.object
    put(c, grey); c.rotation_euler = [random.random() * 3 for _ in range(3)]
    c.hide_render = True; c.keyframe_insert("hide_render", frame=IMPACT - 1)
    c.hide_render = False; c.keyframe_insert("hide_render", frame=IMPACT)
    c.keyframe_insert("location", frame=IMPACT); c.keyframe_insert("rotation_euler", frame=IMPACT)
    d = (p - Vector((0, 0, Z))).normalized()
    c.location = p + d * random.uniform(3, 7) + Vector((-2, 0, 0)); c.keyframe_insert("location", frame=IMPACT + 40)
    c.rotation_euler = [random.random() * 8 for _ in range(3)]; c.keyframe_insert("rotation_euler", frame=IMPACT + 40)
    c.scale = (1, 1, 1); c.keyframe_insert("scale", frame=IMPACT + 20)
    c.scale = (0, 0, 0); c.keyframe_insert("scale", frame=IMPACT + 40)
# reclaimed gold half grows in at impact
gh2 = half(-1); put(gh2, G)
gh2.scale = (0.01, 0.01, 0.01); gh2.keyframe_insert("scale", frame=IMPACT - 1)
gh2.scale = (1.08, 1.08, 1.08); gh2.keyframe_insert("scale", frame=IMPACT + 5)
gh2.scale = (1, 1, 1); gh2.keyframe_insert("scale", frame=IMPACT + 12)
# slow sphere turn: parent to an empty
rot = bpy.data.objects.new("Rot", None); bpy.context.collection.objects.link(rot); rot.location = (0, 0, Z)
bpy.context.view_layer.update()
for o in (gh, gh2):
    o.parent = rot; o.matrix_parent_inverse = rot.matrix_world.inverted()
rot.rotation_euler.z = 0; rot.keyframe_insert("rotation_euler", frame=1)
rot.keyframe_insert("rotation_euler", frame=IMPACT)
rot.rotation_euler.z = math.radians(120); rot.keyframe_insert("rotation_euler", frame=FRAMES)
# fortress: ring of gold towers rising after impact
for i in range(14):
    a = i / 14 * math.tau; rad = 3.7
    h = random.uniform(2.4, 3.8) if i % 2 == 0 else random.uniform(1.4, 2.0)
    x, y = math.cos(a) * rad, math.sin(a) * rad
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5 if i % 2 == 0 else 0.4, depth=h, vertices=24, location=(x, y, 0)); t = bpy.context.object
    put(t, G); smooth(t); t.scale.z = 0.001
    t0 = IMPACT + 4 + i * 2
    t.location.z = 0; t.keyframe_insert("location", frame=t0 - 1)
    t.scale.z = 0.001; t.keyframe_insert("scale", frame=t0 - 1)
    t.scale.z = 1; t.keyframe_insert("scale", frame=t0 + 18)
    t.location.z = h / 2; t.keyframe_insert("location", frame=t0 + 18)
    # crenel cap
    bpy.ops.mesh.primitive_cone_add(radius1=0.6 if i % 2 == 0 else 0.5, radius2=0.0, depth=0.7, vertices=24, location=(x, y, h + 0.35)); cap = bpy.context.object
    put(cap, mat("Cap", (.08, .06, .04, 1), 1, .3)); smooth(cap)
    cap.scale = (0, 0, 0); cap.keyframe_insert("scale", frame=t0 + 16)
    cap.scale = (1, 1, 1); cap.keyframe_insert("scale", frame=t0 + 22)
    # walls between towers
    a2 = (i + 1) / 14 * math.tau
    x2, y2 = math.cos(a2) * rad, math.sin(a2) * rad
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x + x2) / 2, (y + y2) / 2, 0.5)); w = bpy.context.object
    L = math.hypot(x2 - x, y2 - y); w.scale = (L, 0.25, 1.0); w.rotation_euler.z = math.atan2(y2 - y, x2 - x); put(w, G)
    w.location.z = -0.6; w.keyframe_insert("location", frame=t0 + 6)
    w.location.z = 0.5; w.keyframe_insert("location", frame=t0 + 22)
softbox((-6, -4, 4), 5, 4, target=(0, 0, 1.8)); softbox((6, 3, 3), 5, 3, target=(0, 0, 1.8))
light("AREA", (-4, -5, 5), 1500, (1, .7, .35), 3, target=(0, 0, Z))
light("AREA", (4, 5, 6), 1100, (1, .6, .25), 3, target=(0, 0, Z))
fl = light("POINT", (0, -1, Z), 0, (1, .72, .35), 1)
fl.data.energy = 0; fl.data.keyframe_insert("energy", frame=IMPACT - 1)
fl.data.energy = 14000; fl.data.keyframe_insert("energy", frame=IMPACT + 3)
fl.data.energy = 1800; fl.data.keyframe_insert("energy", frame=IMPACT + 40)
# camera: slow orbit-ish, pushes in at impact then pulls back to reveal the fortress
cam, tgt = camera((-2.5, -11, 3.5), (0, 0, Z), lens=55, fstop=2.2)
cam.keyframe_insert("location", frame=1)
cam.location = (1.8, -8.8, 3.0); cam.keyframe_insert("location", frame=IMPACT)
cam.location = (1.0, -14.5, 6.5); cam.keyframe_insert("location", frame=FRAMES)
tgt.location = (0, 0, Z); tgt.keyframe_insert("location", frame=1)
tgt.location = (0, 0, 2.2); tgt.keyframe_insert("location", frame=FRAMES)
for f in range(IMPACT, IMPACT + 10): shake(cam, f, 0.07 * (1 - (f - IMPACT) / 10))
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = "BEZIER"
        except Exception: pass
bpy.ops.wm.save_as_mainfile(filepath=__file__.rsplit("/", 1)[0] + "/half-sold-fortress.blend")
