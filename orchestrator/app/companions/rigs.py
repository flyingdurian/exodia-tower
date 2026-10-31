"""Animation data contracts for all ten agents. Portraits are NOT rigged assets."""
import json
from pathlib import Path

BONE_TREE = {"root":None,"hips":"root","torso":"hips","neck":"torso","head":"neck","hair_back":"head","hair_front":"head","eye_left":"head","eye_right":"head","mouth":"head","upper_arm_left":"torso","forearm_left":"upper_arm_left","hand_left":"forearm_left","upper_arm_right":"torso","forearm_right":"upper_arm_right","hand_right":"forearm_right","thigh_left":"hips","shin_left":"thigh_left","foot_left":"shin_left","thigh_right":"hips","shin_right":"thigh_right","foot_right":"shin_right"}
ANCHORS = {"root":[0,0],"hips":[0,-16],"torso":[0,-15],"neck":[0,-36],"head":[0,-8],"hair_back":[0,-20],"hair_front":[0,-30],"eye_left":[-10,-9],"eye_right":[10,-9],"mouth":[0,3],"upper_arm_left":[-24,-34],"forearm_left":[-10,24],"hand_left":[-3,22],"upper_arm_right":[24,-34],"forearm_right":[10,24],"hand_right":[3,22],"thigh_left":[-12,5],"shin_left":[-4,35],"foot_left":[0,30],"thigh_right":[12,5],"shin_right":[4,35],"foot_right":[0,30]}
POSES = {"neutral":{},"happy":{"head":-5,"upper_arm_left":-18,"upper_arm_right":18},"excited":{"head":-7,"upper_arm_left":-95,"upper_arm_right":95,"forearm_left":-35,"forearm_right":35},"proud":{"torso":-5,"head":5,"upper_arm_left":-18,"upper_arm_right":18},"curious":{"head":15,"torso":5,"upper_arm_right":-15},"wonder":{"head":-16,"upper_arm_left":-15,"upper_arm_right":-35},"thinking":{"head":12,"upper_arm_right":-45,"forearm_right":-85},"processing":{"head":-5,"upper_arm_left":-25,"forearm_left":-80},"concentrating":{"torso":8,"head":-8,"upper_arm_left":-30},"working":{"torso":8,"upper_arm_left":-50,"upper_arm_right":35,"forearm_left":-50,"forearm_right":45},"speaking":{"head":-4,"upper_arm_right":-35,"forearm_right":-35},"annoyed":{"head":12,"upper_arm_left":20,"upper_arm_right":-20},"angry":{"torso":-8,"head":-12,"upper_arm_left":20,"upper_arm_right":-20},"disappointed":{"head":20,"torso":12,"upper_arm_left":12,"upper_arm_right":-12},"sad":{"head":22,"torso":18,"upper_arm_left":15,"upper_arm_right":-15},"hurt":{"torso":20,"head":-12,"upper_arm_left":-55,"forearm_left":-60},"pain":{"torso":28,"head":-24,"upper_arm_left":-30,"upper_arm_right":40},"alarmed":{"head":-15,"upper_arm_left":-70,"upper_arm_right":50},"panic":{"head":-17,"upper_arm_left":-75,"upper_arm_right":70,"forearm_left":-35,"forearm_right":30},"bored":{"head":20,"torso":10,"upper_arm_left":15,"upper_arm_right":-10},"sleepy":{"head":25,"torso":16,"upper_arm_left":18,"upper_arm_right":-18},"sleeping":{"head":30,"torso":24,"upper_arm_left":20,"upper_arm_right":-20},"relieved":{"head":8,"torso":-4,"upper_arm_left":-15,"upper_arm_right":15},"celebrating":{"head":-15,"upper_arm_left":-110,"upper_arm_right":110}}
EMOTIONS = tuple(POSES)

def validate_rig(rig):
    bones=rig.get('bones',{})
    if set(bones)!=set(BONE_TREE): raise ValueError('Missing or unexpected bones')
    for name,pr in BONE_TREE.items():
        if bones[name]['parent']!=pr: raise ValueError('Invalid bone parent '+name)
        if not isinstance(bones[name]['pivot'],list) or len(bones[name]['pivot'])!=2:
            raise ValueError('Invalid pivot '+name)
    if set(rig.get('poses',{}))!=set(EMOTIONS): raise ValueError('24 emotions required')
    if rig.get('production_ready'):
        for name in BONE_TREE:
            if name not in rig.get('sprites',{}): raise ValueError('Missing sprite '+name)

def build_manifest(agent_id,display_name):
    rig={'version':'exodia-rig/v1','agent_id':agent_id,'name':display_name,
         'status':'needs_separated_character_layers','production_ready':False,
         'units':'pixel_100x180','design_canvas':[100,180],
         'bones':{name:{'parent':pr,'pivot':ANCHORS[name]} for name,pr in BONE_TREE.items()},
         'poses':POSES,'sprites':{},
         'motion':{
             'walk':{'period_seconds':0.72,'thigh_swing_deg':24,'knee_bend_deg':30,'arm_swing_deg':15},
             'blink':{'interval_seconds':[3,7],'duration_ms':120},
             'breathe':{'period_seconds':3.2,'torso_rotation_deg':1.5},
             'talk':{'visemes':['rest','A','E','I','O','U','M','F'],'mouth_layers_required':True},
             'hair_secondary':{'spring':0.18,'damping':0.82}
         },
         'reference':f'/assets/companions/portraits/{agent_id}.webp' if agent_id!='nova' else None}
    validate_rig(rig)
    return rig

def load_all(root:Path):
    roster=json.loads((root/'app/companions/roster.json').read_text(encoding='utf8'))
    if not any(a['id']=='nova' for a in roster):roster.append({'id':'nova','name':'Nova'})
    return {a['id']:build_manifest(a['id'],a['name']) for a in roster}
