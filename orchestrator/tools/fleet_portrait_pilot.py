"""Fail-closed fleet portrait intake preflight; never generates or certifies art.

The locked Albedo state vocabulary is the source of truth. A0 source images may
be identity/style references; only independent native per-state sources are
accepted as technical *candidates*. Geometry/acting/owner signoff remain manual.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / 'frontend/companions/roster.json'
REGISTRY = ROOT / 'frontend/companions/production/kiko/portrait_registry.json'
LOCKED_CANVAS = (1536, 1920)
PILOT_KEYS = ('neutral', 'confident', 'angered', 'working', 'pointing')


def canonical():
    roster = json.loads(ROSTER.read_text(encoding='utf-8'))
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    ids = [r['id'] for r in roster]
    if len(ids) != 10 or len(set(ids)) != 10 or set(ids) != {
        'kiko','router','memory','archives','inventory','vault','ninja','cache','strategy','nova'}:
        raise ValueError('Fleet roster drift: 10 stable IDs are mandatory')
    states = registry['states']
    expressions = [k for k, v in states.items() if v['category'] == 'expression']
    actions = [k for k, v in states.items() if v['category'] == 'action']
    if len(states) != 33 or len(expressions) != 20 or len(actions) != 13:
        raise ValueError('Canonical state vocabulary drift: 20 expressions + 13 actions required')
    if len(set(PILOT_KEYS)) != 5 or any(k not in states for k in PILOT_KEYS):
        raise ValueError('Riven pilot state mismatch')
    return { 'roster':roster, 'registry': registry }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def make_riven_manifest():
    src=canonical()
    riven=next(r for r in src['roster'] if r['id']=='router')
    ref=ROOT/'frontend/companions/source_masters/router.png'
    with Image.open(ref) as image: ref_size = list(image.size)
    states=src['registry']['states']
    return {
      'schema':'exodia.fleet-art-pilot/v1',
      'character_id':'router', 'name':riven['name'],
      'identity_reference':{'path':str(ref.relative_to(ROOT)).replace('\\','/'),
        'sha256':sha256(ref),'dimensions':ref_size,
        'classification':'nonproduction_composite_poster_style_reference_only',
        'native_identity_owner_approved':False},
      'native_canvas':[1536,1920],
      'eye_midline_y_px':633.6,'shoulder_baseline_y_px':980.0,
      'head_width_px':614.4,'head_center_x_px':768.0,
      'source_policy':'single_independently_authored_standalone_state_png',
      'production_release_enabled':False,
      'states':{key:{'category':states[key]['category'],
          'brief':{'neutral':'Quiet neutral pathfinder readiness, no pointing or anger',
                   'confident':'Steady decisive tactical gaze, both arms anatomically credible',
                   'angered':'Controlled frustration at a blocked route, not a tantrum',
                   'working':'Active route-planning with connected hands and plausible tools',
                   'pointing':'Clearly connected index finger identifying a safe route'}[key],
          'source_file':None,'source_sha256':None,
          'source_kind':'pending_native_independent_standalone',
          'derived_from_composite':False,'owner_approval_reference':None,
          'actual_landmark_evidence':None,
          'status':'awaiting_native_source'} for key in PILOT_KEYS},
      'native_production_certified':False,
      'note':'A0 Riven identity and 5 independent source masters require new owner review; this manifest never approves pixels.'
    }


def audit_pilot(manifest:dict, source_root:Path):
    canonical_data = canonical()
    if manifest.get('character_id') != 'router' or manifest.get('production_release_enabled') is not False:
        raise ValueError('Pilot cannot reassign identity or enable production release')
    states=manifest.get('states',{})
    if set(states)!=set(PILOT_KEYS):raise ValueError('Pilot must retain its five exact state keys')
    failures=[]; results={}; seen={}
    for key in PILOT_KEYS:
        row=states[key]
        if row['category']!=canonical_data['registry']['states'][key]['category']:
            failures.append(key+':category_drift')
        file=row.get('source_file')
        if not file:
            results[key]={'source':'missing','technical_preflight':'PENDING','native_certified':False}
            continue
        path=(source_root/file).resolve()
        if not path.is_relative_to(source_root.resolve()) or not path.is_file():
            failures.append(key+':invalid_source_path');continue
        if path.suffix.lower()!='.png':failures.append(key+':not_png');continue
        with Image.open(path) as im:
            dim=im.size; fmt=im.format
        h=sha256(path)
        reasons=[]
        if dim!=LOCKED_CANVAS or fmt!='PNG':reasons.append('non_native_source')
        if h!=row.get('source_sha256'):reasons.append('hash_mismatch')
        if row.get('derived_from_composite') is not False:reasons.append('derived_from_composite')
        if row.get('source_kind')!='independent_standalone_native':reasons.append('unverified_source_kind')
        if h in seen:reasons.append('duplicate_bytes_with_'+seen[h])
        seen[h]=key
        if reasons:failures += [key+':'+x for x in reasons]
        results[key]={'source':'provided','sha256':h,'dimensions':list(dim),
            'technical_preflight':'FAIL' if reasons else 'PASS',
            # Human geometry and approval never inferred from metadata or dimensions.
            'landmarks_verified':False,'identity_owner_approved':False,
            'acting_approved':False,'native_certified':False}
    return {'schema':'exodia.fleet-art-pilot-audit/v1',
        'character_id':'router','planned_states':5,
        'technical_source_passed':sum(v['technical_preflight']=='PASS' for v in results.values()),
        'native_production_certified':0,'production_release_enabled':False,
        'failures':failures,'states':results}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,help='Inspect an existing pilot manifest')
    parser.add_argument('--root',type=Path,default=ROOT,help='Root directory for supplied standalone PNGs')
    args=parser.parse_args()
    doc=json.loads(args.manifest.read_text(encoding='utf-8')) if args.manifest else make_riven_manifest()
    print(json.dumps(audit_pilot(doc,args.root),indent=2,sort_keys=True))

if __name__=='__main__':main()
