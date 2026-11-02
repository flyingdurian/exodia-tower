"""Synthetic checks for EXODIA review-only normalization, NOT artistic QA."""
import importlib.util
from pathlib import Path
import pytest
from PIL import Image
MOD=Path(__file__).resolve().parents[1]/'tools'/'portrait_standard.py'
spec=importlib.util.spec_from_file_location('portrait_standard',MOD)
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

@pytest.fixture
def sample(tmp_path):
    p=tmp_path/'source.png'
    Image.new('RGB',(1122,1402),'#252044').save(p)
    points={'method':'manual_visual_estimate',
            'eye_midpoint_source_px':[554,377],
            'head_bounds_x_source_px':[294,814]}
    return p,points

def test_normalizes_with_preserved_source_and_review_gate(sample,tmp_path):
    p,points=sample
    before=gate.fingerprint(p)
    out=tmp_path/'out.png'
    result=gate.normalize_generated(p,out,points,tmp_path/'meta.json')
    assert result['status']=='PASSED'
    assert Image.open(out).size==(1536,1920)
    assert abs(result['mapped_eye_line_px']-633.6)<1
    assert abs(result['mapped_head_width_px']-614.4)<1
    assert result['registration_sha256']
    assert gate.fingerprint(p)==before
    assert not result['registration_verified_from_image']
    assert not result['source_native_resolution']
    assert not result['sequence_generation_authorized']
    assert result['technical_check']['production_ready'] is False

def test_rejects_three_to_four_coercion(sample,tmp_path):
    p,points=sample
    Image.new('RGB',(1122,1496),'#272147').save(p)
    with pytest.raises(ValueError,match='aspect deviates'):
        gate.normalize_generated(p,tmp_path/'out.png',points,tmp_path/'meta.json')

def test_rejects_crop_or_false_source_coordinates(sample,tmp_path):
    p,points=sample
    points['eye_midpoint_source_px']=[554,10]
    with pytest.raises(ValueError,match='without cropping'):
        gate.normalize_generated(p,tmp_path/'out.png',points,tmp_path/'meta.json')

def test_provenance_cannot_be_marked_as_auto_verified(sample,tmp_path):
    p,points=sample
    points['method']='automatically_verified'
    with pytest.raises(ValueError,match='provenance'):
        gate.normalize_generated(p,tmp_path/'out.png',points,tmp_path/'meta.json')
