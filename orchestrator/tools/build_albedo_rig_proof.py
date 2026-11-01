"""Exodia Albedo A1: deterministic, *genuinely skinned* glTF/GLB engineering proof.

This deliberately makes an original, lower-fidelity 3D surface proxy, NOT an
approved art model. No cropped image/sprite is used as a moving body. The
skinned material proxy must never replace the approved reference on the live UI.

No proprietary runtime, Blender, online models, or paid tool required.
"""
from __future__ import annotations
import json, math, struct, hashlib, argparse
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
REL_OUT = 'frontend/companions/production/kiko/albedo_rig_proof.glb'
ACTION_NAMES = ('idle','walk','run','jump','sit','work_computer',
                'typing_working','pointing','explaining','celebrating',
                'stretching','sleeping','waking_up')

# Right-handed glTF Y-up; neutral bind pose is stable and fully 3D.
# Parents are anatomical, not sprites. Extra branches drive hair and dress.
BONES = (
 ('root',None,(0,0,0)),
 ('hips','root',(0,1.48,0)),
 ('spine','hips',(0,.33,0)),
 ('chest','spine',(0,.44,0)),
 ('neck','chest',(0,.35,0)),
 ('head','neck',(0,.24,0)),
 ('jaw','head',(0,-.22,.17)),
 ('eye_L','head',(-.115,.06,.24)),('eye_R','head',(.115,.06,.24)),
 ('shoulder_L','chest',(-.43,.18,0)),
 ('elbow_L','shoulder_L',(-.31,-.41,0)),
 ('wrist_L','elbow_L',(-.24,-.39,0)),
 ('hand_L','wrist_L',(-.08,-.14,0)),
 ('shoulder_R','chest',(.43,.18,0)),
 ('elbow_R','shoulder_R',(.31,-.41,0)),
 ('wrist_R','elbow_R',(.24,-.39,0)),
 ('hand_R','wrist_R',(.08,-.14,0)),
 ('thigh_L','hips',(-.25,-.16,0)),
 ('knee_L','thigh_L',(0,-.60,0)),
 ('ankle_L','knee_L',(0,-.54,0)),
 ('foot_L','ankle_L',(0,-.12,.11)),
 ('thigh_R','hips',(.25,-.16,0)),
 ('knee_R','thigh_R',(0,-.60,0)),
 ('ankle_R','knee_R',(0,-.54,0)),
 ('foot_R','ankle_R',(0,-.12,.11)),
 ('hair_crown','head',(0,.34,-.12)),
 ('hair_back_L','hair_crown',(-.25,-.30,-.18)),
 ('hair_tip_L','hair_back_L',(-.15,-.70,0)),
 ('hair_back_R','hair_crown',(.25,-.30,-.18)),
 ('hair_tip_R','hair_back_R',(.15,-.70,0)),
 ('hair_fringe','hair_crown',(0,-.09,.26)),
 ('cape_L','chest',(-.28,-.18,-.12)),
 ('cape_tip_L','cape_L',(-.22,-.65,-.05)),
 ('cape_R','chest',(.28,-.18,-.12)),
 ('cape_tip_R','cape_R',(.22,-.65,-.05)),
)
INDEX = {b[0]:i for i,b in enumerate(BONES)}
ABS = {}
for name,parent,delta in BONES:
    q = ABS[parent] if parent else (0,0,0)
    ABS[name] = tuple(q[i]+delta[i] for i in range(3))

MATS = [
 ('skin', (.96,.78,.77,1),False),
 ('pearl_cloth',(.85,.86,.97,1),False),
 ('silver_hair',(.72,.70,.96,1),False),
 ('lavender',(.52,.37,.87,1),False),
 ('black_gold',(.13,.12,.25,1),False),
 ('gold',(.95,.73,.42,1),False),
 ('violet_crystal',(.42,.18,.92,1),False),
 ('iris',(.34,.16,.67,1),False),
]

V=[]; N=[]; C=[]; J=[]; W=[]; IND=[]; PART=[]

def unit(a):
    l=math.sqrt(sum(x*x for x in a)) or 1
    return tuple(x/l for x in a)

def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def mul(a,k):return tuple(x*k for x in a)

def point(x,y,z,joint0,joint1=None,t=0.0,material=0):
    V.extend((x,y,z))
    # normal created at ring registration; fallback up
    N.extend((0,0,1)); C.append(material)
    j0=INDEX[joint0];j1=INDEX[joint1 or joint0]
    J.extend((j0,j1,0,0));W.extend((1-t,t,0,0))

def tube(name, pts, radii, joint_labels, mat, sides=14):
    """Continuous ring surface, per-ring two-bone influence. Weighted skin."""
    if not (len(pts)==len(radii)==len(joint_labels)) or len(pts)<2:
        raise ValueError('invalid mesh ring specification')
    start=len(V)//3; seg=[]
    for i,p in enumerate(pts):
        tangent=unit(sub(pts[min(i+1,len(pts)-1)],pts[max(i-1,0)]))
        reference=(0,0,1) if abs(tangent[2])<.9 else (0,1,0)
        a=unit(cross(tangent,reference));b=unit(cross(tangent,a))
        rx,rz=radii[i]
        bone_a,bone_b,blend=joint_labels[i]
        for s in range(sides):
            th=2*math.pi*s/sides
            normal=unit(add(mul(a,math.cos(th)/max(rx,.0001)),mul(b,math.sin(th)/max(rz,.0001))))
            off=add(mul(a,rx*math.cos(th)),mul(b,rz*math.sin(th)))
            point(*(add(p,off)),bone_a,bone_b,blend,mat)
            N[-3:]=list(normal)
        if i:
            for s in range(sides):
                k=start+(i-1)*sides+s; k2=start+(i-1)*sides+(s+1)%sides
                q=start+i*sides+s; q2=start+i*sides+(s+1)%sides
                seg.extend((k,k2,q,k2,q2,q))
    PART.append((mat,seg,name))

def ellipse(name, center, scales, joint, mat, lat=12, lon=20):
    start=len(V)//3;indices=[]
    for i in range(lat+1):
        theta=math.pi*i/lat
        for j in range(lon):
            phi=2*math.pi*j/lon
            d=(math.sin(theta)*math.cos(phi),math.cos(theta),math.sin(theta)*math.sin(phi))
            xyz=add(center,tuple(d[k]*scales[k] for k in range(3)))
            point(*xyz,joint,material=mat)
            N[-3:]=list(unit(tuple(d[k]/max(scales[k],.001) for k in range(3))))
            if i:
                k=start+(i-1)*lon+j;k2=start+(i-1)*lon+(j+1)%lon
                q=start+i*lon+j;q2=start+i*lon+(j+1)%lon
                indices.extend((k,k2,q,k2,q2,q))
    PART.append((mat,indices,name))

def blended_chain(names, radii, mat, sides=16, label=None):
    ps=[ABS[n] for n in names]
    rings=[];rr=[];weights=[]
    for i in range(len(ps)-1):
        for k in range(5):
            u=k/5; rings.append(add(mul(ps[i],1-u),mul(ps[i+1],u)))
            rr.append(tuple(radii[i][j]*(1-u)+radii[i+1][j]*u for j in range(2)))
            weights.append((names[i],names[i+1],u))
    rings.append(ps[-1]);rr.append(radii[-1]);weights.append((names[-1],names[-1],0))
    tube(label or names[0],rings,rr,weights,mat,sides)

# Dress structure, actual 3D surface construction. NO cropped image plane.
blended_chain(['hips','spine','chest','neck'],[(.30,.19),(.24,.15),(.39,.23),(.115,.115)],1,24,'torso_sheath')
ellipse('corset_front',(0,1.96,.145),(.235,.35,.08),'spine',4)
ellipse('face',ABS['head'],(.295,.38,.265),'head',0)
ellipse('neck',(0,2.62,.02),(.12,.18,.12),'neck',0)
for side in ('L','R'):
    blended_chain([f'shoulder_{side}',f'elbow_{side}',f'wrist_{side}',f'hand_{side}'],
                 [(.17,.145),(.123,.125),(.091,.095),(.06,.065)],1,16,f'sleeve_{side}')
    ellipse('glove_'+side,ABS['hand_'+side],(.088,.12,.075),'hand_'+side,4)
    blended_chain([f'thigh_{side}',f'knee_{side}',f'ankle_{side}',f'foot_{side}'],
                 [(.205,.205),(.16,.16),(.103,.10),(.112,.22)],0,16,f'leg_{side}')
    ellipse('boot_'+side,add(ABS['ankle_'+side],(0,-.09,.07)),(.14,.24,.20),'ankle_'+side,1)
    ellipse('boot_tip_'+side,add(ABS['foot_'+side],(0,-.02,.10)),(.125,.085,.19),'foot_'+side,4)
    ellipse('iris_'+side,add(ABS['head'],((-.125 if side=='L' else .125),.06,.257)),(.07,.094,.025),'eye_'+side,7)
    ellipse('pupil_'+side,add(ABS['head'],((-.125 if side=='L' else .125),.06,.276)),(.030,.065,.01),'eye_'+side,4)
# Neckline crystal and jewelry are 3D rigid pieces, not fake face patches.
ellipse('amulet',(.0,2.38,.248),(.068,.10,.043),'chest',6)
for y,rx,rz in [(1.45,.37,.26),(1.20,.51,.34),(.90,.66,.40),(.54,.80,.43)]:
    pass
# Dress flare: rooted at hips with tapered concentric elliptical rings.
ys=[1.65,1.52,1.30,1.05,.80,.54];r=[(.28,.22),(.34,.25),(.47,.32),(.55,.35),(.73,.38),(.85,.39)]
tube('dress_lower',[(0,y,0) for y in ys],r,
     [('hips','spine',max(0,min(1,(y-1.48)/.33))) for y in ys],3,28)
# Narrow pearly panels form distinct physical hanging surfaces, no 2D compositing.
for side in (-1,1):
    label='L' if side<0 else 'R'
    blended_chain([f'cape_{label}',f'cape_tip_{label}'],[(.16,.045),(.26,.055)],1,12,'cape_'+label)
    blended_chain([f'hair_back_{label}',f'hair_tip_{label}'],[(.32,.20),(.21,.13)],2,20,'hair_back_'+label)
    # shorter streaks around the face to allow eye/mouth readability
    ellipse('hair_frame_'+label,add(ABS['head'],(side*.27,-.11,.015)),(.095,.33,.13),'head',2)
ellipse('hair_crown',add(ABS['head'],(0,.30,-.065)),(.315,.19,.21),'hair_crown',2)
blended_chain(['hair_crown','hair_fringe'],[(.26,.11),(.18,.08)],2,12,'fringe')
ellipse('flower_accessory',add(ABS['head'],(.275,.34,.08)),(.10,.11,.05),'hair_crown',1)
ellipse('mouth',add(ABS['head'],(0,-.16,.252)),(.065,.026,.018),'jaw',6)


def q_axis(axis,rad):
    s=math.sin(rad/2);return (axis[0]*s,axis[1]*s,axis[2]*s,math.cos(rad/2))

def q_combine(a,b):
    # Compose orthogonal axis motions instead of silently overwriting one axis.
    ax,ay,az,aw=a; bx,by,bz,bw=b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
            aw*bz+ax*by-ay*bx+az*bw,aw*bw-ax*bx-ay*by-az*bz)

def posture(action,t):
    """Engineering curves: not hand-polished/physical production animation."""
    phase=2*math.pi*t
    out={};pos={}
    def rot(name,axis,degrees):out[name]=q_axis(axis,math.radians(degrees))
    if action=='idle':
        rot('chest',(1,0,0),1.6*math.sin(phase));rot('head',(0,0,1),1.3*math.sin(phase*.5))
    elif action in ('walk','run'):
        swing=28 if action=='walk' else 47;speed=1 if action=='walk' else 1.5
        a=phase*speed
        for sign,side in ((1,'L'),(-1,'R')):
            rot('thigh_'+side,(1,0,0),sign*swing*math.sin(a))
            rot('knee_'+side,(1,0,0),max(0,-sign*math.sin(a))*38*(1.5 if action=='run' else 1))
            rot('shoulder_'+side,(1,0,0),-sign*(swing*.65)*math.sin(a))
        pos['root']=(0,.04*abs(math.sin(2*a)),0)
    elif action=='jump':
        z=max(0,math.sin(math.pi*t))
        pos['root']=(0,.48*z,0)
        for side,sgn in (('L',-1),('R',1)):
            rot('shoulder_'+side,(0,0,1),sgn*82*z)
            rot('knee_'+side,(1,0,0),30*z)
    elif action=='sit':
        pos['hips']=(0,-.33*min(1,4*t),0)
        for side in ('L','R'):rot('thigh_'+side,(1,0,0),-75*min(1,4*t));rot('knee_'+side,(1,0,0),75*min(1,4*t))
        rot('spine',(1,0,0),8*min(1,4*t))
    elif action in ('work_computer','typing_working'):
        rot('spine',(1,0,0),9)
        for side,sgn in (('L',-1),('R',1)):
            rot('shoulder_'+side,(1,0,0),45)
            rot('elbow_'+side,(1,0,0),-70)
            if action=='typing_working':rot('wrist_'+side,(1,0,0),7*math.sin(phase*5+sgn))
        rot('head',(1,0,0),-10)
    elif action=='pointing':
        out['shoulder_R']=q_combine(q_axis((0,0,1),math.radians(-35)),
                                     q_axis((1,0,0),math.radians(68)))
        rot('elbow_R',(1,0,0),-12)
        rot('head',(0,1,0),-14)
    elif action=='explaining':
        for side,sign in (('L',1),('R',-1)):
            rot('shoulder_'+side,(0,0,1),sign*(30+10*math.sin(phase)))
            rot('elbow_'+side,(1,0,0),-35)
        rot('head',(0,0,1),4*math.sin(phase))
    elif action=='celebrating':
        pos['root']=(0,.14*abs(math.sin(phase)),0)
        for side,sign in (('L',-1),('R',1)):
            rot('shoulder_'+side,(0,0,1),sign*(110+8*math.sin(phase)))
    elif action=='stretching':
        for side,sign in (('L',-1),('R',1)):
            rot('shoulder_'+side,(0,0,1),sign*155)
        rot('chest',(0,0,1),6*math.sin(phase))
    elif action=='sleeping':
        rot('head',(0,0,1),16);rot('spine',(1,0,0),12)
        rot('eye_L',(1,0,0),-18);rot('eye_R',(1,0,0),-18)
    elif action=='waking_up':
        rot('head',(0,0,1),16*(1-t))
        rot('spine',(1,0,0),12*(1-t))
        for side,sign in (('L',-1),('R',1)):
            rot('shoulder_'+side,(0,0,1),sign*80*math.sin(math.pi*t))
    # Custom per-strand/cape joint animation curves (keyframed secondary motion).
    for side,sign in (('L',-1),('R',1)):
        rot('hair_back_'+side,(0,0,1),sign*3*math.sin(phase-.8))
        rot('hair_tip_'+side,(1,0,0),5*math.sin(phase-1.2))
        rot('cape_'+side,(1,0,0),4*math.sin(phase-.65))
        rot('cape_tip_'+side,(0,0,1),sign*6*math.sin(phase-1))
    return out,pos

class Buffer:
    def __init__(self):self.data=bytearray();self.views=[];self.accessors=[]
    def pack(self,raw,target=None):
        while len(self.data)%4:self.data.append(0)
        off=len(self.data);self.data.extend(raw)
        obj={'buffer':0,'byteOffset':off,'byteLength':len(raw)}
        if target:obj['target']=target
        self.views.append(obj);return len(self.views)-1
    def accessor(self,flat,fmt,comps,component_type,typ,target=None,normalized=False):
        raw=struct.pack('<'+fmt*len(flat),*flat)
        v=self.pack(raw,target)
        d={'bufferView':v,'componentType':component_type,'count':len(flat)//comps,'type':typ}
        if normalized:d['normalized']=True
        if target==34962 and typ=='VEC3' and len(flat):
            d['min']=[min(flat[i::3]) for i in range(3)]
            d['max']=[max(flat[i::3]) for i in range(3)]
        if typ=='SCALAR' and len(flat) and fmt=='f':d.update(min=[min(flat)],max=[max(flat)])
        self.accessors.append(d);return len(self.accessors)-1


def build(path: Path):
    binary=Buffer()
    acc_v=binary.accessor(V,'f',3,5126,'VEC3',34962)
    acc_n=binary.accessor(N,'f',3,5126,'VEC3',34962)
    acc_j=binary.accessor(J,'H',4,5123,'VEC4',34962)
    acc_w=binary.accessor(W,'f',4,5126,'VEC4',34962)
    positions = []
    for name,_,_ in BONES:
        x,y,z=ABS[name]
        # Column-major mat4 inverse bind translation; rotational bind identity.
        positions.extend([1,0,0,0,0,1,0,0,0,0,1,0,-x,-y,-z,1])
    acc_bind=binary.accessor(positions,'f',16,5126,'MAT4')
    materials=[]
    for name,color,blend in MATS:
        materials.append({'name':name,'pbrMetallicRoughness':{'baseColorFactor':list(color),'metallicFactor':0.04,'roughnessFactor':0.53},'doubleSided':True})
    prims=[]
    for mat,triangles,label in PART:
        ai=binary.accessor(triangles,'I',1,5125,'SCALAR',34963)
        prims.append({'attributes':{'POSITION':acc_v,'NORMAL':acc_n,'JOINTS_0':acc_j,'WEIGHTS_0':acc_w},'indices':ai,'material':mat,'mode':4,'extras':{'surface':label}})
    nodes=[{'name':n,'translation':list(d),'children':[]} for n,p,d in BONES]
    for i,(_,p,_) in enumerate(BONES):
        if p:nodes[INDEX[p]]['children'].append(i)
    # Mesh is skinned, *not parented under any joint*, to prevent double transform.
    mesh_id=len(nodes);nodes.append({'name':'Albedo Engineering Surface Proxy','mesh':0,'skin':0})
    samplers_cache={}
    animations=[]
    for action in ACTION_NAMES:
        # 16 or 24 samples are authored quaternion/translation values, not frame-swapped sprites.
        samples=24 if action in ('walk','run','typing_working') else 16
        times=[i/(samples-1) for i in range(samples)]
        in_acc=binary.accessor(times,'f',1,5126,'SCALAR')
        clip={'name':action,'samplers':[],'channels':[]}
        tracks={}
        for i,t in enumerate(times):
            ro,po=posture(action,t)
            for name,val in ro.items():tracks.setdefault((name,'rotation'),[]).extend(val)
            for name,val in po.items():tracks.setdefault((name,'translation'),[]).extend(val)
        for (bone,prop),values in tracks.items():
            if prop=='translation' and bone!='root':
                # Translation glTF overrides bind translation; offsets must be added.
                x,y,z=BONES[INDEX[bone]][2]
                values=[values[i]+(x,y,z)[i%3] for i in range(len(values))]
            # Some action tracks appear every sample; require complete channel length.
            size=4 if prop=='rotation' else 3
            if len(values)!=samples*size:raise AssertionError((action,bone,prop,len(values),samples))
            v_acc=binary.accessor(values,'f',size,5126,'VEC4' if size==4 else 'VEC3')
            s=len(clip['samplers']);clip['samplers'].append({'input':in_acc,'output':v_acc,'interpolation':'LINEAR'})
            clip['channels'].append({'sampler':s,'target':{'node':INDEX[bone],'path':prop}})
        animations.append(clip)
    manifest={
      'asset':{'version':'2.0','generator':'Exodia A1 3D skinned engineering proxy (no finished character likeness)'},
      'scene':0,'scenes':[{'nodes':[INDEX['root'],mesh_id]}],
      'nodes':nodes,'skins':[{'name':'Albedo Humanoid Experimental Skeleton',
        'joints':list(range(len(BONES))),'skeleton':0,'inverseBindMatrices':acc_bind}],
      'meshes':[{'name':'Non-cutout skinned volumetric 3D meshes','primitives':prims}],
      'materials':materials,'buffers':[{'byteLength':len(binary.data)}],
      'bufferViews':binary.views,'accessors':binary.accessors,'animations':animations,
      'extras':{'owner_approved_art':False,'production_ready':False,'facial_morphs_ready':False,
                'purpose':'real skinning and motion validation only; NOT live-character art'}
    }
    # glTF GLB 2.0: JSON then BIN, each padded to 4-byte boundary.
    j=json.dumps(manifest,separators=(',',':')).encode('utf-8')
    j+=b' ' * (-len(j)%4)
    b=bytes(binary.data);b+=b'\0' * (-len(b)%4)
    glb=b'glTF'+struct.pack('<II',2,12+8+len(j)+8+len(b))
    glb+=struct.pack('<I4s',len(j),b'JSON')+j
    glb+=struct.pack('<I4s',len(b),b'BIN\0')+b
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(glb)
    return {'output':str(path),'sha256':hashlib.sha256(glb).hexdigest(),
            'bones':len(BONES),'skinned_vertices':len(V)//3,'surfaces':len(PART),
            'triangles':sum(len(t)//3 for _,t,_ in PART),'actions':list(ACTION_NAMES),'bytes':len(glb)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/REL_OUT)
    args=parser.parse_args();print(json.dumps(build(args.out),indent=2))
