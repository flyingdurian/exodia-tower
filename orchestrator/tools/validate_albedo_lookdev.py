"""Albedo A2 model fidelity intake. Metadata integrity != artistic acceptance."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
REF={'mission':'bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409',
     'front':'ddf1cc58e770d7cc99ffc3b2bd5a04ec77f720b05b8c96baf214090c899fb082',
     'turnaround':'787fa6009d504083a927c81c97dec1b01f3add6e1a6f5dacd7516f4789abf480'}
VIEWS=('front','front_angle','side','back_angle','back')
CHECKS=('face_identity','silver_lavender_hair','violet_eyes','flower_and_gold_ornament',
        'crystal_and_collar','white_lilac_black_gold_costume','draped_panels','boots',
        'anatomical_proportions','side_and_back_consistency',
        'silhouette_and_facial_readability','no_cropped_2d_surfaces')
def resolve(root,relative):
    if not isinstance(relative,str) or not relative or '\\' in relative or Path(relative).is_absolute():
        raise ValueError('Unsafe or missing file path')
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Path escapes candidate')
    return p
def inspect_glb(p):
    data=p.read_bytes()
    if len(data)<20 or data[:4]!=b'glTF' or int.from_bytes(data[4:8],'little')!=2:
        raise ValueError('Invalid GLB 2 header')
    length,chunk,code=struct.unpack_from('<III',data,8)
    if length!=len(data) or code!=0x4e4f534a or chunk>32000000 or 20+chunk>len(data):
        raise ValueError('GLB JSON chunk invalid')
    g=json.loads(data[20:20+chunk].decode().strip())
    if g.get('asset',{}).get('version')!='2.0':raise ValueError('glTF version wrong')
    meshes=g.get('meshes',[])
    return {'meshes':len(meshes),'materials':len(g.get('materials',[])),
            'textures':len(g.get('textures',[])),
            'primitives':sum(len(m.get('primitives',[])) for m in meshes),
            'engineering_proxy':g.get('asset',{}).get('extras',{}).get('production_ready') is False}
def inspect_png(p):
    with p.open('rb') as f: hdr=f.read(24)
    if len(hdr)<24 or hdr[:8]!=b'\x89PNG\r\n\x1a\n' or hdr[12:16]!=b'IHDR':
        raise ValueError('Expected PNG render')
    w,h=struct.unpack('>II',hdr[16:24])
    if min(w,h)<720 or max(w,h)>16384:raise ValueError('Render size out of bounds')
    return w,h
def review(folder):
    folder=Path(folder).resolve()
    if not (folder/'model_submission.json').is_file():
        return {'status':'incomplete','passed':False,'errors':['model_submission.json missing'],'production_ready':False}
    spec=json.loads((folder/'model_submission.json').read_text(encoding='utf-8'))
    errors=[];details={}
    if spec.get('schema')!='exodia.albedo-lookdev/v1' or spec.get('character_id')!='kiko':
        errors.append('Wrong character or schema')
    if spec.get('reference_sha256')!=REF:errors.append('Approved reference hashes mismatch')
    if spec.get('candidate_kind')!='full_body_3d':errors.append('Not a full-body 3D candidate')
    if spec.get('visual_review_state')=='approved':errors.append('Self-reported approval is not owner signoff')
    try:
        p=resolve(folder,spec.get('model'))
        if p.suffix.lower()!='.glb':raise ValueError('Model must be GLB')
        m=inspect_glb(p);details['model']=m
        details['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        if m['engineering_proxy']:errors.append('Rejected A1 engineering proxy')
        if not m['meshes'] or not m['primitives']:errors.append('No mesh geometry')
        if m['materials']<3 or m['textures']<1:errors.append('No meaningful textured material separation')
    except (ValueError,OSError,TypeError,UnicodeDecodeError) as e:errors.append('Model: '+str(e))
    seen=set()
    for view in VIEWS:
        try:
            p=resolve(folder,spec.get('review_views',{}).get(view))
            details[view]=inspect_png(p)
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            if sha in seen:errors.append(view+': duplicate render')
            seen.add(sha)
        except (ValueError,OSError,TypeError) as e:errors.append(view+': '+str(e))
    notes=spec.get('art_review',{})
    for k in CHECKS:
        if notes.get(k) not in ('pass','fail','pending'):errors.append('Missing review criterion '+k)
        if notes.get(k)=='fail':errors.append('Visual review failed: '+k)
    ok=not errors
    return {'status':'ready_for_owner_visual_review' if ok else 'incomplete','passed':ok,
            'production_ready':False,'visual_identity_approved':False,
            'details':details,'errors':errors,
            'note':'Structural intake is not visual approval. Owner must inspect actual model.'}
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    r=review(args.folder)
    print(json.dumps(r,indent=2))
    raise SystemExit(0 if r['passed'] else 1)
