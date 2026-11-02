"""Core-Five review-only similarity calibration using image-SHA-bound anatomical annotations.

Never infer anatomy from desired target coordinates. Resamples 1122x1402 CONCEPT
sources to 1536x1920 review previews and measures output pixels independently.
The production auditor MUST fail because these aren't native masters.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from recover_core5_sources import LOCKED, CONCEPT_SIZE
from audit_portrait_anchors import measure_png, audit

SIZE=(1536,1920)
EYE=633.6
SHOULDER=980.0
HEAD_WIDTH=614.4

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def coordinates(data,key):
    value=data[key]
    if (not isinstance(value,list) or len(value)!=2 or
            not all(type(v) in (int,float) and math.isfinite(v) for v in value)):
        raise ValueError('invalid_landmark:'+key)
    x,y=map(float,value)
    if not (0<=x<CONCEPT_SIZE[0] and 0<=y<CONCEPT_SIZE[1]):
        raise ValueError('outside_source_canvas:'+key)
    return (x,y)

def calibrate(state,source,annotations,output):
    record={'state':state,'status':'FAIL','production_pass':False,
            'native_source':False,'owner_approved':False}
    if not source.is_file():
        record['errors']=['source_missing'];return record
    record['original_source_sha256']=sha(source)
    if record['original_source_sha256']!=LOCKED[state][1]:
        record['errors']=['original_source_sha_mismatch'];return record
    if annotations is None or annotations.get('source_sha256')!=record['original_source_sha256']:
        record['errors']=['missing_or_wrong_sha_bound_anatomical_annotations'];return record
    try:
        eyes=[coordinates(annotations,x) for x in ('left_eye_xy','right_eye_xy')]
        shoulders=[coordinates(annotations,x) for x in ('left_shoulder_xy','right_shoulder_xy')]
        face_y=sum(p[1] for p in eyes)/2
        body_y=sum(p[1] for p in shoulders)/2
        head_width=annotations['head_width_px']
        if type(head_width) not in (int,float) or not 200<=head_width<=900:
            raise ValueError('invalid_annotated_head_width')
        separation=body_y-face_y
        if separation<150:raise ValueError('invalid_anatomical_vertical_separation')
        scale=(SHOULDER-EYE)/separation
        if not .7<=scale<=1.9:raise ValueError('unsafe_scale')
        face_x=sum(p[0] for p in eyes)/2
        tx=SIZE[0]/2-scale*face_x
        ty=EYE-scale*face_y
        src=cv2.imread(str(source))
        if src is None or (src.shape[1],src.shape[0])!=CONCEPT_SIZE:
            raise ValueError('invalid_source_canvas')
        background=tuple(int(v) for v in src[0,0])
        preview=cv2.warpAffine(src,np.float32([[scale,0,tx],[0,scale,ty]]),
            SIZE,flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,
            borderValue=background)
        output.parent.mkdir(parents=True,exist_ok=True)
        if not cv2.imwrite(str(output),preview):raise ValueError('write_failed')
        regions={}
        for key,xy in zip(
            ('left_eye_search','right_eye_search','left_shoulder_search','right_shoulder_search'),
            eyes+shoulders):
            regions[key]=[round(scale*xy[0]+tx),round(scale*xy[1]+ty)]
        record.update(status='REVIEW_PREVIEW_ONLY',preview_path=output.name,
            preview_sha256=sha(output),preview_canvas=list(SIZE),
            original_canvas=list(CONCEPT_SIZE),
            scale=round(scale,6),translation_xy=[round(tx,3),round(ty,3)],
            predicted_eye_y=round(scale*face_y+ty,3),
            predicted_shoulder_y=round(scale*body_y+ty,3),
            predicted_head_width_px=round(scale*head_width,2),
            input_anatomy_review_status=annotations.get('review_status','pending'),
            output_search_regions=regions)
        try:
            pixels=measure_png(output,regions)
            record.update(pixel_scan=pixels,
                measured_eye_y=pixels['eye_y_px'],
                measured_shoulder_y=pixels['shoulder_y_px'],
                eye_delta_px=round(pixels['eye_y_px']-EYE,3),
                shoulder_delta_px=round(pixels['shoulder_y_px']-SHOULDER,3))
            record['provisional_numeric_match']=(
                abs(record['eye_delta_px'])<=2 and abs(record['shoulder_delta_px'])<=2)
        except (ValueError,KeyError) as ex:
            record['pixel_scan_error']=str(ex)
            record['provisional_numeric_match']=False
        warnings=[]
        if abs(record['predicted_head_width_px']-HEAD_WIDTH)>HEAD_WIDTH*.1:
            warnings.append('head_width_deviation_over_10_percent')
        if (tx>0 or ty>0 or scale*CONCEPT_SIZE[0]+tx<SIZE[0] or
                scale*CONCEPT_SIZE[1]+ty<SIZE[1]):
            warnings.append('border_fill_or_composition_clipping_must_be_visually_reviewed')
        warnings.append('pixel_edges_do_not_prove_real_anatomical_shoulders')
        warnings.append('resampling_does_not_create_native_source_resolution')
        if annotations.get('review_status')!='human_anatomical_review_completed':
            warnings.append('landmark_annotation_unreviewed')
        record['warnings']=warnings
    except (ValueError,KeyError) as ex:
        record['errors']=[str(ex)]
    return record

def comparison(records,output_dir,board_file):
    width,height,gap=336,420,14
    board=Image.new('RGB',(gap+5*(width+gap),620),'#101b2e')
    draw=ImageDraw.Draw(board)
    draw.text((gap,13),'EXODIA CORE FIVE: CONCEPT REVIEW ONLY',fill='#ffffff')
    draw.text((gap,34),'CYAN eye target y=633.6 | GOLD shoulder target y=980 | actual detections below',fill='#c3dee7')
    draw.text((gap,55),'Originals 1122x1402; transformed previews are NOT native masters / NOT owner-approved',fill='#ffc59c')
    for i,state in enumerate(LOCKED):
        rec=records[state];x=gap+i*(width+gap);y=110
        draw.text((x,90),state.upper(),fill='white')
        path=output_dir/(state+'_aligned_review.png')
        if path.is_file():
            with Image.open(path) as im:
                board.paste(im.convert('RGB').resize((width,height),Image.Resampling.LANCZOS),(x,y))
        else:
            draw.rectangle((x,y,x+width,y+height),fill='#2a3545')
            draw.text((x+8,y+205),'ORIGINAL/ANNOTATION UNAVAILABLE',fill='#ffc59c')
        for target,color in ((EYE,'cyan'),(SHOULDER,'#ffd65c')):
            yy=y+round(target*height/SIZE[1])
            draw.line((x,yy,x+width,yy),fill=color,width=2)
        draw.text((x,y+height+8),'SHA '+str(rec.get('preview_sha256','N/A'))[:12],fill='#dce7f0')
        draw.text((x,y+height+25),
                  'Eye '+str(rec.get('measured_eye_y','N/M'))+
                  '  delta '+str(rec.get('eye_delta_px','N/M')),fill='#dce7f0')
        draw.text((x,y+height+42),
                  'Shoulder '+str(rec.get('measured_shoulder_y','N/M'))+
                  '  delta '+str(rec.get('shoulder_delta_px','N/M')),fill='#dce7f0')
        draw.text((x,y+height+60),'PRODUCTION: FAIL',fill='#ffb198')
    board_file.parent.mkdir(parents=True,exist_ok=True)
    board.save(board_file)

def run(originals,annotations_file,out,report_path,board_path):
    annotations=json.loads(annotations_file.read_text()).get('states',{})
    recs={}
    for state,(filename,_) in LOCKED.items():
        recs[state]=calibrate(state,originals/filename,annotations.get(state),
                              out/(state+'_aligned_review.png'))
    comparison(recs,out,board_path)
    report={'schema':'exodia.core5-alignment-review/v1',
            'status':'PRODUCTION_GATE_BLOCKED','native_master_count':0,
            'owner_approved':False,'release_enabled':False,'generated_28_states':0,
            'canvas':list(SIZE),'target_eye_y':EYE,'target_shoulder_y':SHOULDER,
            'target_center_x':768,'target_head_width_px':HEAD_WIDTH,
            'states':recs}
    # Send provisional previews through the REAL fail-closed production auditor.
    # Every concept is deliberately marked non-native; no owner ledger is supplied.
    reg={'states':{}};regions={'states':{}}
    for state,r in recs.items():
        reg['states'][state]={
            'path':r.get('preview_path'),'sha256':r.get('preview_sha256'),
            'original_source_sha256':r.get('original_source_sha256'),
            'distinct_source_verified':r.get('status')=='REVIEW_PREVIEW_ONLY',
            'source_kind':'resampled_concept_preview','native_canvas':list(CONCEPT_SIZE)}
        if r.get('output_search_regions'):
            regions['states'][state]=dict(r['output_search_regions'],
                source_sha256=r['preview_sha256'],review_status='pending')
    out.mkdir(parents=True,exist_ok=True)
    rp=out/'core5_audit_input_registry.json'
    sp=out/'core5_audit_search_regions.json'
    rp.write_text(json.dumps(reg,indent=2)+'\n')
    sp.write_text(json.dumps(regions,indent=2)+'\n')
    independent=audit(rp,sp,out)
    report['production_anchor_audit']=independent
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--originals',type=Path,required=True)
    p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--board',type=Path,required=True)
    a=p.parse_args()
    report=run(a.originals,a.annotations,a.output_dir,a.report,a.board)
    print(json.dumps({'status':report['status'],
                      'states':{k:v['status'] for k,v in report['states'].items()},
                      'auditor_unlocked':report['production_anchor_audit']['full_batch_unlocked']},indent=2))
    return 0 if all(v['status']=='REVIEW_PREVIEW_ONLY' for v in report['states'].values()) else 1

if __name__=='__main__':raise SystemExit(main())
