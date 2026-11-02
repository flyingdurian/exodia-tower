"""Run from Blender 4.2+: builds LOOKDEV cameras, NOT fake Albedo geometry."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
def coll(name):
 c=bpy.data.collections.get(name) or bpy.data.collections.new(name)
 if c.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(c)
 return c
def aim(obj,point):obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
def scene_setup():
 sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE_NEXT';sc.render.film_transparent=True
 sc.render.resolution_x=sc.render.resolution_y=1024;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG'
 studio=coll('ALBEDO_A2_STUDIO_ONLY')
 for name,pos,power,col in [
   ('Key',(-3,-4,5),650,(.85,.89,1)),('Fill',(3,-2,3),450,(.96,.90,1)),
   ('Hair Rim',(2,3,4),700,(.74,.77,1))]:
  data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=3.5;data.color=col
  ob=bpy.data.objects.new(name,data);studio.objects.link(ob);ob.location=pos;aim(ob,(0,0,1))
 cameras={}
 for name,deg in [('front',0),('front_angle',45),('side',90),('back_angle',135),('back',180)]:
  data=bpy.data.cameras.new('A2 '+name);data.type='ORTHO';data.ortho_scale=2.5
  ob=bpy.data.objects.new('A2 '+name,data);studio.objects.link(ob)
  phi=math.radians(deg);ob.location=(5*math.sin(phi),-5*math.cos(phi),1);aim(ob,(0,0,1))
  cameras[name]=ob
 return cameras
def ref(path,name,x):
 if not path or not path.is_file():return
 bpy.ops.object.empty_add(type='IMAGE',location=(x,0,1.1));ob=bpy.context.object
 ob.name='REFERENCE ONLY '+name;ob.data=bpy.data.images.load(str(path.resolve()),check_existing=True)
 ob.empty_display_size=1.5;ob.rotation_euler=(math.pi/2,0,0);ob.hide_render=True
 ob['character_geometry']=False
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',type=Path);p.add_argument('--front',type=Path)
 p.add_argument('--turnaround',type=Path);p.add_argument('--out',type=Path,default=Path('A2_Studio'))
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 a.out.mkdir(parents=True,exist_ok=True);cams=scene_setup()
 ref(a.front,'front painting',-3.4);ref(a.turnaround,'three-view sheet',3.4)
 if a.model:
  if not a.model.is_file() or a.model.suffix.lower()!='.glb':raise ValueError('Real GLB candidate required')
  before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(a.model.resolve()))
  imported=[ob for ob in bpy.data.objects if ob not in before and ob.type=='MESH']
  if not imported:raise ValueError('Candidate has no 3D mesh')
  corners=[ob.matrix_world@Vector(c) for ob in imported for c in ob.bound_box]
  center=Vector(((min(v.x for v in corners)+max(v.x for v in corners))/2,
    (min(v.y for v in corners)+max(v.y for v in corners))/2,
    (min(v.z for v in corners)+max(v.z for v in corners))/2))
  span=max(max(v.z for v in corners)-min(v.z for v in corners),.1)
  for name,cam in cams.items():
   phi=math.radians({'front':0,'front_angle':45,'side':90,'back_angle':135,'back':180}[name])
   cam.location=center+Vector((5*math.sin(phi),-5*math.cos(phi),0))
   cam.data.ortho_scale=span*1.3;aim(cam,center);bpy.context.scene.camera=cam
   bpy.context.scene.render.filepath=str((a.out/(name+'.png')).resolve())
   bpy.ops.render.render(write_still=True)
 bpy.context.scene.camera=cams['front']
 bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'Albedo_A2_lookdev.blend').resolve()))
 print('Unanimated model review studio ready; no approved model automatically created.')
if __name__=='__main__':main()
