"""EXODIA 28-state review batch auditor; invokes the ORIGINAL portrait pixel auditor.

The production gate is deliberately fail-closed until 33 independent native
masters have exact owner hash-specific authorization. This tool records real
pixel geometry only when images and SHA-bound search windows are present.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from PIL import Image
from audit_portrait_anchors import audit as dual_anchor_audit
from core5_native_candidate_gate import dhash

SIZE=(1536,1920)
EYE_Y=633.6
SHOULDER_Y=980.0
HEAD_W=614.4
CORE={'idle','working','explaining','monitoring','pointing'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit_28(project_root, annotations_path=None):
    root=Path(project_root)
    queue=json.loads((root.parent/'assets'/'review'/'albedo_core5'/
                      'authorized_28_state_art_queue.json').read_text())
    states={row['state_key']:row for row in queue['states']}
    assert len(states)==28 and not CORE.intersection(states)
    store=root/'app_data'/'albedo_33_review'
    idx_file=store/'review_index.json'
    idx=json.loads(idx_file.read_text())['states'] if idx_file.is_file() else {}
    annotations=(json.loads(Path(annotations_path).read_text()).get('states',{})
                 if annotations_path and Path(annotations_path).is_file() else {})
    scan_registry={'states':{}}
    scan_regions={'states':{}}
    errors={}
    proof={}
    source_hashes={}
    image_hashes={}
    visual_hashes={}
    for name,row in states.items():
        image=store/'images'/(name+'.png')
        original=store/'sources'/(name+'_original.png')
        entry=idx.get(name,{})
        reasons=[]
        output_sha=None
        source_sha=None
        if not image.is_file() or not original.is_file():
            reasons.append('distinct_native_original_or_image_missing')
        else:
            output_sha=sha(image)
            source_sha=sha(original)
            if (entry.get('image_sha256')!=output_sha or
                    entry.get('source_sha256')!=source_sha):
                reasons.append('image_or_original_sha256_mismatch')
            with Image.open(image) as im:
                if im.format!='PNG' or im.size!=SIZE:
                    reasons.append('output_not_native_1536x1920')
            with Image.open(original) as im:
                if im.format!='PNG' or im.width<SIZE[0] or
                        im.height<SIZE[1] or im.width*5!=im.height*4:
                    reasons.append('original_not_independent_high_resolution_4_to_5')
            if source_sha in source_hashes or output_sha in image_hashes:
                reasons.append('duplicate_source_or_output_sha')
            else:
                source_hashes[source_sha]=name
                image_hashes[output_sha]=name
            try:
                bits=dhash(image.read_bytes())
                for prev,(prior_bits,prior_sha) in visual_hashes.items():
                    if (bits^prior_bits).bit_count()<=3 and output_sha!=prior_sha:
                        reasons.append('near_clone_dhash_'+prev)
                        errors.setdefault(prev,[]).append('near_clone_dhash_'+name)
                visual_hashes[name]=(bits,output_sha)
            except (OSError,ValueError):
                reasons.append('perceptual_scan_failed')
        zone=annotations.get(name,{})
        if not output_sha or zone.get('source_sha256')!=output_sha:
            reasons.append('missing_sha_bound_actual_pixel_search_windows')
            zone=None
        elif not all(key in zone for key in
                     ('left_eye_search','right_eye_search',
                      'left_shoulder_search','right_shoulder_search')):
            reasons.append('incomplete_actual_pixel_search_windows')
            zone=None
        elif zone.get('review_status')!='human_anatomical_review_completed':
            reasons.append('anatomical_landmarks_not_human_reviewed')
        if not zone or not (isinstance(zone.get('head_left_x'),(int,float))
                           and isinstance(zone.get('head_right_x'),(int,float))):
            reasons.append('actual_head_boundaries_unmeasured')
        scan_registry['states'][name]={
          'path':('images/'+name+'.png') if image.is_file() else None,
          'sha256':output_sha,
          'original_source_sha256':source_sha,
          'distinct_source_verified':not reasons,
          'source_kind':'independent_standalone_native' if image.is_file() else 'pending',
          'native_canvas':[1536,1920] if image.is_file() else None
        }
        if zone:scan_regions['states'][name]=zone
        proof[name]={
            'original_filename':name+'_original.png','original_sha256':source_sha,
            'output_filename':name+'.png','output_sha256':output_sha,
            'expected_canvas':list(SIZE),'geometry_review_status':'PENDING',
            'owner_approved':False,'production_status':'pending_production_art',
            'errors':reasons}
    with tempfile.TemporaryDirectory(prefix='exodia_review_audit_') as tmp:
        reg=Path(tmp)/'registry.json';zones=Path(tmp)/'regions.json'
        reg.write_text(json.dumps(scan_registry))
        zones.write_text(json.dumps(scan_regions))
        report=dual_anchor_audit(reg,zones,store,approval_ledger_path=None)
    for name,item in proof.items():
        observed=report['states'][name]
        item['pixel_scan']=observed.get('eyes') and {
            'eyes':observed['eyes'],'shoulders':observed['shoulders'],
            'eye_y':observed.get('eye_y_px'),
            'shoulder_y':observed.get('shoulder_y_px')}
        item['production_audit_errors']=observed['errors']
        reasons=item['errors']+errors.get(name,[])
        zone=annotations.get(name,{})
        if item['pixel_scan'] is not None:
            e=item['pixel_scan']['eyes'];s=item['pixel_scan']['shoulders']
            ey=item['pixel_scan']['eye_y'];sy=item['pixel_scan']['shoulder_y']
            midx=(e[0]['x']+e[1]['x'])/2
            width=(zone.get('head_right_x',0)-zone.get('head_left_x',0)
                   if isinstance(zone.get('head_right_x'),(int,float)) and
                   isinstance(zone.get('head_left_x'),(int,float)) else None)
            numeric={
              'eye_y_px':ey,'shoulder_y_px':sy,
              'eye_delta_px':round(ey-EYE_Y,3),
              'shoulder_delta_px':round(sy-SHOULDER_Y,3),
              'center_x_px':round(midx,3),
              'center_delta_px':round(midx-768,3),
              'eye_separation_px':round(e[1]['x']-e[0]['x'],3),
              'eye_vertical_asymmetry_px':round(abs(e[1]['y']-e[0]['y']),3),
              'shoulder_vertical_asymmetry_px':round(abs(s[1]['y']-s[0]['y']),3),
              'annotated_head_width_px':width,
              'head_width_delta_px':round(width-HEAD_W,3) if width is not None else None,
              'head_width_source':'unapproved_sha_bound_human_annotations',
            }
            item['measured_geometry']=numeric
            if abs(numeric['eye_delta_px'])>2:reasons.append('eye_line_out_of_tolerance')
            if abs(numeric['shoulder_delta_px'])>2:reasons.append('shoulder_line_out_of_tolerance')
            if abs(numeric['center_delta_px'])>2:reasons.append('center_x_out_of_tolerance')
            if numeric['eye_vertical_asymmetry_px']>12:reasons.append('eye_asymmetry')
            if numeric['shoulder_vertical_asymmetry_px']>14:reasons.append('shoulder_asymmetry')
            if not 90<=numeric['eye_separation_px']<=260:reasons.append('implausible_eye_separation')
            if width is not None and abs(width-HEAD_W)>4:reasons.append('head_width_out_of_tolerance')
        item['errors']=sorted(set(reasons))
        item['status']='PROVISIONAL_NUMERIC_OK_OWNER_REQUIRED' if not reasons else 'FAIL'
    return {
       'schema':'exodia.state33-28-review-audit/v1',
       'status':'REVIEW_ONLY_PRODUCTION_GATE_LOCKED',
       'states_expected':28,'originals_sha_checked_count':len(source_hashes),
       'candidate_image_count':sum(x['output_sha256'] is not None for x in proof.values()),
       'independently_audited_numeric_count':sum(x['pixel_scan'] is not None for x in proof.values()),
       'provisional_numeric_pass_count':sum(x['status']=='PROVISIONAL_NUMERIC_OK_OWNER_REQUIRED'
                                            for x in proof.values()),
       'production_owner_approved_count':0,
       'production_release_enabled':False,
       'underlying_portrait_anchor_audit_core_pass':report['core_pass'],
       'states':proof,
       'warning':'Original pixel scanner observes local gradients, not verified anatomy; head width is a manual SHA-bound annotation. Exact owner-approved native art still required.'
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--annotations',type=Path)
    p.add_argument('--report',type=Path,required=True)
    args=p.parse_args()
    report=audit_28(args.project_root,args.annotations)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],
                      'images':report['candidate_image_count'],
                      'numeric_scans':report['independently_audited_numeric_count'],
                      'production_release_enabled':False},indent=2))
    return 0 if report['provisional_numeric_pass_count']==28 else 1

if __name__=='__main__':raise SystemExit(main())
