# Gjør Pixal3D-modellen av Joachim klar for spillet: snur ham mot kameraet, føtter i origo,
# 1,8 m høy, tynner ut masken og krymper teksturene. Skriver ut hvor nakke og munn er,
# som spillets skygge-kode bruker til å vri hodet og åpne munnen.
# Kjør: blender -b --factory-startup -P scripts/joachim_prep.blend.py -- inn.glb public/joachim.glb [dreiing° nakke munn]
# nakke og munn er andel av høyden, målt på en forfra-render av modellen.
import bpy, sys, math
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index('--') + 1:]
FACES, TEX = 30000, 1024
TURN = math.radians(float(a[2])) if len(a) > 2 else 0.0
NECK_F, MOUTH_F = (float(a[3]), float(a[4])) if len(a) > 4 else (0.73, 0.805)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = ob.data
# snu mot -Y (som blir +Z mot kameraet i glTF), føttene i origo, 1,8 m høy
me.transform(Matrix.Rotation(TURN, 4, 'Z'))
vs = [v.co for v in me.vertices]
lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
k = 1.8 / (hi.z - lo.z)
me.transform(Matrix.Scale(k, 4) @ Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
# nakken er under skjegget, munnen litt over; ansiktet er det som stikker lengst fram i munnhøyde
NECK, MOUTH = NECK_F * 1.8, MOUTH_F * 1.8
band = [v.co for v in me.vertices if abs(v.co.z - MOUTH) < 0.03]
front = min(v.y for v in band)
fx = sum(v.x for v in band if v.y < front + 0.03) / max(1, len([v for v in band if v.y < front + 0.03]))
head = [v.co for v in me.vertices if v.co.z > NECK]
hc = sum((v for v in head), Vector()) / len(head)
d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = min(1, FACES / len(me.polygons))
bpy.ops.object.modifier_apply(modifier=d.name)
for img in bpy.data.images:
    if img.size[0] > TEX: img.scale(TEX, TEX)
# glTF: x samme, opp = Blender z, fram = -Blender y
print('JOACHIM faces', len(me.polygons), 'neckY %.3f mouthY %.3f faceZ %.3f faceX %.3f headX %.3f headZ %.3f' % (NECK, MOUTH, -front, fx, hc.x, -hc.y))
bpy.ops.export_scene.gltf(filepath=a[1], export_format='GLB', export_image_format='JPEG', export_jpeg_quality=85, export_yup=True)
