"""Gate 4: pin and stage real independently generated review PNGs.

Run on development/exodia-foundation ONLY. Downloads an already completed
image-generation job by its recorded result URL, verifies original bytes,
performs a tiny symmetric center crop plus ONE uniform downsample, and places
the actual verified image in the existing FastAPI 33-state review store.

No image is counted from a queued job or a text prompt. Production release,
owner approvals and signed portrait registry are NEVER written here.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import argparse
import os
import tempfile
from PIL import Image, ImageOps

NATIVE = (1536, 1920)
MAX_SOURCE_BYTES = 22 * 1024 * 1024
ALLOWED_HOSTS = frozenset({'d8j0ntlcm91z4.cloudfront.net'})
SEED_RELATIVE = Path('assets/review/albedo_core5/gate4_generated_review_candidates.json')
STORE_RELATIVE = Path('orchestrator/app_data/albedo_33_review')


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def verified_source(job: dict, existing: Path) -> bytes:
    expected = job['original_sha256']
    if existing.is_file():
        data = existing.read_bytes()
        if digest(data) != expected:
            raise ValueError('existing_original_corrupt_do_not_overwrite:'+job['state'])
        return data
    url = job.get('result_url', '')
    target = urlparse(url)
    if target.scheme != 'https' or target.hostname not in ALLOWED_HOSTS:
        raise ValueError('untrusted_generation_download_host')
    request = Request(url, headers={'User-Agent': 'EXODIA-Gate4-ProvenanceVerifier/1.0'})
    with urlopen(request, timeout=45) as res:
        data = res.read(MAX_SOURCE_BYTES+1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError('oversized_image_original')
    if digest(data) != expected:
        raise ValueError('downloaded_original_sha256_mismatch:'+job['state'])
    return data


def normalise(data: bytes, job: dict) -> tuple[bytes, str]:
    with Image.open(BytesIO(data)) as im:
        if im.format != 'PNG' or list(im.size) != job['original_dimensions']:
            raise ValueError('original_canvas_or_format_unverified')
        if im.width < NATIVE[0] or im.height < NATIVE[1]:
            raise ValueError('source_is_upscale_forbidden')
        if im.mode != 'RGB':
            raise ValueError('source_color_mode_unexpected')
        crop_box = tuple(job['crop_xyxy'])
        if len(crop_box)!=4:
            raise ValueError('crop_box_invalid')
        l,t,r,b = crop_box
        if not all(type(x) is int for x in crop_box):
            raise ValueError('crop_coordinates_not_integer')
        if l<0 or t<0 or r>im.width or b>im.height:
            raise ValueError('crop_outside_original')
        width,height=r-l,b-t
        if width*5 != height*4 or width<NATIVE[0] or height<NATIVE[1]:
            raise ValueError('crop_not_native_resolution_4_by_5')
        if max(l,im.width-r,t,im.height-b)>max(im.size)*0.02:
            raise ValueError('cropping_more_than_two_percent_prohibited')
        if abs(l-(im.width-r))>1 or abs(t-(im.height-b))>1:
            raise ValueError('asymmetric_cropping_prohibited')
        normalised = im.crop(crop_box).resize(NATIVE,Image.Resampling.LANCZOS)
        raw_pixel_sha = digest(normalised.tobytes())
        if raw_pixel_sha != job['expected_normalized_pixel_sha256']:
            raise ValueError('normalised_pixel_sha256_mismatch')
        output = BytesIO()
        normalised.save(output, format='PNG', optimize=True)
        candidate = output.getvalue()
        if job.get('expected_normalized_file_sha256') and digest(candidate)!=job['expected_normalized_file_sha256']:
            raise ValueError('normalised_file_sha256_mismatch')
        return candidate, raw_pixel_sha


def ingest_one(root: Path, job: dict) -> dict:
    name = job.get('state')
    if name != 'celebrating':
        raise ValueError('unreviewed_generation_job_not_authorized')
    if job.get('owner_approved') is not False or job.get('production_release_enabled') is not False:
        raise ValueError('invalid_release_claim')
    if job.get('status') != 'GENERATED_ORIGINAL_BYTES_VERIFIED_UNAPPROVED':
        raise ValueError('job_is_not_a_completed_art_file')
    if job.get('generator_model') != 'nano_banana_2_1' or not job.get('generator_job_id'):
        raise ValueError('unknown_generation_provenance')
    request = job.get('generation_request')
    if (not isinstance(request,dict) or request.get('model')!=job['generator_model']
            or request.get('aspect_ratio')!='4:5' or request.get('resolution')!='2k'
            or not isinstance(request.get('prompt'),str)
            or len(request['prompt'])<300
            or request.get('reference_original_sha256s')!=[
                '4de9758f8ea2f3f6f24af18d5e5dba8ac8c723c18afa7d55af6668456d2c6e9d',
                'd55da7f4ca4e93a5d40592e97fe5c04cc6e3d9aaa8cbe8f24c64ee7e08de3b62']):
        raise ValueError('generation_request_provenance_incomplete')
    job_input_hash = digest(json.dumps(request,sort_keys=True,ensure_ascii=False,
                                       separators=(',',':')).encode('utf-8'))
    if job.get('generation_input_manifest_sha256') and job['generation_input_manifest_sha256']!=job_input_hash:
        raise ValueError('generation_prompt_manifest_hash_mismatch')
    store = root / STORE_RELATIVE
    original_path = store/'sources'/(name+'_original.png')
    output_path = store/'images'/(name+'.png')
    original_bytes = verified_source(job,original_path)
    normalised_bytes, pixel_sha = normalise(original_bytes,job)
    if output_path.is_file() and digest(output_path.read_bytes())!=digest(normalised_bytes):
        raise ValueError('existing_normalised_image_conflicts')
    staging = store/'review_index.json'
    index = json.loads(staging.read_text()) if staging.is_file() else {
      'schema':'exodia.state33-review-index/v1','states':{}}
    if index.get('schema')!='exodia.state33-review-index/v1':
        raise ValueError('invalid_existing_index')
    old = index['states'].get(name)
    if old and old.get('image_sha256')!=digest(normalised_bytes):
        raise ValueError('existing_state_review_hash_conflict')
    image_hash=digest(normalised_bytes)
    source_hash=digest(original_bytes)
    record = {
      'source_filename': name+'_original.png',
      'source_sha256': source_hash,
      'image_sha256': image_hash,
      'generator_job_id': job['generator_job_id'],
      'generator_model': job['generator_model'],
      'generation_input_manifest_sha256': job_input_hash,
      'source_dimensions': job['original_dimensions'],
      'normalization': {
        'kind': 'symmetric_center_crop_then_uniform_lanczos',
        'crop_xyxy': job['crop_xyxy'],
        'cropped_size': [job['crop_xyxy'][2]-job['crop_xyxy'][0],
                         job['crop_xyxy'][3]-job['crop_xyxy'][1]],
        'output_size': list(NATIVE),
        'source_pixel_sha256': pixel_sha,
      },
      'pose_key':name,
      'pose_evidence_description':job['pose_evidence_description'],
      'geometry_status':'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT',
      'review_status':'GENERATED_UNAPPROVED',
      'owner_approved':False,
      'production_status':'pending_production_art',
      'independent_source_kind':'independently_authored_higher_resolution',
    }
    if staging.is_file() and name in index['states'] and index['states'][name]!=record:
        raise ValueError('existing_state_metadata_conflicts')
    # All preflight and checksums complete before writing source/output/index.
    original_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    original_path.write_bytes(original_bytes)
    output_path.write_bytes(normalised_bytes)
    index['states'][name]=record
    staging.write_text(json.dumps(index,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    proof={'state':name,'generator_job_id':job['generator_job_id'],
        'original_sha256':source_hash,'original_dimensions':job['original_dimensions'],
        'normalized_sha256':image_hash,'normalized_dimensions':list(NATIVE),
        'normalized_pixel_sha256':pixel_sha,'source_kind':'independently_authored_higher_resolution',
        'normalization':record['normalization'],
        'native_review_image_generated':True,
        'anatomy_and_geometry_final_status':'NOT_MEASURED_FAIL_CLOSED',
        'owner_approved':False,'production_release_enabled':False}
    return proof


def run(root: Path) -> dict:
    data = json.loads((root / SEED_RELATIVE).read_text(encoding='utf-8'))
    if data.get('schema')!='exodia.gate4-independent-render-seeds/v1':
        raise ValueError('unrecognized_provenance_manifest_schema')
    jobs=data['jobs']
    if len(jobs)!=1:raise ValueError('unexpected_number_of_verified_jobs')
    results = [ingest_one(root,j) for j in jobs]
    output={
      'schema':'exodia.gate4-real-image-proof/v1',
      'generated_unapproved_native_review_images':len(results),
      'production_release_enabled':False,
      'owner_approved_count':0,
      'remaining_28_review_images_pending':28-len(results),
      'states':{r['state']:r for r in results},
    }
    p=root/'assets'/'review'/'albedo_core5'/'gate4_native_review_art_actual_report.json'
    p.write_text(json.dumps(output,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return output


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[2])
    a=ap.parse_args()
    report=run(a.repo_root)
    print(json.dumps(report,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
