"""Preflight-only visual rejection for Albedo candidate GLB renders.

Not a likeness classifier: passing these guardrails NEVER grants owner approval.
The production gate additionally requires a real GLB, coherent five camera views,
and an explicit owner side-by-side acceptance decision.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

# Canonical files from owner-approved source artwork. These checksums lock source identity.
EXPECTED = {
 'front': 'ddf1cc58e770d7cc99ffc3b2bd5a04ec77f720b05b8c96baf214090c899fb082',
 'turnaround': '787fa6009d504083a927c81c97dec1b01f3add6e1a6f5dacd7516f4789abf480',
 'mission': 'bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409',
}
# Measured from the 1024 x 1536 approved full-body master; not a generic character.
REF_BODY_BOUNDS=(118, 25, 910, 1523)
# Each zone is normalized to full standing body bounds. Keep source areas anatomically fixed.
ZONES = {
 'face':(.36,.066,.65,.189),
 'hair':(.16,.015,.87,.45),
 'collar_crystal':(.40,.17,.60,.265),
 'bodice':(.31,.235,.74,.415),
 'waist_ornament':(.28,.355,.74,.525),
 'draped_panels':(.12,.435,.92,.915),
 'boots':(.29,.805,.75,.997),
}
REQUIRED = ('face','hair','collar_crystal','bodice','waist_ornament','draped_panels','boots')


def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rgb(path:Path)->np.ndarray:
    img=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if img is None or min(img.shape[:2])<220: raise ValueError('Unusable or undersized image')
    return cv2.cvtColor(img,cv2.COLOR_BGR2RGB)


def crop(img:np.ndarray,bounds:tuple[int,int,int,int])->np.ndarray:
    x1,y1,x2,y2=bounds
    h,w=img.shape[:2]
    if min(x1,y1)<0 or x2>w or y2>h or x2-x1<80 or y2-y1<100:
        raise ValueError('Character body bounds missing/invalid')
    return img[y1:y2,x1:x2]


def region(img:np.ndarray,coords)->np.ndarray:
    h,w=img.shape[:2];x1,y1,x2,y2=coords
    return img[round(y1*h):round(y2*h),round(x1*w):round(x2*w)]


def detail_stats(img:np.ndarray)->dict:
    # Normalize to a common photographic size before comparing visual detail.
    h,w=img.shape[:2];neww=512;newh=max(64,round(h*neww/w))
    bgr=cv2.cvtColor(cv2.resize(img,(neww,newh),interpolation=cv2.INTER_AREA),cv2.COLOR_RGB2GRAY)
    edges=cv2.Canny(bgr,48,112,L2gradient=True)
    lap=cv2.Laplacian(bgr,cv2.CV_32F)
    return {'edge_density':round(float(np.mean(edges>0)),6),
            'laplacian_energy':round(float(np.mean(np.abs(lap))),5)}


def evaluate(reference:Path,candidate:Path,body_bounds,render_bounds)->dict:
    if digest(reference)!=EXPECTED['front']:
        raise ValueError('Approved front master fingerprint mismatch; refusal to compare')
    source=crop(load_rgb(reference),tuple(body_bounds))
    render=crop(load_rgb(candidate),tuple(render_bounds))
    zones={}; block=[]
    for label in REQUIRED:
        original=region(source,ZONES[label]);sample=region(render,ZONES[label])
        a,b=detail_stats(original),detail_stats(sample)
        ratio=b['edge_density']/max(a['edge_density'],1e-8)
        # Very low intricate detail is a negative control, NOT a likeness threshold.
        # Long hair must retain distinct strand complexity, not one smooth helmet.
        cutoff=0.45 if label=='hair' else 0.25
        reject=ratio<cutoff
        if reject:block.append(label+' detail is far below approved art')
        zones[label]={'reference':a,'render':b,'relative_edge_detail':round(ratio,4),'low_detail_blocker':reject}
    # At this gate, pixel metrics can only reject. No visual similarity score is
    # sufficient to approve a 3D sculpt or substitute for five real camera views.
    return {'gate':'Albedo A3 / visual preflight',
            'reference_sha256':digest(reference), 'candidate_sha256':digest(candidate),
            'status':'REJECTED_PREVIEW' if block else 'MANUAL_REVIEW_REQUIRED',
            'production_ready':False,'owner_visual_approval':False,
            'technical_nonlikeness_blockers':block, 'zones':zones,
            'warnings':['This report cannot certify character identity, topology, or 3D depth.',
                        'A full GLB and five independent camera renders remain mandatory.',
                        'The reference is an illustration, so valid 3D models may have different microdetail.']}


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--reference',type=Path,required=True)
    ap.add_argument('--render',type=Path,required=True)
    ap.add_argument('--bounds',required=True,help='character body bounds x1,y1,x2,y2 for the render')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    box=tuple(map(int,args.bounds.split(',')))
    if len(box)!=4: ap.error('--bounds needs 4 integers')
    result=evaluate(args.reference,args.render,REF_BODY_BOUNDS,box)
    text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text)
    return 2 if result['status']=='REJECTED_PREVIEW' else 0

if __name__=='__main__':raise SystemExit(main())