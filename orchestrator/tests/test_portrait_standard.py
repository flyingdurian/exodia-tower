import importlib.util
from pathlib import Path
import pytest
pytest.importorskip("PIL", reason="optional portrait QA dependency")
from PIL import Image

p=Path(__file__).resolve().parents[1]/'tools'/'portrait_standard.py'
spec=importlib.util.spec_from_file_location('portrait_standard',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def meta(**changes):
    v={'standard':m.STANDARD_ID,'kind':'emotion','character_id':'kiko',
       'status':'candidate_pending_review','registration':{'eye_x':0.5,'eye_y':0.33,'head_width':0.4}}
    v.update(changes)
    return v


def test_master_accepts_only_canonical_size(tmp_path):
    good=tmp_path/'good.png'; Image.new('RGB',(1536,1920),'#353464').save(good)
    bad=tmp_path/'bad.png'; Image.new('RGB',(1312,1199),'#353464').save(bad)
    assert not m.validate_master(good,meta())['errors']
    assert any('Expected 1536x1920' in x for x in m.validate_master(bad,meta())['errors'])


def test_registration_rejects_scale_or_eye_line_drift(tmp_path):
    image=tmp_path/'portrait.png';Image.new('RGB',(1536,1920)).save(image)
    for key,value in [('eye_x',.65),('eye_y',.52),('head_width',.65)]:
        anchors=meta()['registration'].copy();anchors[key]=value
        assert m.validate_master(image,meta(registration=anchors))['errors']


def test_legacy_reframe_preserves_original_and_ratio(tmp_path):
    source=tmp_path/'landscape.png';Image.new('RGB',(1536,1024),(180,40,80)).save(source)
    original=source.read_bytes()
    out=tmp_path/'review.png'
    result=m.reframe_legacy_review(source,out)
    assert Image.open(out).size == (1536,1920)
    assert result['status'] == 'legacy_review_only_must_regenerate_for_production'
    assert result['portrait_content_box'][2:]==[1474,983]
    assert original==source.read_bytes()
    assert result['native_scale_consistent'] is False


def test_owner_approval_cannot_be_claimed_without_human_review(tmp_path):
    image=tmp_path/'portrait.png';Image.new('RGB',(1536,1920)).save(image)
    result=m.validate_master(image,meta(status='owner_approved'))
    assert any('owner approval' in x for x in result['errors'])


def test_loop_requires_independent_matching_frames(tmp_path):
    imgs=[]
    for i in range(4):
        path=tmp_path/f'{i}.png';Image.new('RGB',(1536,1920),(i*5,0,0)).save(path);imgs.append(path)
    anchors=[meta()['registration'] for _ in imgs]
    assert not m.validate_loop(imgs,anchors)['errors']
    assert any('Duplicate frames' in x for x in m.validate_loop([imgs[0]]*4,anchors)['errors'])
    drifting=[x.copy() for x in anchors];drifting[2]['eye_y']=.36
    assert any('jitter' in x for x in m.validate_loop(imgs,drifting)['errors'])


def test_non_four_to_five_never_passes_even_if_metadata_says_approved(tmp_path):
    image=tmp_path/'wrong.png';Image.new('RGB',(1200,1500)).save(image)
    result=m.validate_master(image,meta(status='owner_approved',human_visual_review='completed'))
    assert result['errors'] and not result['production_ready']