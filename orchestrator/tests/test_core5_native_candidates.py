"""Gate 2 native-art intake negative tests; these drawings are synthetic CI fixtures."""
from io import BytesIO
from pathlib import Path
import hashlib
import sys
import pytest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import core5_native_candidate_gate as gate

def png(i,color=(70,110,150)):
    im=Image.new('RGB',(1536,1920),color)
    d=ImageDraw.Draw(im)
    d.rectangle((100+40*i,140+45*i,730+20*i,1120-30*i),outline='white',width=30)
    d.ellipse((870-34*i,360+40*i,1200+35*i,720+45*i),fill=(30,50+i*28,180-i*22))
    d.line((40,1850-70*i,1430,300+70*i),fill='yellow',width=19+i*2)
    b=BytesIO();im.save(b,format='PNG');return b.getvalue()

def canonical():
    records={};src={};out={}
    for i,state in enumerate(gate.STATES):
        raw=png(i)
        key=state+'.png';src[key]=raw;out[key]=raw
        records[state]={
            'source_kind':'independent_standalone_native','original_filename':key,
            'output_filename':key,'original_sha256':hashlib.sha256(raw).hexdigest(),
            'output_sha256':hashlib.sha256(raw).hexdigest(),
            'source_dimensions':[1536,1920],'normalization':{'kind':'identity'},
            'generator_job_id':'test-fixture-'+state,
            'generation_input_manifest_sha256':'a'*64,
            'pose_evidence_tag':gate.REQUIRED_POSES[state],
            'image_cropped_anatomy':False,'independent_pose_human_reviewed':True,
            'geometry':{
                'pixel_measurement_independent':True,'anatomical_labels_human_verified':True,
                'eyes':[[670,633.6],[866,633.6]],
                'shoulders':[[500,980],[1036,980]],
                'head_width_px':614.4,'center_x_px':768}}
    return {'states':records},src,out

def test_even_structurally_valid_synthetic_images_never_unlock_or_get_owner_approval():
    data,src,out=canonical()
    result=gate.audit_candidate_batch(data,src,out)
    assert result['full_batch_unlocked'] is False
    assert result['owner_approved_count']==0
    assert result['structural_candidate_pass_count']==5
    assert all(s['status']=='NUMERIC_OK_NOT_OWNER_APPROVED' for s in result['states'].values())

def test_reject_missing_candidate():
    data,src,out=canonical()
    del data['states']['pointing']
    r=gate.audit_candidate_batch(data,src,out)
    assert 'missing_candidate' in r['states']['pointing']['errors']

def test_reject_distinct_label_for_same_image_and_original_sha():
    data,src,out=canonical()
    data['states']['pointing']['original_filename']='idle.png'
    data['states']['pointing']['original_sha256']=data['states']['idle']['original_sha256']
    data['states']['pointing']['output_filename']='idle.png'
    data['states']['pointing']['output_sha256']=data['states']['idle']['output_sha256']
    r=gate.audit_candidate_batch(data,src,out)
    assert 'duplicate_original_sha' in r['states']['pointing']['errors']
    assert 'duplicate_output_sha' in r['states']['idle']['errors']

def test_reject_color_shift_clone_via_perceptual_hash():
    data,src,out=canonical()
    source=Image.open(BytesIO(src['idle.png'])).convert('RGB')
    # Color-only replacement has nearly the same grayscale contours.
    im=Image.new('RGB',source.size)
    gray=source.convert('L')
    im.paste(gray)
    buf=BytesIO();im.save(buf,format='PNG')
    clone=buf.getvalue()
    src['pointing.png']=out['pointing.png']=clone
    data['states']['pointing']['original_sha256']=hashlib.sha256(clone).hexdigest()
    data['states']['pointing']['output_sha256']=hashlib.sha256(clone).hexdigest()
    r=gate.audit_candidate_batch(data,src,out)
    assert 'near_identical_pose_or_color_swap' in r['states']['pointing']['errors']

def test_reject_upscaled_concept_mislabeled_as_native():
    data,src,out=canonical()
    raw=Image.new('RGB',(1122,1402),(22,30,41));b=BytesIO();raw.save(b,format='PNG')
    src['idle.png']=b.getvalue()
    data['states']['idle']['original_sha256']=hashlib.sha256(src['idle.png']).hexdigest()
    data['states']['idle']['source_dimensions']=[1122,1402]
    data['states']['idle']['normalization']={'kind':'downsample_lanczos','scale_x':1536/1122,'scale_y':1920/1402}
    r=gate.audit_candidate_batch(data,src,out)
    assert 'source_smaller_than_native_output_upscale_forbidden' in r['states']['idle']['errors']

def test_reject_non_native_canvas_and_missing_provenance():
    data,src,out=canonical()
    im=Image.new('RGB',(1024,1280),'white');b=BytesIO();im.save(b,format='PNG')
    out['explaining.png']=b.getvalue()
    data['states']['explaining']['output_sha256']=hashlib.sha256(out['explaining.png']).hexdigest()
    del data['states']['explaining']['generator_job_id']
    r=gate.audit_candidate_batch(data,src,out)
    assert 'output_canvas_not_1536x1920' in r['states']['explaining']['errors']
    assert 'original_generation_provenance_missing' in r['states']['explaining']['errors']

def test_false_shoulders_head_size_and_invalid_approvals_fail_even_when_pixels_exist():
    data,src,out=canonical()
    data['states']['working']['geometry']['shoulders']=[[500,948],[1036,1012]]
    data['states']['working']['geometry']['head_width_px']=691
    data['states']['working']['approved_by']='owner'
    r=gate.audit_candidate_batch(data,src,out)
    errors=r['states']['working']['errors']
    assert 'shoulder_asymmetric_drift' in errors
    assert 'head_width_out_of_range' in errors
    assert 'forbidden_self_asserted_owner_approval' in errors

def test_wrong_pose_tags_and_anatomy_crop_fail():
    data,src,out=canonical()
    data['states']['pointing']['pose_evidence_tag']='monitoring'
    data['states']['pointing']['image_cropped_anatomy']=True
    r=gate.audit_candidate_batch(data,src,out)
    assert 'wrong_or_missing_distinct_pose_evidence' in r['states']['pointing']['errors']
    assert 'anatomy_crop_clearance_unverified' in r['states']['pointing']['errors']
