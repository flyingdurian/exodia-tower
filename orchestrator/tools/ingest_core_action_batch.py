"""Queue and stage four independently rendered Albedo action portraits.
--approve only checks EXISTING owner approval and image-bound landmarks.
--commit invokes the existing atomic single-file importer. Never invent signoff.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / 'assets/staging_intake'
PRODUCTION = ROOT / 'orchestrator/frontend/companions/production/kiko'
QUEUE = STAGING / 'core_actions_batch.json'
KEYS = ('working', 'explaining', 'monitoring', 'pointing')
BAD_NAMES = ('collage', 'board', 'contact', 'atlas', 'slice', 'crop', 'grid', 'montage', 'upscale')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_normalization import normalize_portrait

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def validate_queue(queue, manifest, registry):
    rows = queue.get('states')
    if queue.get('schema') != 'exodia.albedo-core-actions-batch/v1' or queue.get('automatic_approval') is not False:
        raise ValueError('batch_schema_or_approval_policy_invalid')
    if not isinstance(rows, list) or tuple(r.get('key') for r in rows) != KEYS:
        raise ValueError('action_key_order_mismatch')
    for index, row in enumerate(rows, start=1):
        key = row['key']
        if row.get('priority') != index or row.get('source_file') != key + '.png':
            raise ValueError('state_priority_or_file_mismatch:' + key)
        if registry['states'][key]['category'] != 'action' or manifest['entries'][key]['filename'] != 'incoming/' + key + '.png':
            raise ValueError('registry_state_mapping_mismatch:' + key)
    return rows

def validate_original(image, declaration):
    if not image.is_file() or not declaration.is_file() or image.is_symlink() or declaration.is_symlink():
        raise ValueError('standalone_source_and_provenance_required')
    if any(term in image.name.lower() for term in BAD_NAMES):
        raise ValueError('board_derived_filename_disallowed')
    meta = load(declaration)
    with Image.open(image) as im:
        if im.format != 'PNG':
            raise ValueError('source_not_png')
        w, h = im.size
        im.verify()
    if w < 1536 or h < 1920:
        raise ValueError(f'undersized_original:{w}x{h}')
    digest = sha(image)
    if (meta.get('schema') != 'exodia.independent-portrait-source/v1'
        or meta.get('source_kind') != 'independent_standalone_native'
        or meta.get('derived_from_composite') is not False
        or meta.get('native_canvas') != [w,h]
        or meta.get('original_sha256') != digest
        or meta.get('original_filename') != image.name
        or meta.get('source_method') not in ('independent_image_render', 'standalone_artist_export')):
        raise ValueError('independent_original_hash_or_provenance_mismatch')
    return meta, [w,h], digest

def preapproval(key, staging, original_sha):
    r = staging / 'registration' / (key + '.json')
    a = staging / 'approvals' / (key + '.json')
    if not r.is_file() or not a.is_file():
        return False
    reg,approval = load(r),load(a)
    return bool(reg.get('source_image_sha256') == original_sha
        and approval.get('source_image_sha256') == original_sha
        and reg.get('source_provenance') == approval.get('source_provenance')
        and reg.get('method') == 'human_annotated_from_actual_image'
        and reg.get('human_review') == 'completed'
        and isinstance(reg.get('source_points_px'),dict)
        and approval.get('normalized_visual_review') == 'completed'
        and approval.get('approved_by') == 'owner'
        and approval.get('allow_normalization') is True
        and isinstance(approval.get('owner_confirmation_reference'),str)
        and len(approval.get('owner_confirmation_reference','')) >= 8
        and approval.get('owner_confirmation_reference') == reg.get('owner_confirmation_reference'))

def queue_batch(queue_path=QUEUE, staging=STAGING, production=PRODUCTION,
                source_dir=None, approve=False, commit=False):
    registry_file = production / 'portrait_registry.json'
    registry = load(registry_file)
    rows = validate_queue(load(queue_path),load(staging/'manifest_template.json'),registry)
    reports=[]
    for row in rows:
        key=row['key']
        entry={'key':key,'priority':row['priority'],'status':'AWAITING_SOURCE'}
        state=load(registry_file)['states'][key]
        if state.get('status') == 'verified':
            entry['status']='ALREADY_VERIFIED'
            reports.append(entry)
            continue
        staged=staging/'incoming'/(key+'.png')
        candidate=(source_dir/(key+'.png')) if source_dir else staged
        proof=(source_dir/(key+'.source.json')) if source_dir else staging/'incoming'/(key+'.source.json')
        if not candidate.is_file():
            reports.append(entry)
            continue
        try:
            provenance,canvas,digest=validate_original(candidate,proof)
            if source_dir:
                staged.parent.mkdir(parents=True,exist_ok=True)
                if staged.exists() and sha(staged) != digest:
                    raise ValueError('source_conflict_no_overwrite')
                if not staged.exists():
                    shutil.copy2(candidate,staged)
                proof_dst=staging/'incoming'/(key+'.source.json')
                if proof_dst.exists() and load(proof_dst) != provenance:
                    raise ValueError('provenance_conflict_no_overwrite')
                if not proof_dst.exists():
                    shutil.copy2(proof,proof_dst)
            image, transform=normalize_portrait(staged)
            preview=staging/'normalized_previews'/(key+'.png')
            if preview.is_file() and sha(preview) != transform['output_sha256']:
                raise ValueError('normalized_preview_conflict')
            if not preview.exists():
                preview.parent.mkdir(parents=True,exist_ok=True)
                preview.write_bytes(image)
            r=staging/'registration'/(key+'.json')
            a=staging/'approvals'/(key+'.json')
            if not r.exists():
                save(r, {'state_key':key,'source_image_sha256':digest,
                  'source_provenance':provenance,'source_points_px':None,
                  'method':'pending_actual_image_landmark_measurement',
                  'human_review':'pending','owner_confirmation_reference':None,
                  'note':'Target y=633.6 and width=614.4 are not measured landmarks.'})
            if not a.exists():
                save(a,{'schema':'exodia.portrait-static-approval-record/v1',
                  'state_key':key,'category':'action','source_image_sha256':digest,
                  'source_provenance':provenance,'allow_normalization':True,
                  'normalized_visual_review':'pending','approved_by':None,
                  'owner_confirmation_reference':None,'reviewed_by':None})
            entry.update(status='STAGED_PENDING_APPROVAL',source_canvas=canvas,
                         source_sha256=digest,normalized_sha256=transform['output_sha256'])
            if approve and preapproval(key,staging,digest):
                cmd=[sys.executable,str(ROOT/'orchestrator/tools/ingest_standalone_portrait.py'),
                     '--state',key,'--source',str(staged),'--staging-root',str(staging),
                     '--registry-root',str(production),'--normalize']
                if commit:cmd.append('--commit')
                proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
                entry.update(status=('COMMITTED' if commit else 'PREFLIGHT_PASSED') if proc.returncode == 0 else 'INGEST_FAILED',
                             exit_code=proc.returncode,console_tail=(proc.stderr+proc.stdout)[-2000:])
        except (OSError,ValueError) as exc:
            entry.update(status='SOURCE_REJECTED',reason=str(exc))
        reports.append(entry)
    verified=sum(v['status']=='verified' for v in load(registry_file)['states'].values())
    return {'schema':'exodia.albedo-core-actions-report/v1','states':reports,
            'verified_total':verified,'target':33,'committed_this_run':sum(v['status']=='COMMITTED' for v in reports),
            'release_enabled':load(registry_file)['release']['enabled']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,default=QUEUE)
    p.add_argument('--staging-root',type=Path,default=STAGING)
    p.add_argument('--registry-root',type=Path,default=PRODUCTION)
    p.add_argument('--source-dir',type=Path)
    p.add_argument('--approve',action='store_true',help='Only validate existing owner review; never auto-author approval')
    p.add_argument('--commit',action='store_true')
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    try:
        result=queue_batch(args.queue,args.staging_root,args.registry_root,args.source_dir,args.approve,args.commit)
    except (ValueError,OSError,KeyError) as exc:
        print('[FAIL] '+str(exc),file=sys.stderr)
        return 2
    for state in result['states']:
        print(f"[{state['status']}] {state['key']}",file=sys.stderr)
    print(f"[INFO] {result['verified_total']}/33 verified",file=sys.stderr)
    print(json.dumps(result,indent=2))
    if args.report:save(args.report,result)
    return 0

if __name__=='__main__':raise SystemExit(main())
