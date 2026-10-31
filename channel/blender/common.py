"""Shared helpers for Quiet Money Blender clips (Blender 5.2, Eevee). 9:16, 8 s, 24 fps."""
import bpy, math, random
from mathutils import Vector

FPS, FRAMES = 24, 192
IMPACT = 144  # last third starts at 128

def reset(res=(1080, 1920), samples=24):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FRAMES
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng; break
        except TypeError:
            pass
    try: sc.eevee.taa_render_samples = samples
    except Exception: pass
    for a, v in (("use_raytracing", False), ("use_shadows", True)):
        try: setattr(sc.eevee, a, v)
        except Exception: pass
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - High Contrast"
    except Exception: pass
    w = bpy.data.worlds.new("W"); w.use_nodes = True; sc.world = w
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.05, 0.032, 0.018, 1); bg.inputs[1].default_value = 0.6
    return sc

def mat(name, color, metal=0.0, rough=0.4, emit=None, estr=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = color
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = estr
    return m

def gold(rough=0.22): return mat("Gold", (1.0, 0.66, 0.2, 1), 1.0, rough)
def glow(strength=6): return mat("Glow", (1, .6, .2, 1), 0, 0.5, (1.0, 0.62, 0.18, 1), strength)
def darkfloor():
    return mat("Floor", (0.02, 0.018, 0.018, 1), 0.6, 0.18)

def put(obj, m):
    obj.data.materials.clear(); obj.data.materials.append(m); return obj

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True
    return o

def floor(m=None, z=0):
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, z))
    f = bpy.context.object; put(f, m or darkfloor()); return f

def key(obj, frame, **kw):
    for k, v in kw.items():
        setattr(obj, k, v)
        obj.keyframe_insert(k, frame=frame)

def ease(obj):
    """Smooth (bezier) interpolation everywhere."""
    ad = obj.animation_data
    if not ad or not ad.action: return
    try:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "BEZIER"
    except Exception:
        pass

def light(kind, loc, energy, color=(1, .7, .35), size=2, rot=None, target=None):
    d = bpy.data.lights.new(kind, kind); d.energy = energy; d.color = color
    if kind == "AREA": d.size = size
    if kind == "SPOT": d.spot_size = math.radians(50); d.spot_blend = 0.6
    o = bpy.data.objects.new(kind, d); bpy.context.collection.objects.link(o); o.location = loc
    if target:
        c = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(c); c.location = target
        tc = o.constraints.new("TRACK_TO"); tc.target = c; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
    return o

def camera(loc, target, lens=70, fstop=1.8):
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    co = bpy.data.objects.new("Cam", cd); bpy.context.collection.objects.link(co)
    co.location = loc
    tgt = bpy.data.objects.new("CamTarget", None); bpy.context.collection.objects.link(tgt)
    tgt.location = target
    tc = co.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
    cd.dof.focus_object = tgt
    bpy.context.scene.camera = co
    return co, tgt

def shake(obj, frame, amp, prop="location"):
    random.seed(frame)
    v = getattr(obj, prop).copy()
    setattr(obj, prop, v + Vector([random.uniform(-amp, amp) for _ in range(3)]))
    obj.keyframe_insert(prop, frame=frame)
    setattr(obj, prop, v)

def setup_output(path):
    sc = bpy.context.scene
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path

def softbox(loc, size, strength=8, color=(1, .72, .4), target=(0, 0, 1)):
    """Emissive panel so metals have something warm to reflect."""
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    o = bpy.context.object
    o.data.materials.append(mat("SB", (0, 0, 0, 1), 0, 1, color + (1,), strength))
    c = bpy.data.objects.new("T", None); bpy.context.collection.objects.link(c); c.location = target
    tc = o.constraints.new("TRACK_TO"); tc.target = c; tc.track_axis = "TRACK_Z"; tc.up_axis = "UP_Y"
    o.visible_camera = False
    return o
