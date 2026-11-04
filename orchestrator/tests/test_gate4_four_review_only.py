"""Gate4 owner-accepted four-image DEVELOPMENT-only importer regression tests.

Synthetic image fixtures verify code logic, not artwork production. The
actual four approved PNG originals are stored in the owner ZIP separately.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys
import zipfile
import pytest
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'orchestrator'))
from tools.apply_gate4_four_review_only import (
    SCHEMA,NORMALIZATION,require_source_and_review,
    expected_paths,preflight,verify_locked_29
)
SHA=lambda b:hashlib.sha256(b).hexdigest()
LEDGER=ROOT/'assets'/'review'/'albedo_core5'/'gate4_four_accepted_development_review_only.json'

def test_four_original_source_approval_is_sha_specific_not_native_certified():
    ledger=json.loads(LEDGER.read_text())
    assert ledger['schema']=='exodia.gate4-owner-accepted-four-lowres-review-only/v1'
    assert ledger['owner_acceptance']=='ACCEPTED_FOR_DEVELOPMENT_NOT_PRODUCTION'
    assert ledger['production_approval_count']==0
    assert ledger['release_enabled'] is False
    assert ledger['protected_other_state_count']==29
    assert ledger['review_only_intake_archive_sha256']=='248b11c4880a3f355dbf3db6d8676e867adafd1441b1c756c91411e8dce6fe30'
    assert set(ledger['states'])=={'angered','awaiting_command','neutral','tantrum'}
    assert len({r['original_sha256'] for r in ledger['states'].values()})==4
    assert len({r['expected_resampled_png_sha256'] for r in ledger['states'].values()})==4
    assert all(r['original_canvas']==[1122,1402] and
               r['review_canvas']==[1536,1920] and
               r['native_production_certified'] is False
               for r in ledger['states'].values())

def test_preflight_requires_exactly_four_originals_and_four_non_native_review_images():
    assert expected_paths()=={'review_only_manifest.json'}|{
      f'{sub}/{state}{"_original" if sub=="sources" else ""}.png'
      for sub in ('sources','images')
      for state in ('angered','awaiting_command','neutral','tantrum')
    }
    assert NORMALIZATION=='REVIEW_ONLY_SYMMETRIC_CROP_THEN_UNIFORM_LANCZOS_UPSCALE'
    assert SCHEMA=='exodia.gate4-four-resampled-development-intake/v1'
    before=SHA((ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'review_index.json').read_bytes())
    bad=BytesIO()
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr('review_only_manifest.json','{}')
    with pytest.raises(ValueError,match='review_zip_not_exactly_four'):
        preflight(ROOT,bad.getvalue())
    assert SHA((ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'review_index.json').read_bytes())==before

def test_exact_aspect_crop_and_presentation_pixels_require_real_source():
    source=Image.new('RGB',(1122,1402),(50,40,75))
    draw=ImageDraw.Draw(source)
    draw.ellipse((180,110,920,940),fill=(200,175,215))
    draw.polygon([(220,1200),(670,880),(1090,1300)],fill=(35,91,143))
    s=BytesIO();source.save(s,format='PNG',compress_level=1)
    raw=s.getvalue()
    review=source.crop((1,1,1121,1401)).resize((1536,1920),Image.Resampling.LANCZOS)
    o=BytesIO();review.save(o,format='PNG',compress_level=1)
    assert require_source_and_review(raw,o.getvalue(),'neutral')==SHA(review.tobytes())
    # A presentation image NOT precisely derived from the recorded
    # independently generated original is rejected.
    review.putpixel((300,500),(255,0,0))
    corrupt=BytesIO();review.save(corrupt,format='PNG',compress_level=1)
    with pytest.raises(ValueError,match='presentation_pixels_not_proven'):
        require_source_and_review(raw,corrupt.getvalue(),'neutral')
    assert len(raw)>1000

def test_locked_29_and_production_registry_remain_exact():
    snapshot=verify_locked_29(ROOT)
    assert snapshot['locked_29_verified']==29
    assert len(snapshot['frozen_hashes'])>=29
    contract=snapshot['contract']
    assert contract['release_enabled'] is False
    assert contract['owner_final_production_approval'] is False
    assert contract.get('review_only_correction_completed',0) in (0,4)

def test_fastapi_review_only_route_requires_operator_confirmation():
    from fastapi.testclient import TestClient
    from app.api.server import app
    with TestClient(app) as client:
        r=client.post('/api/albedo/state33/gate4-four-review-import',
                      data=b'not-an-archive',headers={'content-type':'application/zip'})
        assert r.status_code==403
        r=client.post('/api/albedo/state33/gate4-four-review-import',
                      content=b'not-an-archive',
                      headers={'content-type':'application/zip',
                               'x-exodia-client':'exodia-dashboard'})
        assert r.status_code in (413,422)
        m=client.get('/api/albedo/state33/manifest').json()
        assert m['count']==33
        assert m['production_release_enabled'] is False
        assert m['owner_production_approved_count']==0
