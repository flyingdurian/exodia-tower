"""Stage only real, SHA-verified standalone high-resolution Runway renders.

This tool is release-safe and idempotent. The render provider's task ID is
provenance, not proof that artwork exists: a byte-for-byte verified original
file and a re-created SHA-matched native review PNG are mandatory.
"""
from __future__ import annotations
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import argparse
import json
import re
from PIL import Image

SIZE=(1536,1920)
DOMAIN='dnznrvs05pmza.cloudfront.net'
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
HEX=re.compile(r'^[a-f0-9]{64}$')
LIMIT=22*1024*1024
MANIFEST=Path('assets/review/albedo_core5/gate4_runway_verified_sources.json')
STORE=Path('orchestrator/app_data/albedo_33_review')
QUEUE=Path('assets/review/albedo_core5/authorized_28_state_art_queue.json')
BLUEPRINT=Path('assets/blueprints/albedo_28_state_batch_gate.json')
REPORT=Path('assets/review/albedo_core5/gate4_runway_verified_report.json')


def hexsha(data):
    return sha256(data).hexdigest()


def read_download(job, prior_path):
    if prior_path.is_file():
        b=prior_path.read_bytes()
    else:
        uri=urlparse(job.get('source_url',''))
        if uri.scheme!='https' or uri.hostname!=DOMAIN:
            raise ValueError('source_url_host_not_authorized')
        with urlopen(Request(job['source_url'],headers={
                'User-Agent':'EXODIA/4-StandaloneSourceVerification'
                }),timeout=60) as res:
            b=res.read(LIMIT+1)
    if len(b)>LIMIT or not b:
        raise ValueError('invalid_or_oversized_original')
    if hexsha(b)!=job['original_sha256']:
        raise ValueError('source_sha256_mismatch:'+job['state'])
    return b


def process(job,data):
    if len(job.get('original_dimensions',[]))!=2:
        raise ValueError('original_dimensions_missing')
    with Image.open(BytesIO(data)) as im:
        if im.format!='PNG' or list(im.size)!=job['original_dimensions']:
            raise ValueError('original_png_format_or_dimensions_incorrect')
        if im.width<SIZE[0] or im.height<SIZE[1]:
            raise ValueError('original_source_smaller_than_native')
        if im.mode!='RGB':
            raise ValueError('non_rgb_original_requires_explicit_review')
        box=job['crop_xyxy']
        if not isinstance(box,list) or len(box)!=4 or any(type(v)!=int for v in box):
            raise ValueError('invalid_crop_coordinates')
        l,t,r,b=box
        if l<0 or t<0 or r>im.width or b>im.height or r<=l or b<=t:
            raise ValueError('source_crop_oob')
        w,h=r-l,b-t
        if w*5!=h*4 or w<SIZE[0] or h<SIZE[1]:
            raise ValueError('source_crop_not_exact_4_by_5')
        if abs(l-(im.width-r))>1 or abs(t-(im.height-b))>1:
            raise ValueError('source_crop_asymmetric')
        if max(l,t,im.width-r,im.height-b)>max(im.size)*0.02:
            raise ValueError('source_crop_loses_anatomy')
        cropped=im.crop(box)
        out=cropped.resize(SIZE,Image.Resampling.LANCZOS)
        pixel_hash=hexsha(out.tobytes())
        if pixel_hash!=job['normalized_pixel_sha256']:
            raise ValueError('normalized_pixels_mismatch:'+job['state'])
        output=BytesIO()
        out.save(output,format='PNG',optimize=True)
        b=output.getvalue()
        if hexsha(b)!=job['normalized_sha256']:
            raise ValueError('normalized_png_file_sha256_mismatch:'+job['state'])
        return b


def stage(root):
    seed=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    if seed.get('schema')!='exodia.gate4-runway-verified-jobs/v1':
        raise ValueError('invalid_seed_schema')
    jobs=seed.get('jobs') or []
    if not jobs:raise ValueError('empty_completed_job_manifest')
    queue_path=root/QUEUE
    queue=json.loads(queue_path.read_text(encoding='utf-8'))
    bykey={s['state_key']:s for s in queue['states']}
    if len(bykey)!=28:raise ValueError('invalid_authorized_queue')
    if not all(not s.get('owner_hash_bound_approval') for s in queue['states']):
        raise ValueError('unexpected_owner_approval_in_batch')
    store=root/STORE
    index_path=store/'review_index.json'
    index=json.loads(index_path.read_text()) if index_path.is_file() else {
        'schema':'exodia.state33-review-index/v1','states':{}}
    if index.get('schema')!='exodia.state33-review-index/v1':
        raise ValueError('review_index_schema_mismatch')
    seen_original={v.get('source_sha256') for v in index['states'].values()}
    seen_output={v.get('image_sha256') for v in index['states'].values()}
    seen_jobs={v.get('generator_job_id') for v in index['states'].values()}
    prepared=[]
    encountered=set()
    for job in jobs:
        state=job.get('state')
        if state not in bykey or state in encountered:
            raise ValueError('unauthorized_or_duplicate_state')
        encountered.add(state)
        if job.get('status')!='GENERATED_ORIGINAL_BYTES_VERIFIED_UNAPPROVED':
            raise ValueError('no_actual_verified_source')
        if job.get('model')!='nano-banana-2' or not UUID.fullmatch(job.get('task_id','')):
            raise ValueError('untracked_generation_job')
        if job.get('owner_approved') is not False or job.get('production_release_enabled') is not False:
            raise ValueError('fabricated_approval')
        if not all(HEX.fullmatch(job.get(k,'')) for k in (
                'original_sha256','normalized_sha256','normalized_pixel_sha256')):
            raise ValueError('missing_sha256')
        if job['original_sha256'] in seen_original or job['normalized_sha256'] in seen_output:
            old=index['states'].get(state)
            if not old or old.get('source_sha256')!=job['original_sha256'] or old.get('image_sha256')!=job['normalized_sha256']:
                raise ValueError('cloned_or_reused_original')
        elif job['task_id'] in seen_jobs:
            raise ValueError('duplicated_generation_task')
        source=store/'sources'/(state+'_original.png')
        output=store/'images'/(state+'.png')
        original=read_download(job,source)
        normalized=process(job,original)
        if output.is_file() and hexsha(output.read_bytes())!=job['normalized_sha256']:
            raise ValueError('output_conflicts_with_existing_art')
        if bykey[state].get('generation_status')=='generated_unapproved_native_candidate':
            if bykey[state].get('source_sha256')!=job['original_sha256']:
                raise ValueError('queue_conflict')
        elif bykey[state].get('generation_status')!='authorized_not_generated':
            raise ValueError('unauthorized_queue_status')
        record={
            'source_filename':state+'_original.png',
            'source_sha256':job['original_sha256'],
            'image_sha256':job['normalized_sha256'],
            'generator_job_id':job['task_id'],
            'generator_model':job['model'],
            'generation_service':'Runway',
            'source_dimensions':job['original_dimensions'],
            'normalization':{
                'kind':'symmetric_center_crop_then_uniform_lanczos',
                'crop_xyxy':job['crop_xyxy'],
                'cropped_size':[job['crop_xyxy'][2]-job['crop_xyxy'][0],
                                job['crop_xyxy'][3]-job['crop_xyxy'][1]],
                'output_size':list(SIZE),
                'source_pixel_sha256':job['normalized_pixel_sha256'],
            },
            'pose_key':state,
            'pose_evidence_description':bykey[state]['visual_must_show']['action_pose'],
            'geometry_status':'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT',
            'review_status':'GENERATED_UNAPPROVED',
            'owner_approved':False,
            'production_status':'pending_production_art',
            'independent_source_kind':'independently_authored_higher_resolution',
        }
        prior=index['states'].get(state)
        if prior and prior!=record:
            raise ValueError('conflicting_review_index_record')
        seen_original.add(job['original_sha256'])
        seen_output.add(job['normalized_sha256'])
        seen_jobs.add(job['task_id'])
        prepared.append((state,source,output,original,normalized,record,job))
    # Do not mutate registry at any point; files only become review candidates.
    blueprint_file=root/BLUEPRINT
    blueprint=json.loads(blueprint_file.read_text(encoding='utf-8'))
    if blueprint.get('production_release_enabled') is not False:
        raise ValueError('production_gate_not_locked')
    for state,src,out,data,pixels,rec,job in prepared:
        src.parent.mkdir(parents=True,exist_ok=True)
        out.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(data)
        out.write_bytes(pixels)
        index['states'][state]=rec
        bykey[state].update(
            generation_status='generated_unapproved_native_candidate',
            source_sha256=job['original_sha256'],
            output_sha256=job['normalized_sha256'],
            original_canvas=job['original_dimensions'],
            output_canvas=list(SIZE),
            generation_job_id=job['task_id'],
            human_pose_review='pending',
            production_status='pending_production_art',
            owner_hash_bound_approval=None,
        )
    count=sum(s['generation_status']=='generated_unapproved_native_candidate'
              for s in queue['states'])
    queue['generated_count']=count
    blueprint['generated_states']=count
    for path,obj in [
            (index_path,index),(queue_path,queue),(blueprint_file,blueprint)]:
        path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    report={'schema':'exodia.gate4-runway-binary-recovery/v1',
        'verified_standalone_originals_in_this_manifest':len(prepared),
        'expansion_generated_count':count,
        'expansion_missing_count':28-count,
        'core5_native_certified_count':0,
        'owner_approved_count':0,
        'production_release_enabled':False,
        'states':{state:{'source_sha256':job['original_sha256'],
                'output_sha256':job['normalized_sha256'],
                'source_dimensions':job['original_dimensions'],
                'output_dimensions':list(SIZE),
                'task_id':job['task_id'],
                'pose_review':'PENDING_ANATOMY_AND_GEOMETRY'}
                for state,_,_,_,_,_,job in prepared}}
    (root/REPORT).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo-root',type=Path,
                   default=Path(__file__).resolve().parents[2])
    a=p.parse_args()
    print(json.dumps(stage(a.repo_root),indent=2))

if __name__=='__main__':main()
