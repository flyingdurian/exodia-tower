"""Gate 4: verify actual committed Celebrating original, native review PNG,
pixel provenance, real workbench delivery and immutable production lockdown.
No synthetic artwork is counted as generated in this file.
"""
from pathlib import Path
from hashlib import sha256
import json
import pytest
from PIL import Image, ImageChops
from fastapi.testclient import TestClient
from app.api.server import app
from app.config import Settings
from app.companions.state33_review_assets import manifest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'orchestrator'/'app_data'/'albedo_33_review'
ORIGINAL=BASE/'sources'/'celebrating_original.png'
OUTPUT=BASE/'images'/'celebrating.png'
INDEX=BASE/'review_index.json'
EXPECTED_ORIGINAL='25affe7f46d60cdee0c016ec691a997d22963ee62f77bb8107dcaee4cbb24759'
EXPECTED_OUTPUT='cc4612e7565f6659e5349fdf20d9daa9c795fbb0e9a7fab87fd45c8e9c56c08e'
EXPECTED_PIXEL='32941e53f8f0ff96ebd3a4faed2b6441b4545b3884e8ef23fc001665b64a73ac'

@pytest.mark.skipif(not ORIGINAL.is_file() or not OUTPUT.is_file(),
                    reason='real artwork binary not yet staged in this local checkout')
def test_actual_generated_image_sha_canvas_and_pixel_transform():
    assert sha256(ORIGINAL.read_bytes()).hexdigest()==EXPECTED_ORIGINAL
    assert sha256(OUTPUT.read_bytes()).hexdigest()==EXPECTED_OUTPUT
    row=json.loads(INDEX.read_text())['states']['celebrating']
    assert row['source_sha256']==EXPECTED_ORIGINAL
    assert row['image_sha256']==EXPECTED_OUTPUT
    assert row['generator_job_id']=='a1966bad-8d42-4e75-8ae0-c5bcd3696b60'
    assert row['generation_input_manifest_sha256']==(
        '33451e662bea059050b552133c2aadf6fb22d1743a3a8a362ff864da0c1f71dd')
    assert row['normalization']['kind']=='symmetric_center_crop_then_uniform_lanczos'
    assert row['normalization']['crop_xyxy']==[8,2,1848,2302]
    with Image.open(ORIGINAL) as im:
        assert im.format=='PNG' and im.size==(1856,2304)
        native=im.convert('RGB').crop((8,2,1848,2302)).resize(
            (1536,1920),Image.Resampling.LANCZOS)
    with Image.open(OUTPUT) as im:
        assert im.format=='PNG' and im.size==(1536,1920)
        assert ImageChops.difference(native,im.convert('RGB')).getbbox() is None
    assert sha256(native.tobytes()).hexdigest()==EXPECTED_PIXEL
    assert row['geometry_status']=='PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT'
    assert row['owner_approved'] is False
    assert row['production_status']=='pending_production_art'

@pytest.mark.skipif(not OUTPUT.is_file(),
                    reason='real artwork binary not yet staged in this local checkout')
def test_real_fastapi_returns_identical_image_and_live_demo_review_status():
    m=manifest(Settings().root)
    assert m['count']==33
    queue=json.loads((ROOT/'assets'/'review'/'albedo_core5'/
                      'authorized_28_state_art_queue.json').read_text())
    assert m['additional_review_art_available_count']==queue['generated_count']
    assert m['states']['celebrating']['sha256']==EXPECTED_OUTPUT
    assert m['states']['celebrating']['art_status']=='INDEPENDENT_ART_UNAPPROVED_REVIEW'
    assert m['states']['celebrating']['owner_approved'] is False
    assert m['states']['celebrating']['native_production_certified'] is False
    assert m['states']['celebrating']['signal_overlay']=='triumphant_halo'
    assert m['states']['celebrating']['geometry_status']=='ACTUAL_PIXELS_GEOMETRY_FAIL_OWNER_UNREVIEWED'
    measured=m['states']['celebrating']['measurements']
    assert measured['eye_y']==519.427
    assert measured['shoulder_y']==869.5
    assert measured['eye_delta']==-114.173
    assert measured['shoulder_delta']==-110.5
    assert measured['head_width_px'] is None
    assert measured['numeric_provisional_pass'] is False
    assert m['states_without_review_images']==33-m['artwork_available_count']
    with TestClient(app) as client:
        r=client.get('/api/albedo/state33/review-assets/celebrating')
        assert r.status_code==200
        assert r.headers.get('content-type')=='image/png'
        assert sha256(r.content).hexdigest()==EXPECTED_OUTPUT
        surprise=client.get('/api/albedo/state33/review-assets/surprised')
        assert surprise.status_code==200
        assert sha256(surprise.content).hexdigest()==m['states']['surprised']['sha256']
        assert client.get('/api/albedo/state33/manifest').json()['production_release_enabled'] is False
    production=json.loads((ROOT/'orchestrator'/'frontend'/'companions'/'production'/'kiko'/
                           'portrait_registry.json').read_text())
    assert production['release']['enabled'] is False
    assert len([s for s in production['states'].values()
                if s['status']=='pending_production_art'])==33
    queue=json.loads((ROOT/'assets'/'review'/'albedo_core5'/
                      'authorized_28_state_art_queue.json').read_text())
    assert queue['generated_count']>=1
    assert sum(s['generation_status']=='generated_unapproved_native_candidate'
               for s in queue['states'])==queue['generated_count']

def test_all_33_real_review_portraits_are_delivered_with_correct_source_and_output_sha():
    """Verify REAL image files, not a 33/33 UI state-count proxy."""
    m=manifest(Settings().root)
    assert m['count']==33
    assert m['verified_independent_review_art_count']==33
    assert m['core_five_independent_review_art_count']==5
    assert m['additional_review_art_available_count']==28
    assert m['artwork_available_count']==33
    assert m['states_without_review_images']==0
    idx=json.loads(INDEX.read_text())
    assert len(idx['states'])==33
    original_hashes=set()
    output_hashes=set()
    with TestClient(app) as client:
        for name in m['state_order']:
            info=m['states'][name]
            entry=idx['states'][name]
            source=BASE/'sources'/(name+'_original.png')
            output=BASE/'images'/(name+'.png')
            assert source.is_file() and output.is_file(),name
            assert source.stat().st_size>500_000,name
            with Image.open(source) as im:
                assert im.format=='PNG' and im.width>=1536 and im.height>=1920,name
            with Image.open(output) as im:
                assert im.format=='PNG' and im.size==(1536,1920),name
            source_hash=sha256(source.read_bytes()).hexdigest()
            output_hash=sha256(output.read_bytes()).hexdigest()
            assert source_hash==info['source_sha256']==entry['source_sha256'],name
            assert output_hash==info['sha256']==entry['image_sha256'],name
            assert info['art_status']=='INDEPENDENT_ART_UNAPPROVED_REVIEW',name
            assert info['owner_approved'] is False,name
            assert info['native_production_certified'] is False,name
            assert entry['owner_approved'] is False,name
            assert entry['production_status']=='pending_production_art',name
            original_hashes.add(source_hash)
            output_hashes.add(output_hash)
            response=client.get(info['image_url'])
            assert response.status_code==200,name
            assert response.headers['content-type']=='image/png',name
            assert sha256(response.content).hexdigest()==output_hash,name
    assert len(original_hashes)==len(output_hashes)==33
    assert m['production_release_enabled'] is False
    assert m['owner_production_approved_count']==0
    assert m['native_core_five_certified_count']==0
