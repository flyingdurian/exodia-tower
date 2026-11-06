"""Fail-closed technical preflight for the separate 40-frame operations chibi family.

This cannot certify identity, expression fidelity, or owner approval from pixels alone.
Owner review evidence and landmark inspection remain independent release gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS=('n','ne','e','se','s','sw','w','nw')


def audit(manifest:Path,root:Path=ROOT)->dict:
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema')!='exodia.albedo-chibi/v1' or data.get('character_id')!='kiko':
        raise ValueError('Chibi identity contract mismatch')
    if data.get('production_release_enabled') is not False:
        raise ValueError('Chibi release flag must remain locked during staging')
    names=[n for d in DIRECTIONS for n in (f'idle_{d}', *(f'walk_{d}_{k:02d}' for k in range(4)))]
    if set(data.get('frames',{}))!=set(names):
        raise ValueError('Exactly 40 keyed frames are required')
    if data.get('directions')!=list(DIRECTIONS):
        raise ValueError('Chibi direction order mismatched')
    pending=data.get('asset_status')=='pending_production_frames'
    if not pending and data.get('asset_status')!='approved_40_frame_set':
        raise ValueError('Unknown chibi asset status')
    sha_set=set()
    for name in names:
        row=data['frames'][name]
        if pending:
            if row.get('status')!='pending_independent_art' or any(row.get(k) is not None for k in ('src','sha256','approval_sha256','source_provenance')):
                raise ValueError(f'Partial art promotion forbidden: {name}')
            continue
        expected=f'/assets/albedo_chibi/frames/{name}.png'
        if row.get('src')!=expected:
            raise ValueError(f'Unexpected frame source path {name}')
        sha=row.get('sha256')
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError(f'Missing approved source SHA: {name}')
        if row.get('status')!='owner_approved' or row.get('approval_sha256')!=sha:
            raise ValueError(f'Approval SHA gate failed: {name}')
        meta=row.get('source_provenance') or {}
        if meta.get('source_kind')!='independent_standalone' or meta.get('derived_from_composite') is not False:
            raise ValueError(f'Independent standalone provenance missing: {name}')
        landmark=meta.get('foot_anchor_px')
        if not isinstance(landmark,list) or len(landmark)!=2 or any(not isinstance(v,(int,float)) for v in landmark):
            raise ValueError(f'Manual foot anchor missing: {name}')
        if not (0<=landmark[0]<192 and 0<=landmark[1]<256):
            raise ValueError(f'Foot anchor outside source: {name}')
        if not isinstance(meta.get('human_review_reference'),str) or not meta['human_review_reference'].strip():
            raise ValueError(f'Missing human-reviewed identity/foot registration evidence: {name}')
        if sha in sha_set:
            raise ValueError(f'Duplicate frame source SHA: {name}')
        sha_set.add(sha)
        path=root/'frontend'/'albedo_chibi'/'frames'/f'{name}.png'
        if not path.is_file():
            raise ValueError(f'Missing independently authored frame file: {path}')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError(f'Frame bytes SHA mismatch: {name}')
        with Image.open(path) as img:
            if img.format!='PNG' or img.size!=(192,256):
                raise ValueError(f'Non-native sprite canvas: {name}')
            if img.mode!='RGBA' or img.getchannel('A').getextrema()!=(0,255):
                raise ValueError(f'Native RGBA cutout transparency required: {name}')
    return {'schema':'exodia.albedo-chibi-audit/v1','character':'kiko',
            'frame_count':len(names),'byte_verified':len(sha_set),
            'production_release_enabled':False,
            'status':'PENDING_INDEPENDENT_ART_AND_OWNER_APPROVAL' if pending else 'BYTE_AND_PROVENANCE_PREFLIGHT_ONLY',
            'native_owner_certified':False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,default=ROOT/'frontend'/'albedo_chibi_manifest.json')
    p.add_argument('--root',type=Path,default=ROOT)
    args=p.parse_args()
    print(json.dumps(audit(args.manifest,args.root),indent=2))

if __name__=='__main__':
    main()
