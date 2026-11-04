"""EXODIA Tower Gate 4: stage 32 independently generated 2K Runway originals.

This is a verified-byte review-art intake; does not approve anatomy, geometry,
identity, authenticity of references, or release. Never modifies production
portrait_registry.json or main. Each image must originate from a distinct
finished generation task, have verifiable PNG pixels, and match SHA-256.
"""
from __future__ import annotations
import hashlib,json,urllib.request,sys
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'sources'
IMAGES=ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'images'
INDEX=ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'review_index.json'
QUEUE=ROOT/'assets'/'review'/'albedo_core5'/'authorized_28_state_art_queue.json'
GATE=ROOT/'assets'/'blueprints'/'albedo_28_state_batch_gate.json'
MANIFEST_DIR=ROOT/'assets'/'review'/'albedo_core5'
CORE={'idle','working','explaining','monitoring','pointing'}

def sha(b):return hashlib.sha256(b).hexdigest()
def read_manifest():
    batches=[]
    for n in range(1,5):
        p=MANIFEST_DIR/f'gate4_runway_verified_batch_{n}.json'
        x=json.loads(p.read_text(encoding='utf-8'))
        if x.get('schema')!='exodia.gate4.runway-source-verified/v1' or len(x.get('states',[]))!=8:
            raise ValueError(f'invalid_completed_independent_batch_{n}')
        batches.extend(x['states'])
    names=[x['state'] for x in batches]
    if len(set(names))!=32 or len(names)!=32:raise ValueError('expected_32_independent_generation_states')
    queue=json.loads(QUEUE.read_text(encoding='utf-8'))
    expected={x['state_key'] for x in queue['states']}|CORE
    expected.discard('celebrating')
    if set(names)!=expected:raise ValueError('32_state_names_not_authorized_or_incomplete')
    ids=[x.get('task_id') for x in batches]
    if len(set(ids))!=32 or not all(ids):raise ValueError('unique_generation_task_ids_required')
    src_sha=[x.get('source_sha256') for x in batches]
    if len(set(src_sha))!=32:raise ValueError('duplicate_source_sha256')
    return batches,queue

def checked_download(item,path):
    expected=item['source_sha256']
    if path.is_file():
        old=path.read_bytes()
        if sha(old)!=expected:raise ValueError('conflicting_existing_source:'+item['state'])
        return old
    from urllib.parse import urlparse
    url=item['result_url']
    u=urlparse(url)
    if u.scheme!='https' or u.netloc!='dnznrvs05pmza.cloudfront.net':
        raise ValueError('unexpected_image_result_host')
    req=urllib.request.Request(url,headers={'User-Agent':'EXODIA-Tower-VerifiedArtIntake/1.0'})
    with urllib.request.urlopen(req,timeout=120) as f:
        buf=f.read(25000001)
    if len(buf)>25000000:raise ValueError('oversized_source_png')
    if sha(buf)!=expected:raise ValueError('download_hash_mismatch:'+item['state'])
    return buf

def normalized_png(source,item):
    with Image.open(BytesIO(source)) as p:
        if p.format!='PNG':raise ValueError('source_must_be_png')
        if list(p.size)!=item['source_dimensions']:raise ValueError('source_dimensions_mismatch')
        p.verify()
    with Image.open(BytesIO(source)) as p:
        w,h=p.size
        if w<1536 or h<1920:raise ValueError('source_below_native')
        k=min(w//4,h//5); cw,ch=4*k,5*k
        box=((w-cw)//2,(h-ch)//2,(w-cw)//2+cw,(h-ch)//2+ch)
        if list(box)!=item['crop_xyxy']:raise ValueError('source_crop_transform_mismatch')
        if max(w-cw,h-ch)>max(w,h)*0.05:raise ValueError('material_source_crop')
        img=p.convert('RGB').crop(box).resize((1536,1920),Image.Resampling.LANCZOS)
        if sha(img.tobytes())!=item['normalized_pixel_sha256']:
            raise ValueError('pixel_transform_mismatch:'+item['state'])
        b=BytesIO();img.save(b,format='PNG',optimize=True)
        raw=b.getvalue()
        if sha(raw)!=item['normalized_sha256']:raise ValueError('normalized_byte_hash_mismatch:'+item['state'])
        return raw

def perform():
    sources,queue=read_manifest()
    idx=json.loads(INDEX.read_text(encoding='utf-8'))
    if idx.get('schema')!='exodia.state33-review-index/v1':raise ValueError('invalid_review_index')
    if set(idx['states'])!={'celebrating'} and set(idx['states'])!=set(x['state'] for x in sources)|{'celebrating'}:
        raise ValueError('unexpected_review_index_state_set')
    gate=json.loads(GATE.read_text(encoding='utf-8'))
    if gate.get('production_release_enabled') is not False:raise ValueError('release_is_not_locked')
    author={x['state_key']:x for x in queue['states']}
    seen_sha={idx['states']['celebrating']['source_sha256']}
    report={'schema':'exodia.gate4.all-original-source-files-audited/v1','all_art_state_count':33,
            'review_originals_verified':0,'review_normalized_verified':0,
            'production_release_enabled':False,'owner_approved_count':0,
            'geometry_and_anatomy_approved_count':0,'states':{}}
    # Verify all 32 files BEFORE committing any updated index or queue.
    pending=[]
    for item in sources:
        name=item['state']
        if item.get('status')!='ACTUAL_STANDALONE_SOURCE_VERIFIED':
            raise ValueError('not_a_verified_completed_render:'+name)
        if item.get('model')!='Runway nano-banana-2 2K':
            raise ValueError('unrecognized_model:'+name)
        if item.get('owner_approved') is not False or item.get('production_release_enabled') is not False:
            raise ValueError('forged_approval:'+name)
        sp=SOURCE/(name+'_original.png');op=IMAGES/(name+'.png')
        original=checked_download(item,sp)
        if sha(original)!=item['source_sha256']:raise ValueError('source_hash_error:'+name)
        if item['source_sha256'] in seen_sha:raise ValueError('cloned_exact_source:'+name)
        seen_sha.add(item['source_sha256'])
        output=normalized_png(original,item)
        if op.is_file() and sha(op.read_bytes())!=sha(output):
            raise ValueError('conflicting_existing_normalized:'+name)
        pending.append((item,original,output))
        report['states'][name]={
            'source_sha256':sha(original),'image_sha256':sha(output),
            'source_dimensions':item['source_dimensions'],'native_review_dimensions':[1536,1920],
            'task_id':item['task_id'],'status':'REAL_ORIGINAL_AND_PNG_HASH_VERIFIED',
            'geometric_landmarks':'NOT_OWNER_CERTIFIED',
            'owner_approved':False}
    SOURCE.mkdir(parents=True,exist_ok=True);IMAGES.mkdir(parents=True,exist_ok=True)
    for item,original,output in pending:
        name=item['state']
        (SOURCE/(name+'_original.png')).write_bytes(original)
        (IMAGES/(name+'.png')).write_bytes(output)
        entry={
            'source_filename':name+'_original.png','source_sha256':sha(original),
            'image_sha256':sha(output),'generator_job_id':item['task_id'],
            'generator_model':'Runway nano-banana-2 2K',
            'generation_input_manifest_sha256':item['generation_prompt_sha256'],
            'source_dimensions':item['source_dimensions'],
            'normalization':{'kind':'symmetric_center_crop_then_uniform_lanczos',
                             'crop_xyxy':item['crop_xyxy'],
                             'cropped_size':[item['crop_xyxy'][2]-item['crop_xyxy'][0],
                                             item['crop_xyxy'][3]-item['crop_xyxy'][1]],
                             'output_size':[1536,1920],
                             'source_pixel_sha256':item['normalized_pixel_sha256']},
            'pose_key':name,'pose_evidence_description':item.get('pose_brief',''),
            'geometry_status':'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT',
            'review_status':'GENERATED_UNAPPROVED','owner_approved':False,
            'production_status':'pending_production_art',
            'independent_source_kind':'independently_authored_higher_resolution'}
        old=idx['states'].get(name)
        if old and old['source_sha256']!=entry['source_sha256']:
            raise ValueError('existing_review_image_conflicts:'+name)
        idx['states'][name]=entry
        if name not in CORE:
            q=author[name]
            q.update(generation_status='generated_unapproved_native_candidate',
                     source_sha256=sha(original),output_sha256=sha(output),
                     original_canvas=item['source_dimensions'],output_canvas=[1536,1920],
                     generation_job_id=item['task_id'],human_pose_review='pending',
                     production_status='pending_production_art',owner_hash_bound_approval=None)
    if len(idx['states'])!=33:raise ValueError('incomplete_real_33_state_index')
    queue['generated_count']=sum(x['generation_status']=='generated_unapproved_native_candidate' for x in queue['states'])
    if queue['generated_count']!=28:raise ValueError('incomplete_28_state_expansion')
    gate['generated_states']=28
    INDEX.write_text(json.dumps(idx,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    QUEUE.write_text(json.dumps(queue,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    GATE.write_text(json.dumps(gate,indent=2)+'\n',encoding='utf-8')
    report['review_originals_verified']=33
    report['review_normalized_verified']=33
    report['states']['celebrating']={
        'source_sha256':idx['states']['celebrating']['source_sha256'],
        'image_sha256':idx['states']['celebrating']['image_sha256'],
        'status':'PREVIOUSLY_VERIFIED_INDEPENDENT_ORIGINAL',
        'geometry':'FAIL_ALREADY_RECORDED','owner_approved':False}
    (MANIFEST_DIR/'gate4_all_real_33_state_byte_audit.json').write_text(
        json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'verified_33_real_originals':33,'verified_33_native_review_PNGs':33,
                      'expansion_states_generated':queue['generated_count'],
                      'owner_approved':0,'production_release_enabled':False}))
if __name__=='__main__':perform()
