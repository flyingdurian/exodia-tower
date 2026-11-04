"""EXODIA 33-state review asset catalog and strict native-art intake.

The five Core-Five assets remain SHA-verified CONCEPT previews.
New independently authored artwork can enter a local review sandbox only.
No code path here modifies the signed production registry or release.enabled.
"""
from __future__ import annotations
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from threading import RLock
from zipfile import ZipFile, is_zipfile
from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError
from app.companions import core5_review_assets

LOCK = RLock()
MAX_COMPRESSED = 170 * 1024 * 1024
MAX_TOTAL_UNPACKED = 370 * 1024 * 1024
MAX_MEMBER = 25 * 1024 * 1024
SIZE = (1536, 1920)
SHA = re.compile(r'^[a-f0-9]{64}$')
CORE = tuple(core5_review_assets.STATES)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _base(root: Path) -> Path:
    return root / 'app_data' / 'albedo_33_review'

def _queue(root: Path) -> dict:
    source = root.parent / 'assets' / 'review' / 'albedo_core5' / 'authorized_28_state_art_queue.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    if (data.get('schema') != 'exodia.albedo-28-review-art-authorization/v1'
            or data.get('count') != 28 or len(data.get('states', [])) != 28):
        raise ValueError('invalid_authorized_28_state_queue')
    return data

def _registry(root: Path) -> dict:
    path = root / 'frontend' / 'companions' / 'production' / 'kiko' / 'portrait_registry.json'
    reg = json.loads(path.read_text(encoding='utf-8'))
    if reg.get('release', {}).get('enabled') is not False:
        raise ValueError('production_registry_not_locked')
    return reg

def _png(data: bytes):
    try:
        with Image.open(BytesIO(data)) as im:
            if im.format != 'PNG':
                raise ValueError('must_be_png')
            dimensions = im.size
            im.verify()
        return dimensions
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError('invalid_png') from exc

def dhash(blob: bytes, *, face=False):
    with Image.open(BytesIO(blob)) as im:
        gray = ImageOps.grayscale(im)
        if face:
            width, height = gray.size
            gray = gray.crop((int(width * .15), int(height * .06),
                              int(width * .85), int(height * .63)))
        pixels = list(gray.resize((9, 8), Image.Resampling.LANCZOS).getdata())
    result = 0
    for y in range(8):
        for x in range(8):
            result = (result << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return result

def _index(root: Path) -> dict:
    file = _base(root) / 'review_index.json'
    if not file.is_file():
        return {'schema': 'exodia.state33-review-index/v1', 'states': {}}
    data = json.loads(file.read_text(encoding='utf-8'))
    if data.get('schema') != 'exodia.state33-review-index/v1':
        raise ValueError('invalid_review_index')
    return data

def _valid_local(root: Path, name: str, row: dict) -> bool:
    file = _base(root) / 'images' / (name + '.png')
    return (file.is_file() and SHA.fullmatch(str(row.get('image_sha256', '')))
            and sha(file.read_bytes()) == row['image_sha256']
            and _png(file.read_bytes()) == SIZE)

def manifest(root: Path) -> dict:
    queue = _queue(root)
    prod = _registry(root)
    core = core5_review_assets.current_manifest(root)
    idx = _index(root)
    # Owner Gate 4: 29 states accepted for continued DEVELOPMENT, four
    # corrections outstanding. This review metadata NEVER unlocks production.
    lock_path = root.parent / 'assets' / 'review' / 'albedo_core5' / 'gate4_four_state_correction_lock.json'
    correction_lock = json.loads(lock_path.read_text(encoding='utf-8')) if lock_path.is_file() else None
    if correction_lock is not None:
        if (correction_lock.get('schema') != 'exodia.gate4-four-state-owner-correction-lock/v1'
                or set(correction_lock.get('target_states', [])) != {
                    'angered', 'awaiting_command', 'neutral', 'tantrum'}
                or correction_lock.get('protected_count') != 29):
            raise ValueError('invalid_four_state_owner_development_lock')
        if set(correction_lock.get('frozen_review_hashes', {})) != set(prod['states']):
            raise ValueError('owner_review_lock_mismatches_33_state_registry')
        # A temporary EMPTY image store is permitted for isolated fixture
        # tests and first-time deployment. Once all 33 exist, the 29-image
        # freeze is mandatory and cannot be bypassed by editing the index.
        if len(idx.get('states', {})) == 33:
          for frozen_name, frozen in correction_lock['frozen_review_hashes'].items():
            if frozen_name not in correction_lock['target_states']:
                current = idx.get('states', {}).get(frozen_name)
                if current is None or (current.get('source_sha256') != frozen['original_sha256']
                   or current.get('image_sha256') != frozen['review_sha256']):
                    raise ValueError('protected_29_state_sha_mismatch:' + frozen_name)
    # UI is deliberately Core-Five-first; the signed production registry's
    # canonical state keyset and order remain untouched.
    order = list(CORE) + [name for name in prod['states'] if name not in CORE]
    core_reference = set(CORE)
    queued = {x['state_key']: x for x in queue['states']}
    if set(order) != core_reference.union(queued) or len(order) != 33:
        raise ValueError('33_state_queue_mismatch')
    states = {}
    for name in order:
        metadata = prod['states'][name]
        if metadata.get('status') != 'pending_production_art':
            raise ValueError('non_pending_production_state:' + name)
        item = {
            'key': name,
            'label': metadata['label'],
            'category': metadata['category'],
            'signal_overlay': metadata.get('signal_overlay', 'none'),
            'production_status': 'pending_production_art',
            'owner_approved': False,
            'native_production_certified': False,
            'tentative_reference_approved': name in core_reference,
            'image_url': None,
            'sha256': None,
            'source_sha256': None,
            'source_filename': None,
            'geometry_status': 'NO_IMAGE_MEASURED',
            'art_status': 'PENDING_INDEPENDENT_ART',
            'pose_direction': None,
            'owner_development_status': (correction_lock['frozen_review_hashes'][name]['development_review_status']
                                         if correction_lock else 'UNREVIEWED_FOR_CONTINUED_DEVELOPMENT'),
            'owner_final_visual_approved': False,
        }
        if name in core_reference:
            item['pose_direction'] = 'Core-Five source pose — tentative visual reference'
            art = core['states'][name]
            item['source_filename'] = art['source_filename']
            item['source_sha256'] = art['source_sha256']
            item['measurements'] = art.get('measurements')
            item['geometry_status'] = 'PROVISIONAL_CONCEPT_MIDPOINTS_ONLY'
            if art['availability'] == 'unapproved_concept_review':
                item['art_status'] = 'CONCEPT_REVIEW_AVAILABLE'
                item['image_url'] = art['image_url']
                item['sha256'] = art['sha256']
        else:
            item['pose_direction'] = queued[name]['visual_must_show']['action_pose']
        # A genuinely generated, SHA-verified independent Core-Five review
        # candidate takes precedence over the 1122x1402 concept preview.
        # Neither is owner-approved; signed production registry is unchanged.
        row = idx.get('states', {}).get(name)
        if row and _valid_local(root, name, row):
            item['art_status'] = 'INDEPENDENT_ART_UNAPPROVED_REVIEW'
            item['image_url'] = '/api/albedo/state33/review-assets/' + name
            item['sha256'] = row['image_sha256']
            item['source_sha256'] = row['source_sha256']
            item['source_filename'] = row['source_filename']
            item['geometry_status'] = row.get(
                'geometry_status', 'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT')
            item['independent_source_kind'] = row.get('independent_source_kind')
            item['source_dimensions'] = row.get('source_dimensions')
            item['review_status'] = 'GENERATED_UNAPPROVED'
            if name in core_reference:
                item['pose_direction'] = 'New independently rendered Core-Five review candidate'
                item.pop('measurements', None)  # Never reuse CONCEPT measurements.
            if name=='celebrating':
                evidence_path=(root.parent/'assets'/'review'/'albedo_core5'/
                               'gate4_celebrating_actual_landmark_fail.json')
                if evidence_path.is_file():
                    proof=json.loads(evidence_path.read_text(encoding='utf-8'))
                    if (proof.get('output_sha256')==row['image_sha256']
                            and proof.get('original_sha256')==row['source_sha256']
                            and proof.get('checks',{}).get('owner_visual_approved') is False):
                        measurements=proof['actual_pixel_measurements']
                        item['measurements']={
                            'eye_y':measurements['eye_mid_y_px'],
                            'shoulder_y':measurements['shoulder_mid_y_px'],
                            'eye_delta':measurements['eye_delta_px'],
                            'shoulder_delta':measurements['shoulder_delta_px'],
                            'head_width_px':measurements['head_width_px'],
                            'center_x_px':measurements['eye_center_x_px'],
                            'center_delta_px':measurements['center_delta_px'],
                            'iris_left':measurements['iris_left'],
                            'iris_right':measurements['iris_right'],
                            'shoulder_left':measurements['shoulder_left'],
                            'shoulder_right':measurements['shoulder_right'],
                            'eye_separation_px':measurements['eye_separation_px'],
                            'eye_asymmetry_px':measurements['eye_vertical_asymmetry_px'],
                            'shoulder_asymmetry_px':measurements['shoulder_vertical_asymmetry_px'],
                            'numeric_provisional_pass':False,
                        }
                        item['geometry_status']='ACTUAL_PIXELS_GEOMETRY_FAIL_OWNER_UNREVIEWED'
        # Gate 4: a verified independently generated Core-Five review PNG
        # supersedes the 1122x1402 tentative concept preview in the live
        # workbench only. No native production approval is implied.
        if name in core_reference:
            row = idx.get('states', {}).get(name)
            if row and _valid_local(root, name, row):
                item['art_status'] = 'INDEPENDENT_ART_UNAPPROVED_REVIEW'
                item['image_url'] = '/api/albedo/state33/review-assets/' + name
                item['sha256'] = row['image_sha256']
                item['source_sha256'] = row['source_sha256']
                item['source_filename'] = row['source_filename']
                item['geometry_status'] = 'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT'
                item['measurements'] = None
                item['pose_direction'] = 'Independently illustrated Core-Five '+name+' action; native candidate pending geometric and owner art review'
        states[name] = item
    ready = sum(x['image_url'] is not None for x in states.values())
    core_ready = sum(states[x]['image_url'] is not None for x in CORE)
    real_core = sum(states[x]['art_status']=='INDEPENDENT_ART_UNAPPROVED_REVIEW'
                    for x in CORE)
    concept_core = sum(states[x]['art_status']=='CONCEPT_REVIEW_AVAILABLE'
                       for x in CORE)
    newly_loaded = ready - core_ready
    return {
        'schema': 'exodia.state33-review-workbench/v1',
        'state_order': order,
        'count': 33,
        'core_five_count': 5,
        'additional_state_count': 28,
        'production_release_enabled': False,
        'native_core_five_certified_count': 0,
        'owner_production_approved_count': 0,
        'tentative_reference_signoff_count': 5,
        'artwork_available_count': ready,
        'concept_preview_available_count': concept_core,
        'core_five_independent_review_art_count': real_core,
        'core_native_review_art_available_count': real_core,  # review only, NOT certified production
        'verified_independent_review_art_count': real_core+newly_loaded,
        'additional_review_art_available_count': newly_loaded,
        'states_without_review_images': 33 - ready,
        'batch_review_generation_authorized': True,
        'owner_development_accepted_count': 29 if correction_lock else 0,
        'owner_targeted_correction_count': 4 if correction_lock else 0,
        'targeted_corrections_rendered_count': correction_lock.get('correction_completed',0) if correction_lock else 0,
        'production_status': 'ALL_33_PENDING_PRODUCTION_ART',
        'states': states,
        'warning': 'All generated review files are unapproved. Canonical facial/shoulder geometry and identity still require owner art review; release remains disabled.'
    }

def asset(root: Path, state: str) -> Path | None:
    m = manifest(root)
    row = m['states'].get(state)
    if not row or row['art_status'] != 'INDEPENDENT_ART_UNAPPROVED_REVIEW':
        return None
    return _base(root) / 'images' / (state + '.png')

def import_art(root: Path, archive: bytes) -> dict:
    """Partial or full 28-state original-art batch; art review only, fail closed."""
    # The owner has frozen 29 exact 33-state source/output hashes. The legacy
    # generic import must not bypass the NEW four-state correction gate by
    # overwriting an already complete 33-state library.
    lock_file = root.parent / 'assets' / 'review' / 'albedo_core5' / 'gate4_four_state_correction_lock.json'
    if lock_file.is_file() and len(_index(root).get('states', {})) == 33:
        raise ValueError('owner_locked_33_state_library_use_gate4_four_state_import')
    if not isinstance(archive, bytes) or not archive or len(archive) > MAX_COMPRESSED:
        raise ValueError('review_zip_invalid_size')
    if not is_zipfile(BytesIO(archive)):
        raise ValueError('review_zip_invalid')
    expected = {row['state_key']: row for row in _queue(root)['states']}
    with ZipFile(BytesIO(archive)) as container:
        entries = container.infolist()
        if sum(e.file_size for e in entries) > MAX_TOTAL_UNPACKED:
            raise ValueError('uncompressed_zip_exceeds_safety_limit')
        members = {}
        for e in entries:
            if e.is_dir():
                continue
            path = PurePosixPath(e.filename.replace('\\','/'))
            if ('..' in path.parts or e.filename.startswith('/')
                    or e.file_size > MAX_MEMBER or e.filename in members
                    or any(':' in part for part in path.parts)):
                raise ValueError('unsafe_or_duplicate_zip_member')
            members[e.filename] = e
        if 'review_batch_manifest.json' not in members:
            raise ValueError('review_batch_manifest_required')
        manifest_bytes = container.read('review_batch_manifest.json')
        proposal = json.loads(manifest_bytes)
        batch = proposal.get('states')
        if (proposal.get('schema') != 'exodia.state33-independent-art-review/v1'
                or not isinstance(batch, dict) or not batch or not set(batch).issubset(expected)):
            raise ValueError('invalid_review_batch_manifest')
        original_hashes = {}
        output_hashes = {}
        perceptual = {}
        # Import staging is only performed AFTER the entire uploaded set
        # passes safety, image provenance, size and anti-cloning checks.
        verified = {}
        for state, row in batch.items():
            if not isinstance(row, dict):
                raise ValueError('invalid_state_metadata:' + state)
            if (row.get('approved_by') or row.get('owner_approved') is True
                    or row.get('production_release_enabled')):
                raise ValueError('self_asserted_owner_approval_forbidden:' + state)
            if row.get('pose_key') != state:
                raise ValueError('state_pose_identity_mismatch:' + state)
            if row.get('source_kind') not in (
                    'independent_standalone_native','independently_authored_higher_resolution'):
                raise ValueError('independent_native_source_kind_required:' + state)
            if not isinstance(row.get('generator_job_id'),str) or len(row['generator_job_id'])<8:
                raise ValueError('generator_job_id_missing:' + state)
            if not isinstance(row.get('pose_evidence_description'),str) or len(row['pose_evidence_description'].strip())<30:
                raise ValueError('distinct_pose_evidence_description_missing:' + state)
            if (not SHA.fullmatch(str(row.get('generation_input_manifest_sha256','')))
                    or row.get('derived_from_composite') is not False):
                raise ValueError('independent_source_provenance_missing:' + state)
            source_name = state + '_original.png'
            output_name = state + '.png'
            for path in ('sources/' + source_name, 'images/' + output_name):
                if path not in members:
                    raise ValueError('source_or_image_missing:' + state + ':' + path)
            with container.open(members['sources/' + source_name]) as handle:
                original = handle.read(MAX_MEMBER + 1)
            with container.open(members['images/' + output_name]) as handle:
                output = handle.read(MAX_MEMBER + 1)
            if len(original) > MAX_MEMBER or len(output) > MAX_MEMBER:
                raise ValueError('image_too_large:' + state)
            orig_sha = sha(original)
            image_sha = sha(output)
            if (orig_sha != row.get('source_sha256')
                    or image_sha != row.get('image_sha256')):
                raise ValueError('sha256_mismatch:' + state)
            orig_dims = _png(original)
            out_dims = _png(output)
            if out_dims != SIZE:
                raise ValueError('output_not_native_1536x1920:' + state)
            if (orig_dims[0] < SIZE[0] or orig_dims[1] < SIZE[1]
                    or orig_dims[0] * 5 != orig_dims[1] * 4):
                raise ValueError('source_would_require_upscale:' + state)
            if row.get('source_dimensions') != list(orig_dims):
                raise ValueError('original_dimensions_unverified:' + state)
            if orig_dims == SIZE:
                if original != output or row.get('normalization') != 'identity':
                    raise ValueError('native_source_must_be_byte_identical:' + state)
            else:
                if row.get('normalization') != 'direct_lanczos_downsample':
                    raise ValueError('source_downsample_provenance_missing:' + state)
                with Image.open(BytesIO(original)) as im:
                    expected_pixels = im.convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)
                with Image.open(BytesIO(output)) as im:
                    output_pixels = im.convert('RGB')
                    if ImageChops.difference(expected_pixels, output_pixels).getbbox():
                        raise ValueError('output_not_proven_downsample:' + state)
            if ((orig_dims == SIZE and row.get('source_kind') != 'independent_standalone_native') or
                    (orig_dims != SIZE and row.get('source_kind') != 'independently_authored_higher_resolution')):
                raise ValueError('original_source_kind_and_dimensions_disagree:' + state)
            if (orig_sha in original_hashes or image_sha in output_hashes):
                raise ValueError('duplicate_original_or_image_sha:' + state)
            original_hashes[orig_sha] = state
            output_hashes[image_sha] = state
            perceptual[state] = (dhash(output), dhash(output, face=True))
            verified[state] = (row, output, original)
        # Compare with existing review imports and within the new batch.
        with LOCK:
            previous = _index(root)
            existing = {}
            for state, old in previous['states'].items():
                if state in verified:
                    continue
                path = _base(root) / 'images' / (state + '.png')
                if path.is_file() and sha(path.read_bytes()) == old.get('image_sha256'):
                    existing[state] = (old, path.read_bytes())
            for state,(row,data,original) in verified.items():
                for other,(old,old_bytes) in existing.items():
                    if (row['source_sha256'] == old.get('source_sha256')
                            or row['image_sha256'] == old.get('image_sha256')):
                        raise ValueError('clone_sha_against_existing:' + state + ':' + other)
                    a,b=perceptual[state]
                    if ((a ^ dhash(old_bytes)).bit_count() <= 3
                            and (b ^ dhash(old_bytes, face=True)).bit_count() <= 3):
                        raise ValueError('perceptual_clone_against_existing:' + state + ':' + other)
                for other,(a,b) in perceptual.items():
                    if state != other and ((a ^ perceptual[state][0]).bit_count() <= 3
                            and (b ^ perceptual[state][1]).bit_count() <= 3):
                        raise ValueError('duplicate_pose_or_color_shift:' + state + ':' + other)
            target = _base(root)
            target.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(dir=target, prefix='stage33_') as tmp:
                stage = Path(tmp)
                for state,(row,data,original) in verified.items():
                    (stage / (state + '.png')).write_bytes(data)
                    (stage / (state + '_original.png')).write_bytes(original)
                    (stage / (state + '_original.png')).write_bytes(original)
                images = target / 'images'
                sources = target / 'sources'
                images.mkdir(parents=True,exist_ok=True)
                sources.mkdir(parents=True,exist_ok=True)
                for state in verified:
                    shutil.move(str(stage / (state + '.png')),str(images / (state + '.png')))
                    shutil.move(str(stage / (state + '_original.png')),str(sources / (state + '_original.png')))
                new_rows = dict(previous['states'])
                for state,(row,_,_) in verified.items():
                    new_rows[state] = {
                      'source_filename': state + '_original.png',
                      'source_sha256': row['source_sha256'],
                      'image_sha256': row['image_sha256'],
                      'generator_job_id': row['generator_job_id'],
                      'generation_input_manifest_sha256': row['generation_input_manifest_sha256'],
                      'source_dimensions': row['source_dimensions'],
                      'normalization': row['normalization'],
                      'pose_key': state,
                      'geometry_status': 'PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT',
                      'review_status': 'unapproved',
                    }
                (target / 'review_index.json').write_text(
                    json.dumps({'schema':'exodia.state33-review-index/v1',
                                'states':new_rows},indent=2)+'\n',encoding='utf-8')
    return manifest(root)
