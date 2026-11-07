"""EXODIA fail-closed dual-anchor pixel audit. CV scans actual image pixels near
image-hash-bound proposed search windows. Hints are not landmark certification.
"""
import argparse,hashlib,json,re
from pathlib import Path
import cv2,numpy as np
SIZE=(1536,1920)
CORE=('idle','working','explaining','monitoring','pointing')
EYE_Y=633.6
SHOULDER_Y=980.0
TOL_EYE=2.0
TOL_SHOULDER=2.0
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def iris(hsv,pt):
    cx,cy=map(int,pt);h,w=hsv.shape[:2]
    if not(38<=cx<w-38 and 30<=cy<h-30):raise ValueError('eye_search_outside_canvas')
    yy,xx=np.mgrid[cy-24:cy+25,cx-33:cx+34]
    c=hsv[cy-24:cy+25,cx-33:cx+34].astype(np.float32)
    H,S,V=c[:,:,0],c[:,:,1],c[:,:,2]
    mask=np.exp(-.5*((xx-cx)/21)**2-.5*((yy-cy)/15)**2)*(H>=122)*(H<=169)*(S/255)*((255-V)/255)
    strength=float(mask.sum())
    if strength<75:raise ValueError('iris_pixel_evidence_low')
    return dict(x=float((xx*mask).sum()/strength),y=float((yy*mask).sum()/strength),signal=round(strength,2))
def shoulder(gray,pt):
    cx,cy=map(int,pt);h,w=gray.shape[:2]
    if not(20<=cx<w-20 and 26<=cy<h-26):raise ValueError('shoulder_search_outside_canvas')
    patch=gray[cy-22:cy+23,cx-18:cx+19]
    gradient=np.abs(cv2.Sobel(patch,cv2.CV_32F,0,1,ksize=3)).mean(axis=1)
    gradient=np.convolve(gradient,[.2,.6,.2],mode='same')
    index=int(np.argmax(gradient))
    if float(gradient[index])<28:raise ValueError('shoulder_edge_evidence_low')
    return dict(x=float(cx),y=float(cy-22+index),signal=round(float(gradient[index]),2))
def measure_png(path,regions):
    img=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if img is None:raise ValueError('missing_or_invalid_image')
    if (img.shape[1],img.shape[0])!=SIZE:raise ValueError('incorrect_canvas')
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV);gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    eyes=[iris(hsv,regions[k]) for k in ('left_eye_search','right_eye_search')]
    shoulders=[shoulder(gray,regions[k]) for k in ('left_shoulder_search','right_shoulder_search')]
    return dict(eye_y_px=round(sum(a['y'] for a in eyes)/2,3),
                shoulder_y_px=round(sum(a['y'] for a in shoulders)/2,3),
                eyes=eyes,shoulders=shoulders)
def audit(registry_path,regions_path,asset_root=None,approval_ledger_path=None):
    reg=json.loads(Path(registry_path).read_text())
    zones=json.loads(Path(regions_path).read_text()).get('states',{})
    # Search region owner_confirmed is not production authorization.
    # Human-reviewed SHA-bound approval is an independent input.
    approvals=(json.loads(Path(approval_ledger_path).read_text()).get('states',{})
               if approval_ledger_path else {})
    root=Path(asset_root or Path(registry_path).parent).resolve()
    results={};originals={}
    for name,e in reg['states'].items():
        errors=[];out=dict(state=name,status='FAIL')
        path=e.get('path');searched=zones.get(name)
        if not path:errors.append('pending_production_art')
        else:
            file=(root/path).resolve()
            if not file.is_relative_to(root):errors.append('unsafe_path')
            elif not file.is_file():errors.append('file_missing')
            else:
                actual_sha=sha(file);out['sha256']=actual_sha
                if e.get('sha256')!=actual_sha:errors.append('image_sha256_mismatch')
                if not searched or searched.get('source_sha256')!=actual_sha:
                    errors.append('image_bound_search_regions_missing')
                else:
                    try:
                        m=measure_png(file,searched);out.update(m)
                        out['eye_delta_px']=round(m['eye_y_px']-EYE_Y,3)
                        out['shoulder_delta_px']=round(m['shoulder_y_px']-SHOULDER_Y,3)
                        if abs(m['eye_y_px']-EYE_Y)>TOL_EYE:errors.append('eye_anchor_out_of_range')
                        if abs(m['shoulder_y_px']-SHOULDER_Y)>TOL_SHOULDER:errors.append('shoulder_anchor_out_of_range')
                    except (ValueError,KeyError) as ex:errors.append('pixel_detection_'+str(ex))
        if not searched or searched.get('review_status')!='owner_confirmed':
            errors.append('search_regions_not_owner_reviewed')
        if e.get('distinct_source_verified') is not True:
            errors.append('distinct_master_not_verified')
        original=e.get('original_source_sha256')
        if not isinstance(original,str) or not re.fullmatch(r'[a-f0-9]{64}',original):
            errors.append('original_source_sha256_missing_or_invalid')
        if (e.get('source_kind')!='independent_standalone_native'
                or e.get('native_canvas')!=list(SIZE)):
            errors.append('native_standalone_source_not_verified')
        else:
            # Native source status now REQUIRES enhanced geometry evidence,
            # independently of two convenient midline PASS numbers.
            from core5_geometry_gate import validate_independent_measurements
            head_zone=searched.get('head_edges_px') if searched else None
            head_ok=(isinstance(head_zone,list) and len(head_zone)==2 and
                     all(type(v) in (int,float) for v in head_zone))
            if not head_ok or 'eyes' not in out or 'shoulders' not in out:
                errors.append('native_head_and_independent_landmarks_missing')
            else:
                measured={
                    'pixel_measurement_independent':True,
                    'anatomical_labels_human_verified':(
                        searched.get('anatomy_review_status')=='owner_confirmed'),
                    'eyes':[[v['x'],v['y']] for v in out['eyes']],
                    'shoulders':[[v['x'],v['y']] for v in out['shoulders']],
                    'head_width_px':head_zone[1]-head_zone[0],
                    'center_x_px':(out['eyes'][0]['x']+out['eyes'][1]['x'])/2}
                g=validate_independent_measurements(measured,source_approved=True)
                out['enhanced_native_geometry']=g
                if g['status']!='PASS':
                    errors.extend('native_geometry_'+x for x in g['errors'])
                if (not searched.get('head_edges_image_sha256') or
                     searched['head_edges_image_sha256']!=out.get('sha256')):
                    errors.append('head_edges_not_bound_to_image_sha256')
            if not e.get('independent_generation_job_id'):
                errors.append('native_generation_job_provenance_missing')
        approval=approvals.get(name) or {}
        expected_sha=out.get('sha256')
        if (not expected_sha or approval.get('image_sha256')!=expected_sha
                or approval.get('original_source_sha256')!=original
                or not approval.get('approval_reference')
                or approval.get('anatomy_pose_review')!='completed'
                or approval.get('eye_landmarks_reviewed') is not True
                or approval.get('shoulder_landmarks_reviewed') is not True
                or approval.get('distinct_state_reviewed') is not True):
            errors.append('owner_hash_bound_approval_missing')
        if original:
            if original in originals:
                errors.append('cloned_original_source')
                results[originals[original]]['errors'].append('cloned_original_source')
            else:originals[original]=name
        out['errors']=errors;results[name]=out
    for e in results.values():e['status']='PASS' if not e['errors'] else 'FAIL'
    core={k:results[k]['status'] if k in results else 'FAIL' for k in CORE}
    passed=all(x=='PASS' for x in core.values())
    return dict(schema='exodia.anchor-audit/v1',
      anchor_targets={'canvas':list(SIZE),'eye_y':EYE_Y,'eye_tolerance_px':TOL_EYE,
                      'shoulder_y':SHOULDER_Y,'shoulder_tolerance_px':TOL_SHOULDER},
      core_pass=passed,full_batch_unlocked=passed,core_states=core,
      approval_ledger_supplied=approval_ledger_path is not None,
      checked_count=len(results),passed_count=sum(v['status']=='PASS' for v in results.values()),
      states=results,warning='Pixel gradients cannot prove anatomical shoulder identity; genuine owner-reviewed SHA-bound ledger and independent visual inspection mandatory. Metadata alone is not proof.')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--search-regions',type=Path,required=True)
    p.add_argument('--asset-root',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--owner-approval-ledger',type=Path,help='Externally reviewed hash-bound five-state sign-off; omit to remain fail closed')
    a=p.parse_args();report=audit(a.registry,a.search_regions,a.asset_root,a.owner_approval_ledger)
    print(json.dumps(report,indent=2))
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['core_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
