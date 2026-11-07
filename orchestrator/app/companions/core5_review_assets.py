"""Local, fail-closed Gate 2/Core-Five workbench asset import.

Serves only five SHA-bound, unapproved concept review images from an operator's
Gate 1 review ZIP. Not a producer or publisher of native production artwork.
"""
from __future__ import annotations
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
from threading import Lock
from zipfile import ZipFile, BadZipFile
import shutil
import tempfile
from PIL import Image, UnidentifiedImageError

STATES=('idle','working','explaining','monitoring','pointing')
MAX_BUNDLE=65*1024*1024
MAX_CONTENT=120*1024*1024
MAX_MEMBER=18*1024*1024
IMPORT_LOCK=Lock()

def sha_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()

def _png(blob: bytes, size: tuple[int,int]):
    try:
        with Image.open(BytesIO(blob)) as im:
            if im.format!='PNG' or im.size!=size: raise ValueError('invalid_image_dimensions_or_format')
            im.verify()
    except (OSError,UnidentifiedImageError) as exc:
        raise ValueError('invalid_image_bytes') from exc

def expected_telemetry(project_root: Path) -> dict:
    path=project_root.parent/'assets'/'review'/'albedo_core5'/'verified_concept_pixel_telemetry_2026-11-02.json'
    return json.loads(path.read_text(encoding='utf-8'))

def _locations(project_root: Path):
    return project_root/'app_data'/'core5_review'

def current_manifest(project_root: Path) -> dict:
    root=_locations(project_root)
    expected=expected_telemetry(project_root)
    states={}
    for state in STATES:
        source=expected['states'][state]
        output=root/(state+'.png')
        actual=sha_bytes(output.read_bytes()) if output.is_file() else None
        known=actual==source['review_preview_sha256']
        states[state]={
           'label':state.capitalize(),
           'availability':'unapproved_concept_review' if known else 'missing_review_asset',
           'image_url':f'/api/albedo/core5/review-assets/{state}' if known else None,
           'sha256':actual if known else None,
           'source_filename':source['source_filename'],
           'source_sha256':source['original_source_sha256'],
           'canvas':[1536,1920],
           'source_canvas':[1122,1402],
           'measurements':{
             'eye_y':source['measured_output_eye_y_px'],
             'shoulder_y':source['measured_output_shoulder_y_px'],
             'eye_delta':source['eye_delta_px'],
             'shoulder_delta':source['shoulder_delta_px'],
             'head_width_px':source['estimated_head_width_px'],
             'numeric_provisional_pass':source['provisional_numeric_pass'],
           },
           'production_status':'pending_production_art',
           'owner_approved':False,
           'native_master':False,
           'art_kind':'verified_concept_resampled_review_only'}
    return {'schema':'exodia.core5-live-workbench/v2',
            'release_enabled':False,'mode':'review_only','state_order':list(STATES),
            'all_five_loaded':all(states[x]['availability']=='unapproved_concept_review' for x in STATES),
            'production_masters_loaded':0,'generated_28_states':0,
            'states':states,
            'warning':'These are calibrated 1122x1402 concept resamples, NOT native production masters or approved art.'}

def import_review_zip(project_root: Path, archive: bytes) -> dict:
    if not isinstance(archive,bytes) or not archive or len(archive)>MAX_BUNDLE:
        raise ValueError('invalid_archive_size')
    if not __import__('zipfile').is_zipfile(BytesIO(archive)):
        raise ValueError('invalid_zip')
    expected=expected_telemetry(project_root)['states']
    blobs={}
    with ZipFile(BytesIO(archive)) as bundle:
        entries=bundle.infolist()
        if sum(m.file_size for m in entries)>MAX_CONTENT:
            raise ValueError('unsafe_uncompressed_archive_size')
        by_name={}
        for item in entries:
            if item.is_dir():continue
            filename=item.filename.replace('\\','/')
            path=PurePosixPath(filename)
            if (filename.startswith('/') or '..' in path.parts or
                any(part.endswith(':') for part in path.parts) or
                item.file_size>MAX_MEMBER or filename in by_name):
                raise ValueError('unsafe_or_duplicated_zip_member')
            by_name[filename]=item
        for state in STATES:
            record=expected[state]
            source_name='originals/'+record['source_filename']
            preview_name='aligned_previews/'+state+'_aligned_review.png'
            for path,known,size in (
                (source_name,record['original_source_sha256'],(1122,1402)),
                (preview_name,record['review_preview_sha256'],(1536,1920))):
                if path not in by_name:
                    raise ValueError('missing_verified_'+state+'_'+path)
                with bundle.open(by_name[path]) as fh:
                    data=fh.read(MAX_MEMBER+1)
                if len(data)>MAX_MEMBER:raise ValueError('member_too_large')
                if sha_bytes(data)!=known:
                    raise ValueError('source_sha256_mismatch_'+state)
                _png(data,size)
                blobs[path]=data
    target=_locations(project_root)
    target.parent.mkdir(parents=True,exist_ok=True)
    with IMPORT_LOCK:
        with tempfile.TemporaryDirectory(prefix='core5-review-',dir=str(target.parent)) as tmp:
            stage=Path(tmp)
            for state in STATES:
                path='aligned_previews/'+state+'_aligned_review.png'
                (stage/(state+'.png')).write_bytes(blobs[path])
            # Import is never an upgrade of the production registry.
            target.mkdir(parents=True,exist_ok=True)
            for state in STATES:
                shutil.move(str(stage/(state+'.png')),str(target/(state+'.png')))
    result=current_manifest(project_root)
    if not result['all_five_loaded']:
        raise ValueError('post_import_hash_validation_failed')
    return result

def local_asset(project_root: Path, state: str) -> Path | None:
    if state not in STATES:return None
    current=current_manifest(project_root)
    if current['states'][state]['availability']!='unapproved_concept_review':
        return None
    return _locations(project_root)/(state+'.png')
