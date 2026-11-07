"""Fail-closed Gate 2 independent native Core-Five candidate acceptance.

Every returned state is always PENDING_OWNER_VISUAL. A numerical or visual
heuristic cannot stand in for original-image provenance or owner authorization.
"""
from __future__ import annotations
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageOps
try:
    from core5_geometry_gate import validate_independent_measurements
except ModuleNotFoundError:
    from orchestrator.tools.core5_geometry_gate import validate_independent_measurements

STATES=('idle','working','explaining','monitoring','pointing')
CANVAS=(1536,1920)
ALLOW_SOURCE={'independent_standalone_native','independently_authored_higher_resolution'}
REQUIRED_POSES={
    'idle':'relaxed_centered',
    'working':'interactive_workstation',
    'explaining':'explanatory_hand_gesture',
    'monitoring':'attentive_observation',
    'pointing':'extended_index_connected_wrist'
}

def digest(data):return hashlib.sha256(data).hexdigest()

def image_info(content):
    with Image.open(BytesIO(content)) as im:
        if im.format!='PNG':raise ValueError('not_png')
        size=im.size
        im.verify()
    return size

def dhash(data):
    with Image.open(BytesIO(data)) as im:
        gray=ImageOps.grayscale(im).resize((9,8),Image.Resampling.LANCZOS)
        pix=list(gray.getdata())
    bits=0
    for row in range(8):
        for col in range(8):
            bits=(bits<<1)|int(pix[row*9+col]>pix[row*9+col+1])
    return bits

def audit_candidate_batch(manifest, sources, outputs):
    """Explicit bytes dictionaries: filenames -> PNG content."""
    states=manifest.get('states',{})
    review={'schema':'exodia.core5-native-candidates/v2',
            'status':'FAIL_PENDING_OWNER_AND_ARTWORK',
            'production_release_enabled':False,
            'generated_28_states':0,
            'owner_approved_count':0,
            'full_batch_unlocked':False,'states':{}}
    original_hashes={};outputs_hashes={};perceptual={}
    for state in STATES:
        item=states.get(state) or {}
        errs=[]
        if not item:
            errs.append('missing_candidate')
            review['states'][state]={'status':'FAIL','errors':errs,
                'owner_approved':False,'production_status':'pending_production_art'}
            continue
        if item.get('approved_by') or item.get('owner_approved') is True:
            errs.append('forbidden_self_asserted_owner_approval')
        if item.get('pose_evidence_tag')!=REQUIRED_POSES[state]:
            errs.append('wrong_or_missing_distinct_pose_evidence')
        filename=item.get('original_filename','')
        outputname=item.get('output_filename','')
        source=sources.get(filename);output=outputs.get(outputname)
        if not isinstance(source,bytes):
            errs.append('source_png_missing')
        if not isinstance(output,bytes):
            errs.append('output_png_missing')
        if item.get('source_kind') not in ALLOW_SOURCE:
            errs.append('non_native_or_unverified_independence')
        if not item.get('generator_job_id') or not item.get('generation_input_manifest_sha256'):
            errs.append('original_generation_provenance_missing')
        source_dims=None;output_dims=None
        if source is not None and isinstance(source,bytes):
            original_sha=digest(source)
            if item.get('original_sha256')!=original_sha:errs.append('original_sha_mismatch')
            try:source_dims=image_info(source)
            except (OSError,ValueError):errs.append('invalid_original_png')
            if original_sha in original_hashes:
                errs.append('duplicate_original_sha')
                review['states'][original_hashes[original_sha]]['errors'].append('duplicate_original_sha')
            else:original_hashes[original_sha]=state
        else:original_sha=None
        if output is not None and isinstance(output,bytes):
            output_sha=digest(output)
            if item.get('output_sha256')!=output_sha:errs.append('output_sha_mismatch')
            try:output_dims=image_info(output)
            except (OSError,ValueError):errs.append('invalid_output_png')
            if output_sha in outputs_hashes:
                errs.append('duplicate_output_sha')
                review['states'][outputs_hashes[output_sha]]['errors'].append('duplicate_output_sha')
            else:outputs_hashes[output_sha]=state
            try:
                ph=dhash(output)
                for other,(original_ph,other_sha) in perceptual.items():
                    if (ph^original_ph).bit_count()<=3 and output_sha!=other_sha:
                        errs.append('near_identical_pose_or_color_swap')
                        review['states'][other]['errors'].append('near_identical_pose_or_color_swap')
                perceptual[state]=(ph,output_sha)
            except (OSError,ValueError):errs.append('invalid_perceptual_image')
        else:output_sha=None
        if source_dims:
            if item.get('source_dimensions')!=list(source_dims):
                errs.append('source_dimensions_manifest_mismatch')
            if source_dims[0]<CANVAS[0] or source_dims[1]<CANVAS[1]:
                errs.append('source_smaller_than_native_output_upscale_forbidden')
            if source_dims[0]*5!=source_dims[1]*4:
                errs.append('source_aspect_ratio_not_4_to_5')
        if output_dims!=CANVAS:
            errs.append('output_canvas_not_1536x1920')
        operation=item.get('normalization') or {}
        if source_dims==CANVAS:
            if operation.get('kind')!='identity' or source!=output:
                errs.append('native_source_requires_byte_identical_identity')
        elif source_dims is not None and source_dims!=CANVAS:
            if operation.get('kind')!='downsample_lanczos' or (
                operation.get('scale_x')!=CANVAS[0]/source_dims[0] or
                operation.get('scale_y')!=CANVAS[1]/source_dims[1]):
                errs.append('unsupported_or_unproven_normalization')
        geo=validate_independent_measurements(item.get('geometry',{}),source_approved=False)
        # Missing approval remains a release hold, but does not erase
        # separately measurable structural results.
        errs.extend(e for e in geo['errors'] if e!='owner_exact_hash_approval_missing')
        if item.get('image_cropped_anatomy') is not False:
            errs.append('anatomy_crop_clearance_unverified')
        if item.get('independent_pose_human_reviewed') is not True:
            errs.append('pose_distinctness_not_human_reviewed')
        review['states'][state]={
            'status':'FAIL' if errs else 'NUMERIC_OK_NOT_OWNER_APPROVED',
            'errors':sorted(set(errs)),
            'source_sha256':original_sha,'output_sha256':output_sha,
            'source_canvas':list(source_dims) if source_dims else None,
            'output_canvas':list(output_dims) if output_dims else None,
            'pose_evidence_tag':item.get('pose_evidence_tag'),
            'measured_geometry':geo,'owner_approved':False,
            'production_status':'pending_production_art'}
    # Cross-image errors may have been introduced after first state was set.
    for item in review['states'].values():
        if item['errors']:item['status']='FAIL'
    review['structural_candidate_pass_count']=sum(
        v['status']=='NUMERIC_OK_NOT_OWNER_APPROVED' for v in review['states'].values())
    return review

if __name__=='__main__':
    raise SystemExit('Use audit_candidate_batch with real independently rendered image bytes')
