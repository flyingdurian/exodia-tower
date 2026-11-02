"""Synthetic-only pixel detector tests; never production owner approval."""
import sys,json,hashlib
from pathlib import Path
import cv2,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_portrait_anchors import measure_png,audit,CORE
def draw(p,y=634):
    im=np.zeros((1920,1536,3),np.uint8)
    for x in (658,878):
        cv2.circle(im,(x,y),21,(180,40,130),-1)
        cv2.circle(im,(x,y),5,(25,6,19),-1)
    for x in (495,1050):
        cv2.rectangle(im,(x-18,980),(x+18,995),(240,240,240),-1)
    cv2.imwrite(str(p),im)
    return hashlib.sha256(p.read_bytes()).hexdigest()
def hints(sha,y=634,review='owner_confirmed'):
    return dict(source_sha256=sha,left_eye_search=[658,y],right_eye_search=[878,y],
        left_shoulder_search=[495,980],right_shoulder_search=[1050,980],review_status=review)
def test_real_pixels_can_match_exact_targets(tmp_path):
    p=tmp_path/'im.png';draw(p)
    m=measure_png(p,hints('none'))
    assert abs(m['eye_y_px']-633.6)<=2
    assert abs(m['shoulder_y_px']-980)<=2
def test_wrong_canvas_rejected(tmp_path):
    p=tmp_path/'im.png';cv2.imwrite(str(p),np.zeros((300,300,3),np.uint8))
    try:measure_png(p,hints('none'))
    except ValueError as e:assert 'incorrect_canvas' in str(e)
    else:raise AssertionError('accepted incorrect size')
def test_core_gate_rejects_misaligned_gold(tmp_path):
    data={};regions={}
    for key in CORE:
        p=tmp_path/(key+'.png');sha=draw(p,674 if key=='working' else 634)
        data[key]=dict(path=p.name,sha256=sha,distinct_source_verified=True)
        regions[key]=hints(sha,674 if key=='working' else 634)
    reg=tmp_path/'reg.json';h=tmp_path/'h.json'
    reg.write_text(json.dumps({'states':data}))
    h.write_text(json.dumps({'states':regions}))
    report=audit(reg,h)
    assert report['full_batch_unlocked'] is False
    assert 'eye_anchor_out_of_range' in report['states']['working']['errors']
def test_unreviewed_sources_never_unlock(tmp_path):
    p=tmp_path/'idle.png';sha=draw(p)
    r=tmp_path/'reg.json';h=tmp_path/'h.json'
    r.write_text(json.dumps({'states':{'idle':dict(path=p.name,sha256=sha,distinct_source_verified=False)}}))
    h.write_text(json.dumps({'states':{'idle':hints(sha,review='pending')}}))
    report=audit(r,h)
    assert report['full_batch_unlocked'] is False
    assert 'search_regions_not_owner_reviewed' in report['states']['idle']['errors']
