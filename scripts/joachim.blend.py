# Bygger Joachim i 3D og eksporterer public/joachim.glb.
# Kjør: blender -b --factory-startup -P scripts/joachim.blend.py -- [forhåndsvisning.png]
# Figuren ser mot -Y i Blender, som blir +Z (mot kameraet) i glTF.
# Nodene Head, Jaw, ArmL og ArmR er dreiepunkter spillet animerer.
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix

random.seed(7)
OUT = __file__.replace('scripts/joachim.blend.py', 'public/joachim.glb')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = ARGS[0] if ARGS else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def mat(name, hexcol, rough=0.7, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    b.inputs['Base Color'].default_value = (*lin, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

M = {
    'skin': mat('Skin', '#eaa98a', 0.55), 'hair': mat('Hair', '#8e8881', 0.95), 'beard': mat('Beard', '#6e5c4b', 0.95),
    'jacket': mat('Jacket', '#566b2c', 0.85), 'shirt': mat('Shirt', '#17161b', 0.75), 'jeans': mat('Jeans', '#2f4f86', 0.85),
    'shoe': mat('Shoe', '#5b3620', 0.45), 'leather': mat('Leather', '#8b5327', 0.5), 'black': mat('Frame', '#0b0b0d', 0.2),
    'white': mat('EyeWhite', '#f5f1ea', 0.3), 'pupil': mat('Pupil', '#2a1d14', 0.15), 'mouth': mat('Mouth', '#4d1818', 0.6),
    'lens': mat('Lens', '#dcecff', 0.03), 'brass': mat('Brass', '#d9a84b', 0.3, 1.0), 'button': mat('Button', '#3d4a1f', 0.5),
}
M['lens'].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.22
RAINBOW = [mat('Stripe' + str(i), c, 0.6) for i, c in enumerate(['#e5312f', '#f28a1c', '#f5d01f', '#46b347', '#2c6bd4'])]

def new_obj(name, me, material):
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    if material: me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    return ob

def lathe(name, profile, material, seg=36, sx=1.0, sy=1.0, cut=None, shape=None):
    """Dreier en profil (r, z) rundt Z. cut: halv åpning i grader rundt fronten (-Y). shape(x, y, z) kan bule ut."""
    bm = bmesh.new(); rings = []
    for r, z in profile:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = math.sin(a) * r * sx, -math.cos(a) * r * sy
            if shape: x, y, z2 = shape(x, y, z)
            else: z2 = z
            ring.append(bm.verts.new((x, y, z2)))
        rings.append(ring)
    for j in range(len(rings) - 1):
        for i in range(seg):
            a = 2 * math.pi * (i + 0.5) / seg
            if cut and (a < math.radians(cut) or a > 2 * math.pi - math.radians(cut)): continue
            bm.faces.new((rings[j][i], rings[j][(i + 1) % seg], rings[j + 1][(i + 1) % seg], rings[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me, material)

def sphere(name, material, loc, size, seg=24, keep=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1)
    for v in bm.verts: v.co = Vector((v.co.x * size[0] + loc[0], v.co.y * size[1] + loc[1], v.co.z * size[2] + loc[2]))
    if keep:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f.calc_center_median())], context='FACES')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me, material)

def fluffy(ob, scale=0.018, strength=0.018, subsurf=1):
    """Krøllete overflate: del opp og dytt punktene ut med støy."""
    if subsurf:
        s = ob.modifiers.new('sub', 'SUBSURF'); s.levels = subsurf; s.render_levels = subsurf
    tex = bpy.data.textures.new(ob.name + '_curl', 'CLOUDS'); tex.noise_scale = scale; tex.noise_depth = 2
    d = ob.modifiers.new('disp', 'DISPLACE'); d.texture = tex; d.strength = strength; d.mid_level = 0.5; d.texture_coords = 'GLOBAL'
    return ob

def tube(name, material, pts, radii, seg=16):
    """Rør langs punkter med varierende radius (armer)."""
    bm = bmesh.new(); rings = []
    for k, (p, r) in enumerate(zip(pts, radii)):
        p = Vector(p)
        t = (Vector(pts[min(k + 1, len(pts) - 1)]) - Vector(pts[max(k - 1, 0)])).normalized()
        n1 = t.orthogonal().normalized(); n2 = t.cross(n1)
        rings.append([bm.verts.new(p + (n1 * math.cos(2 * math.pi * i / seg) + n2 * math.sin(2 * math.pi * i / seg)) * r) for i in range(seg)])
    for j in range(len(rings) - 1):
        for i in range(seg):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % seg], rings[j + 1][(i + 1) % seg], rings[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return new_obj(name, me, material)

def curve_mesh(name, pts, bevel, material, closed=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    sp.use_cyclic_u = closed; cu.bevel_depth = bevel; cu.bevel_resolution = 2
    ob = bpy.data.objects.new(name + '_c', cu); scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    return new_obj(name, me, material)

def pivot(name, loc, parent=None):
    e = bpy.data.objects.new(name, None); e.location = loc; scene.collection.objects.link(e)
    if parent: attach(e, parent)
    return e

def attach(obj, parent):
    bpy.context.view_layer.update()
    mw = obj.matrix_world.copy(); obj.parent = parent; obj.matrix_world = mw

root = pivot('Joachim', (0, 0, 0))

# ---------- bein og sko: kraftige, litt korte
for sx in (-1, 1):
    attach(lathe('Leg', [(0.08, 0.07), (0.088, 0.3), (0.1, 0.55), (0.115, 0.8), (0.12, 0.88)], M['jeans'], 20,
                 shape=lambda x, y, z, sx=sx: (x * 0.9 + sx * (0.092 + (z - 0.07) * 0.015), y * 0.9, z)), root)
    attach(sphere('Shoe', M['shoe'], (sx * 0.093, -0.045, 0.045), (0.07, 0.135, 0.05)), root)

# ---------- kropp: svart t-skjorte over en god mage, åpen grønn jakke utenpå
SLIM = 0.84
def belly(x, y, z):
    if y < 0: y *= 1 + 0.17 * math.exp(-((z - 1.0) / 0.13) ** 2)
    return x, y, z
def fine(profile, step=0.0125):
    out = []
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        n = max(1, int(abs(z1 - z0) / step))
        out += [(r0 + (r1 - r0) * k / n, z0 + (z1 - z0) * k / n) for k in range(n)]
    return out + [profile[-1]]
torso = fine([(r * SLIM, z) for r, z in [(0.2, 0.82), (0.25, 0.88), (0.28, 0.97), (0.29, 1.06), (0.28, 1.16), (0.26, 1.27), (0.245, 1.35), (0.2, 1.42), (0.11, 1.47), (0.06, 1.49)]])
shirt = lathe('Shirt', torso, M['shirt'], 40, 1.0, 0.8, shape=belly)
for m in RAINBOW: shirt.data.materials.append(m)
for p in shirt.data.polygons:
    c = p.center
    a = abs(math.atan2(c.x, -c.y))
    if a < math.radians(24) and 1.12 <= c.z < 1.245:
        p.material_index = 1 + min(4, int((1.245 - c.z) / 0.025))
attach(shirt, root)
jacket = lathe('Jacket', [(r + 0.028, z) for r, z in torso if z < 1.46] + [(0.14, 1.47)], M['jacket'], 40, 1.0, 0.82, cut=30, shape=belly)
sol = jacket.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.018; sol.offset = 1
attach(jacket, root)
# krage og brystlommer
attach(lathe('Collar', [(0.13, 1.44), (0.15, 1.49), (0.12, 1.53)], M['jacket'], 32, 1.0, 0.9, cut=55), root)
for sx in (-1, 1):
    a = math.radians(48) * sx
    attach(sphere('Pocket', M['jacket'], (math.sin(a) * 0.25, -math.cos(a) * 0.22, 1.24), (0.055, 0.02, 0.045), 12), root)
    attach(sphere('Button', M['button'], (sx * 0.115, -0.2, 1.12), (0.01, 0.006, 0.01), 8), root)
# skulderveske med rem på skrå over brystet
attach(curve_mesh('Strap', [(0.17, -0.12, 1.44), (0.085, -0.205, 1.3), (-0.045, -0.235, 1.13), (-0.16, -0.21, 1.0), (-0.24, -0.1, 0.95)], 0.013, M['leather']), root)
attach(sphere('Bag', M['leather'], (-0.26, -0.02, 0.9), (0.055, 0.14, 0.11), 16), root)
attach(sphere('Buckle', M['brass'], (-0.31, -0.03, 0.93), (0.006, 0.02, 0.016), 10), root)

# ---------- armer: dreiepunkt i skulderen, litt bøyd i albuen
for side, sx in (('L', 1), ('R', -1)):
    arm = pivot('Arm' + side, (sx * 0.235, 0, 1.38), root)
    pts = [(sx * 0.235, 0, 1.38), (sx * 0.27, -0.01, 1.25), (sx * 0.29, -0.02, 1.12), (sx * 0.3, -0.05, 1.0), (sx * 0.3, -0.08, 0.9)]
    attach(tube('Sleeve' + side, M['jacket'], pts, [0.074, 0.07, 0.064, 0.058, 0.056]), arm)
    attach(sphere('Hand' + side, M['skin'], (sx * 0.3, -0.09, 0.84), (0.045, 0.04, 0.06)), arm)
    attach(sphere('Thumb' + side, M['skin'], (sx * 0.277, -0.125, 0.86), (0.017, 0.017, 0.028), 12), arm)

# ---------- hode: dreiepunkt i nakken
head = pivot('Head', (0, 0, 1.49), root)
H = lambda o: attach(o, head)
H(lathe('Neck', [(0.07, 1.46), (0.072, 1.56)], M['skin'], 16))
H(sphere('Face', M['skin'], (0, 0, 1.665), (0.118, 0.128, 0.145), 32))
H(sphere('Nose', M['skin'], (0, -0.135, 1.64), (0.026, 0.03, 0.032)))
H(sphere('NoseTip', M['skin'], (0, -0.15, 1.625), (0.022, 0.02, 0.02)))
for sx in (-1, 1):
    H(sphere('Ear', M['skin'], (sx * 0.12, 0.005, 1.655), (0.02, 0.035, 0.048), 16))
    H(sphere('Cheek', M['skin'], (sx * 0.066, -0.098, 1.628), (0.034, 0.022, 0.024), 16))
# vikende grå krøller rundt sider og bakhode, bar blank isse
H(fluffy(lathe('Hair', [(0.116, 1.59), (0.15, 1.62), (0.165, 1.68), (0.158, 1.73), (0.13, 1.77), (0.09, 1.795)], M['hair'], 40, 1.0, 1.05, cut=58), 0.016, 0.04, 2))
# buskete skjegg fra øre til øre, haken er egen del så den kan gå opp og ned når han prater
keep = lambda c: c.z < 1.585 + 0.085 * min(1, abs(c.x) / 0.11) and c.y < 0.06
beard = fluffy(sphere('BeardFull', M['beard'], (0, -0.045, 1.5), (0.14, 0.125, 0.19), 28, keep), 0.022, 0.028)
bpy.context.view_layer.objects.active = beard
for mname in [m.name for m in beard.modifiers]: bpy.ops.object.modifier_apply(modifier=mname)
bm = bmesh.new(); bm.from_mesh(beard.data)
# munnåpning i skjegget rett under barten
bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x) < 0.03 and 1.553 < f.calc_center_median().z < 1.582 and f.calc_center_median().y < -0.11], context='FACES')
lower = bm.copy()
SPLIT = 1.566
# bare midten av skjegget under munnen følger kjeven; sidene sitter fast
moving = lambda c: c.z < SPLIT and abs(c.x) < 0.075 and c.y < -0.07
bmesh.ops.delete(bm, geom=[f for f in bm.faces if moving(f.calc_center_median())], context='FACES')
bmesh.ops.delete(lower, geom=[f for f in lower.faces if not moving(f.calc_center_median())], context='FACES')
bm.to_mesh(beard.data); bm.free(); beard.name = 'Beard'
chin_me = bpy.data.meshes.new('Chin'); lower.to_mesh(chin_me); lower.free()
chin = new_obj('Chin', chin_me, None); chin.data.materials.append(M['beard'])
for v in chin.data.vertices: v.co = Vector((v.co.x * 1.04, (v.co.y + 0.045) * 1.02 - 0.045, v.co.z))
H(beard)
for sx in (-1, 1):
    H(fluffy(sphere('Moustache', M['beard'], (sx * 0.036, -0.143, 1.593), (0.046, 0.024, 0.02), 16), 0.012, 0.008))
H(sphere('Mouth', M['mouth'], (0, -0.13, 1.558), (0.05, 0.03, 0.03), 16))
H(sphere('Teeth', M['white'], (0, -0.152, 1.576), (0.021, 0.006, 0.005), 12))
jaw = pivot('Jaw', (0, 0.03, 1.605), head)
attach(sphere('Lip', mat('Lip', '#a3504a', 0.5), (0, -0.158, 1.558), (0.024, 0.01, 0.007), 14), jaw)
attach(chin, jaw)
# øyne, buskete bryn og de svarte rektangulære brillene
for sx in (-1, 1):
    H(sphere('Eye', M['white'], (sx * 0.045, -0.112, 1.681), (0.025, 0.013, 0.021), 16))
    H(sphere('Pupil', M['pupil'], (sx * 0.041, -0.1245, 1.68), (0.012, 0.004, 0.012), 12))
    H(fluffy(sphere('Brow', M['hair'], (sx * 0.046, -0.121, 1.717), (0.031, 0.012, 0.011), 14), 0.008, 0.006))
    w, h, r, cx, cy, cz = 0.037, 0.025, 0.007, sx * 0.047, -0.138, 1.68
    corner = lambda ox, oz, a0: [(cx + ox + math.cos(a0 + k * math.pi / 8) * r, cy, cz + oz + math.sin(a0 + k * math.pi / 8) * r) for k in range(5)]
    rect = corner(w - r, h - r, 0) + corner(-w + r, h - r, math.pi / 2) + corner(-w + r, -h + r, math.pi) + corner(w - r, -h + r, 1.5 * math.pi)
    H(curve_mesh('Frame', rect, 0.0055, M['black'], closed=True))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)
    for v in bm.verts: v.co = Vector((cx + v.co.x * w, cy + 0.002, cz + v.co.y * h))
    me = bpy.data.meshes.new('Lens'); bm.to_mesh(me); bm.free(); H(new_obj('Lens', me, M['lens']))
    H(curve_mesh('Temple', [(sx * 0.084, -0.138, 1.688), (sx * 0.121, -0.07, 1.69), (sx * 0.124, 0.0, 1.67)], 0.004, M['black']))
H(curve_mesh('Bridge', [(-0.011, -0.141, 1.686), (0, -0.145, 1.69), (0.011, -0.141, 1.686)], 0.0045, M['black']))

# ---------- bruk modifikatorer og eksporter
bpy.context.view_layer.update()
for o in list(scene.objects):
    if o.type == 'MESH' and o.modifiers:
        bpy.context.view_layer.objects.active = o
        for mname in [m.name for m in o.modifiers]: bpy.ops.object.modifier_apply(modifier=mname)
# tette masker (hår, skjegg) tynnes ut så fila holder seg liten
for o in list(scene.objects):
    if o.type == 'MESH':
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        if n > 2500:
            bpy.context.view_layer.objects.active = o
            d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = 2500 / n
            bpy.ops.object.modifier_apply(modifier=d.name)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in scene.objects if o.type == 'MESH')
print('JOACHIM triangles:', tris)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=True)
print('JOACHIM exported', OUT)

if PREVIEW:
    for i, (loc, rot) in enumerate((((1.2, -2.7, 1.5), (86, 0, 24)), ((0.0, -1.1, 1.64), (90, 0, 0)), ((0.0, -1.1, 1.64), (90, 0, 0)))):
        if i == 2: jaw.rotation_euler.x = 0.09
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam)
        cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]; cam.data.lens = 55 if i == 0 else 70
        scene.camera = cam
        if i == 0:
            for lloc, e in (((2, -2, 3), 180), ((-2.5, -1, 2), 70), ((0, 2.5, 2.5), 120)):
                l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA')); l.data.energy = e; l.data.size = 2
                l.location = lloc; l.rotation_euler = (Vector((0, 0, 1.1)) - Vector(lloc)).to_track_quat('-Z', 'Y').to_euler(); scene.collection.objects.link(l)
            world = bpy.data.worlds.new('w'); world.use_nodes = True
            world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.06, 0.09, 1); scene.world = world
            for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
                try: scene.render.engine = eng; break
                except TypeError: pass
            scene.view_settings.view_transform = 'Standard'
            scene.render.resolution_x, scene.render.resolution_y = 600, 800
        scene.render.filepath = PREVIEW.replace('.png', '_%d.png' % i)
        bpy.ops.render.render(write_still=True)
