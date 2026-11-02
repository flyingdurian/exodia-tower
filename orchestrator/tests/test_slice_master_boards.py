"""Checks designed to fail closed on fake production-quality cropped assets."""
import importlib.util
from pathlib import Path
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'tools'/'slice_master_boards.py'
spec=importlib.util.spec_from_file_location('slice_master_boards',SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_exact_panel_inventory():
    r=m.boxes()
    assert len(r)==31
    assert len([x for x in r if x['category']=='expression'])==20
    assert len([x for x in r if x['category']=='action'])==11
    assert len({(x['sheet'],x['source_label']) for x in r})==31

def test_bounds_and_source_validation(tmp_path):
    for name,size in m.EXPECTED_SHEETS.items():Image.new('RGB',size).save(tmp_path/name)
    d=m.inspect(tmp_path)
    assert not d['errors']
    assert d['boards_found']==3
    assert d['matched_label_candidates']==21
    assert not d['production_eligible']

def test_missing_canonical_states_not_invented(tmp_path):
    for name,size in m.EXPECTED_SHEETS.items():Image.new('RGB',size).save(tmp_path/name)
    d=m.inspect(tmp_path)
    assert len(d['missing_canonical_states'])==12
    assert 'awaiting_command' in d['missing_canonical_states']
    assert 'thinking_deeper' in d['missing_canonical_states']
    assert 'neutral' in d['missing_canonical_states']

def test_review_crops_keep_actual_pixel_dimensions(tmp_path):
    for name,size in m.EXPECTED_SHEETS.items():Image.new('RGB',size).save(tmp_path/name)
    d=m.inspect(tmp_path)
    v=m.create_review(tmp_path,tmp_path/'review',d)
    assert v['count']==31
    assert len(list((tmp_path/'review').rglob('*.png')))==31
    for row in v['slices']:
        path=tmp_path/'review'/row['file']
        assert list(Image.open(path).size)==row['crop_size_px']
        assert row['status']=='review_only_not_native'
        assert row['crop_sha256']==m.sha256(path)

def test_production_cannot_enlarge_or_fake_anchors(tmp_path):
    for name,size in m.EXPECTED_SHEETS.items():Image.new('RGB',size).save(tmp_path/name)
    d=m.inspect(tmp_path)
    errors=m.production_preflight(tmp_path,d,None,None)
    assert 'source_cells_not_native_1536x1920' in errors
    assert 'facial_landmarks_not_verified' in errors
    assert 'incomplete_33_state_mapping' in errors

def test_missing_source_fails(tmp_path):
    d=m.inspect(tmp_path)
    assert d['errors'] and not d['production_eligible']