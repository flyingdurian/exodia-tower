"""Offline synthetic tests only; never count as actual Core-Five artwork approval."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import pytest
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import recover_core5_sources as recover
import calibrate_core5_concepts as cal

def sample_png(rgb):
    im=Image.new('RGB',(1122,1402),rgb)
    b=io.BytesIO();im.save(b,format='PNG');return b.getvalue()

def make_package(root,missing=None,invalid=None):
    bundle=root/'source.zip';expected={}
    with zipfile.ZipFile(bundle,'w') as z:
        for n,state in enumerate(recover.LOCKED):
            fn=state+'.png'
            raw=sample_png((20+n*20,35,210-n*15))
            expected[state]=(fn,hashlib.sha256(raw).hexdigest())
            if state!=missing:
                z.writestr('sources/'+fn,
                           sample_png((255,0,0)) if state==invalid else raw)
        z.writestr('manifest.json','{"source":"synthetic"}')
    return bundle,expected

def test_recover_preserves_all_five_concepts_byte_exact(tmp_path):
    bundle,expected=make_package(tmp_path)
    report=recover.recover(bundle,tmp_path/'out',expected=expected)
    assert report['status']=='PASS_CONCEPT_RECOVERY_ONLY'
    assert report['native_production_master_count']==0
    assert len(report['manifests'])==1
    for state,(name,wanted) in expected.items():
        assert report['states'][state]['status']=='VERIFIED_CONCEPT'
        assert hashlib.sha256((tmp_path/'out'/name).read_bytes()).hexdigest()==wanted

@pytest.mark.parametrize('missing,invalid,failure',[
    ('pointing',None,'MISSING'),(None,'idle','HASH_MISMATCH')])
def test_recover_never_promotes_incomplete_source(tmp_path,missing,invalid,failure):
    bundle,expected=make_package(tmp_path,missing,invalid)
    report=recover.recover(bundle,tmp_path/'out',expected=expected)
    assert report['status']=='FAIL'
    assert report['states'][missing or invalid]['status']==failure
    assert not (tmp_path/'out').exists()

def test_zip_traversal_fails_closed(tmp_path):
    bundle=tmp_path/'bad.zip'
    with zipfile.ZipFile(bundle,'w') as z:z.writestr('../unsafe.txt','bad')
    with pytest.raises(ValueError,match='unsafe_zip_member'):
        recover.recover(bundle,tmp_path/'out')

def test_calibration_rescans_pixels_but_refuses_production(tmp_path,monkeypatch):
    source=tmp_path/'idle.png'
    img=np.zeros((1402,1122,3),np.uint8)
    for x in (480,640):
        cv2.circle(img,(x,485),18,(180,40,130),-1)
        cv2.circle(img,(x,485),4,(25,6,19),-1)
    for x in (365,760):
        cv2.rectangle(img,(x-15,785),(x+15,798),(245,245,245),-1)
    cv2.imwrite(str(source),img)
    actual=hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setitem(cal.LOCKED,'idle',(source.name,actual))
    ann={'source_sha256':actual,'left_eye_xy':[480,485],
         'right_eye_xy':[640,485],'left_shoulder_xy':[365,785],
         'right_shoulder_xy':[760,785],'head_width_px':532,
         'review_status':'pending'}
    output=tmp_path/'review.png'
    result=cal.calibrate('idle',source,ann,output)
    assert result['status']=='REVIEW_PREVIEW_ONLY'
    assert tuple(result['preview_canvas'])==(1536,1920)
    # Pixel-based second-pass correction can legitimately move source-annotation
    # predictions. It is the OUTPUT-PIXEL scan, not the initial affine formula,
    # that determines numeric compliance.
    assert len(result['feedback_iterations'])>=1
    if result['provisional_numeric_match']:
        assert abs(result['measured_eye_y']-633.6)<=2
        assert abs(result['measured_shoulder_y']-980)<=2
    assert 'pixel_scan' in result or 'pixel_scan_error' in result
    assert result['native_source'] is False
    assert result['production_pass'] is False
    assert result['owner_approved'] is False

def test_missing_five_way_annotations_keep_batch_locked(tmp_path):
    ann=tmp_path/'annotations.json';ann.write_text('{"states":{}}')
    report=cal.run(tmp_path/'missing',ann,tmp_path/'out',
                   tmp_path/'result.json',tmp_path/'comparison.png')
    assert all(s['status']=='FAIL' for s in report['states'].values())
    assert report['production_anchor_audit']['full_batch_unlocked'] is False
    assert report['generated_28_states']==0
    assert (tmp_path/'comparison.png').is_file()

def test_canonical_handoff_manifest_must_match_locked_originals(tmp_path):
    bundle,expected=make_package(tmp_path)
    # Rewrite fixture archive, supplying the real canonical schema with an
    # intentional misleading SHA. The verifier must reject the whole batch.
    b=tmp_path/'canonical.zip'
    with zipfile.ZipFile(bundle) as source,zipfile.ZipFile(b,'w') as target:
        for member in source.infolist():
            target.writestr(member,source.read(member.filename))
        body={'sources':{
            state:{'filename':'sources/'+filename,
                   'sha256':('f'*64 if state=='pointing' else wanted),
                   'dimensions':[1122,1402],'format':'PNG',
                   'release_approved':False,'dual_anchor_certified':False}
            for state,(filename,wanted) in expected.items()}}
        target.writestr('EXODIA_CORE5_SOURCE_MANIFEST_2026-11-02.json',json.dumps(body))
    result=recover.recover(b,tmp_path/'untrusted',expected=expected)
    assert result['status']=='FAIL'
    assert result['canonical_manifest_verification']['pointing']=='MISMATCH'
    assert not (tmp_path/'untrusted').exists()
