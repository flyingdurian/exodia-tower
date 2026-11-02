"""Synthetic fixtures verify gating logic; they are NOT character art or a fluidity proof."""
import importlib.util
import json
from pathlib import Path
import shutil
import pytest
from PIL import Image,ImageDraw

TOOL=Path(__file__).resolve().parents[1]/'tools'/'validate_portrait_motion.py'
_spec=importlib.util.spec_from_file_location('validate_portrait_motion',TOOL)
gate=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

@pytest.fixture(scope='module')
def reference(tmp_path_factory):
    root=tmp_path_factory.mktemp('native_frame_gate')
    mask=Image.new('L',gate.CANVAS,0)
    ImageDraw.Draw(mask).rectangle((720,960,900,1120),fill=255)
    mask.save(root/'motion_mask.png',compress_level=1)
    records=[]
    for i in range(48):
        im=Image.new('RGB',gate.CANVAS,(27,27,57))
        d=ImageDraw.Draw(im)
        d.rectangle((755,1000,800,1045),fill=(80+i*2,85,135))
        name=f'frame_{i:03}.png'
        path=root/name
        im.save(path,compress_level=1)
        records.append({'path':name,'sha256':gate.sha256(path.read_bytes()),
                        'source_dimensions':list(gate.CANVAS),
                        'render_method':'artist_native_master'})
    anchors={
        'left_eye_corner':[540,550,24,24],
        'right_eye_corner':[955,550,24,24],
        'hair_ornament':[1150,260,24,24],
        'left_shoulder':[390,940,24,24],
        'right_shoulder':[1120,940,24,24],
    }
    manifest={'schema':gate.SCHEMA,'agent_id':'kiko','state':'working',
              'fps':24,'asset_stage':'candidate_review_only',
              'source_art_type':'independently_authored_native_frames',
              'camera':{'translate_px':[0,0],'zoom':1,'rotation_deg':0,'crop':None},
              'motion_mask':'motion_mask.png','locked_anchor_boxes':anchors,
              'frames':records}
    return root,manifest

def test_technical_pass_is_not_production_or_visual_approval(reference):
    path,manifest=reference
    result=gate.audit(manifest,path)
    assert result['technical_pass'],result['errors']
    assert not result['production_ready']
    assert result['source_authorship_verified'] is False
    assert result['fluidity_visually_verified'] is False
    assert result['frame_count']==48

def test_exact_camera_lock_is_mandatory(reference):
    path,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['camera']['translate_px']=[1,0]
    assert 'camera_transform_must_be_exactly_fixed' in gate.audit(data,path)['errors']

def test_native_size_and_storyboard_sources_fail(reference):
    path,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['source_art_type']='upscaled_storyboard'
    assert 'upscaled_or_storyboard_source_not_eligible' in gate.audit(data,path)['errors']
    data=json.loads(json.dumps(manifest))
    Image.new('RGB',(256,320)).save(path/'fake.png')
    data['frames'][1]['path']='fake.png'
    data['frames'][1]['sha256']=gate.sha256((path/'fake.png').read_bytes())
    assert any('invalid_native_png' in e for e in gate.audit(data,path)['errors'])

def test_one_changed_static_anchor_pixel_fails(reference):
    root,manifest=reference
    with Image.open(root/'frame_001.png') as src:im=src.copy()
    im.putpixel((545,555),(255,0,0))
    target=root/'bad_anchor.png'
    im.save(target)
    data=json.loads(json.dumps(manifest))
    data['frames'][1]['path']='bad_anchor.png'
    data['frames'][1]['sha256']=gate.sha256(target.read_bytes())
    result=gate.audit(data,root)
    assert any('modified_static_or_anchor_pixels' in e for e in result['errors'])
    assert any('locked_anchor_modified_left_eye_corner' in e for e in result['errors'])
    target.unlink()

def test_repeated_frames_cannot_masquerade_as_smooth(reference):
    root,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['frames'][1]=data['frames'][0].copy()
    result=gate.audit(data,root)
    assert 'duplicate_frame_bytes' in result['errors']
    assert any('duplicate_or_frozen_neighbor' in e for e in result['errors'])

def test_anchored_masks_and_safe_border(reference):
    root,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['locked_anchor_boxes']['hair_ornament']=[720,960,24,24]
    assert any('locked anchor cannot overlap' in e for e in gate.audit(data,root)['errors'])
    data=json.loads(json.dumps(manifest))
    data['motion_mask']='frame_000.png'
    assert any('invalid_motion_mask_or_anchors' in e for e in gate.audit(data,root)['errors'])

def test_minimum_frames_duration_and_fps(reference):
    root,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['frames']=data['frames'][:4]
    assert 'minimum_48_independent_frames' in gate.audit(data,root)['errors']
    data=json.loads(json.dumps(manifest))
    data['fps']=30
    assert 'loop_duration_too_short' in gate.audit(data,root)['errors']

def test_fleet_identity_and_legacy_paths(reference):
    root,manifest=reference
    data=json.loads(json.dumps(manifest))
    data['agent_id']='nova'
    assert gate.audit(data,root)['technical_pass']
    data=json.loads(json.dumps(manifest))
    data['frames'][0]['path']='old_STORYBOARD_ONLY.png'
    assert 'frame_0_legacy_storyboard_or_reframe' in gate.audit(data,root)['errors']
    assert not gate.relative_asset_path('../bad.png')
    assert not gate.relative_asset_path('/abs.png')
