"""Albedo camera-lock tests; source images are synthetic storyboard fixtures."""
import importlib.util
from pathlib import Path
from PIL import Image
import pytest

MODULE=Path(__file__).parents[1]/'tools'/'albedo_camera_lock.py'
spec=importlib.util.spec_from_file_location('albedo_camera_lock',MODULE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture(source):
    source.mkdir(parents=True,exist_ok=True)
    for state in m.STATES:
        for i in range(1,5):
            Image.new('RGB',(200,240),(i*12,5,50)).save(
                source/f'{state}_storyboard_{i:02d}.png')

def test_fixed_storyboard_canvas_and_status(tmp_path):
    src=tmp_path/'src';fixture(src)
    result=m.build(src,tmp_path/'out')
    assert result['status']=='review_only_not_hd_motion'
    assert result['camera_translation_px']==[0,0]
    assert result['production_canvas_px']==[1536,1920]
    for state in m.STATES:
        entry=result['loops'][state]
        assert entry['approved_as_full_hd'] is False
        assert entry['display_order']==[1,2,3,4,3,2]
        with Image.open(tmp_path/'out'/entry['gif']) as im:
            assert im.size==(256,320) and im.n_frames>=4

def test_source_offsets_register_same_crown_anchor():
    for offsets in m.OFFSETS.values():
        assert offsets[0]==(0,0)
        assert len({(37-dx)+(120+dx) for dx,_ in offsets})==1
        assert len({(38-dy)+(23+dy) for _,dy in offsets})==1

def test_unexpected_source_size_fails_closed(tmp_path):
    src=tmp_path/'src';fixture(src)
    Image.new('RGB',(1536,1920)).save(src/'idle_storyboard_01.png')
    with pytest.raises(ValueError,match='Unexpected storyboard'):
        m.render_frames(src,'idle')

def test_native_registration_and_duplicates(tmp_path):
    files=[]
    for i in range(4):
        p=tmp_path/f'{i}.png'
        Image.new('RGB',(1536,1920),(i*50,10,100)).save(p); files.append(p)
    positions=[{'eye_x':.5,'eye_y':.33,'head_width':.4} for _ in files]
    assert m.validate_native(files,positions)==[]
    assert 'duplicate_frames' in m.validate_native([files[0]]*4,positions)
    positions[1]['eye_x']=.52
    assert 'camera_drift_eye_x' in m.validate_native(files,positions)

def test_non_native_master_cannot_pass(tmp_path):
    files=[]
    for i in range(4):
        p=tmp_path/f'bad{i}.png'
        Image.new('RGB',(200,250),(i*40,0,10)).save(p);files.append(p)
    positions=[{'eye_x':.5,'eye_y':.33,'head_width':.4} for _ in files]
    assert sum('not_native_4x5' in e for e in m.validate_native(files,positions))==4

def test_fixed_background_across_preview_frames(tmp_path):
    src=tmp_path/'src';fixture(src)
    for state in m.STATES:
        frames=m.render_frames(src,state)
        assert len({img.getpixel((0,0)) for img in frames})==1
        assert len({img.getpixel((255,319)) for img in frames})==1
