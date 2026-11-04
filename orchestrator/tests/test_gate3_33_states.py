"""Gate 3: 33-state navigator, native review intake and release lockdown.

All images in these tests are synthetic fixtures; no synthetic pixels can
become actual Albedo production or owner-approved art.
"""
from __future__ import annotations
from io import BytesIO
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.api.server import app
from app.companions import state33_review_assets as review
ROOT=Path(__file__).resolve().parents[1]

def make_image(state, *, size=(1536,1920), color=(70,85,110)):
    im = Image.new('RGB',size,color)
    d = ImageDraw.Draw(im)
    if state=='happy':
        d.ellipse((120,200,540,880),fill=(200,155,55))
        d.line((110,100,900,1750),fill=(25,240,90),width=54)
    elif state=='neutral':
        d.polygon([(110,800),(920,240),(1200,1720)],fill=(30,225,130))
        d.ellipse((300,80,1000,830),outline=(245,170,25),width=65)
    else:
        d.rectangle((245,140,1100,1615),outline=(245,200,40),width=83)
    b=BytesIO();im.save(b,format='PNG');return b.getvalue()

def make_batch(states=('neutral',), *, source_images=None, row_overrides=None):
    source_images = source_images or {}
    rows={}
    b=BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        for state in states:
            raw=source_images.get(state) or make_image(state)
            rows[state]={
              'source_sha256':hashlib.sha256(raw).hexdigest(),
              'image_sha256':hashlib.sha256(raw).hexdigest(),
              'source_dimensions':[1536,1920],
              'normalization':'identity','source_kind':'independent_standalone_native',
              'generator_job_id':'test-original-job-'+state,
              'generation_input_manifest_sha256':hashlib.sha256(state.encode()).hexdigest(),
              'pose_key':state,
              'pose_evidence_description':'State-specific original body pose with isolated rendering for '+state,
              'derived_from_composite':False,
            }
            if row_overrides and state in row_overrides:rows[state].update(row_overrides[state])
            z.writestr('sources/'+state+'_original.png',raw)
            z.writestr('images/'+state+'.png',raw)
        z.writestr('review_batch_manifest.json',json.dumps({
            'schema':'exodia.state33-independent-art-review/v1','states':rows}))
    return b.getvalue()

def test_full_33_state_manifest_is_real_registry_and_has_no_approved_art(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    with TestClient(app) as c:
        response=c.get('/api/albedo/state33/manifest')
        assert response.status_code==200,response.text
        body=response.json()
        assert body['schema']=='exodia.state33-review-workbench/v1'
        assert body['count']==33
        assert body['core_five_count']==5
        assert body['additional_state_count']==28
        assert len(body['state_order'])==33
        assert body['state_order'][:5]==['idle','working','explaining','monitoring','pointing']
        assert all(body['states'][name]['tentative_reference_approved'] for name in body['state_order'][:5])
        assert set(body['states'])==set(body['state_order'])
        # This test deliberately isolates the review-file backing store;
        # the GitHub checkout may have zero or five legacy Core-Five
        # concept PNGs installed. In either case no independent images exist.
        assert 28 <= body['states_without_review_images'] <= 33
        assert body['additional_review_art_available_count']==0
        assert body['core_native_review_art_available_count']==0
        assert body['production_release_enabled'] is False
        assert body['owner_production_approved_count']==0
        assert body['native_core_five_certified_count']==0
        assert body['tentative_reference_signoff_count']==5
        assert all(s['production_status']=='pending_production_art' for s in body['states'].values())
        assert all(s['owner_approved'] is False for s in body['states'].values())
        assert c.get('/test-workbench').status_code==200
        assert 'test_workbench_33.mjs' in c.get('/test-workbench').text
        assert c.get('/state33-review').status_code==200
        assert c.get('/api/albedo/state33/review-assets/happy').status_code==404

def test_import_requires_operator_header_and_accepts_review_only_image(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    payload=make_batch()
    with TestClient(app) as c:
        assert c.post('/api/albedo/state33/review-import',content=payload,
             headers={'content-type':'application/zip'}).status_code==403
        r=c.post('/api/albedo/state33/review-import',content=payload,
             headers={'content-type':'application/zip','x-exodia-client':'exodia-dashboard'})
        assert r.status_code==200,r.text
        obj=r.json()
        assert obj['additional_review_art_available_count']==1
        assert obj['artwork_available_count']>=1
        entry=obj['states']['neutral']
        assert entry['art_status']=='INDEPENDENT_ART_UNAPPROVED_REVIEW'
        assert entry['geometry_status']=='PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT'
        assert entry['owner_approved'] is False
        assert entry['production_status']=='pending_production_art'
        img=c.get(entry['image_url'])
        assert img.status_code==200
        assert hashlib.sha256(img.content).hexdigest()==entry['sha256']
        assert obj['production_release_enabled'] is False

def test_import_rejects_cloned_image_same_pose_different_state(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    identical=make_image('neutral')
    with pytest.raises(ValueError,match='duplicate_original_or_image_sha'):
        review.import_art(ROOT,make_batch(
          ('neutral','happy'),source_images={'neutral':identical,'happy':identical}))

def test_import_rejects_color_swap_same_structure(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    image=make_image('neutral')
    with Image.open(BytesIO(image)) as im:
        gray=im.convert('L').convert('RGB')
        swapped=BytesIO();gray.save(swapped,format='PNG')
    with pytest.raises(ValueError,match='duplicate_pose_or_color_shift'):
        review.import_art(ROOT,make_batch(
            ('neutral','happy'),source_images={'neutral':image,'happy':swapped.getvalue()}))

def test_import_rejects_upscaled_concept_even_when_dimensions_lie(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    raw=make_image('neutral',size=(1122,1402))
    data=make_batch(source_images={'neutral':raw},row_overrides={
        'neutral':{'source_dimensions':[1122,1402]}})
    with pytest.raises(ValueError,match='output_not_native_1536x1920'):
        review.import_art(ROOT,data)

@pytest.mark.parametrize('extra,reason',[
    ({'approved_by':'owner'},'self_asserted_owner_approval_forbidden'),
    ({'derived_from_composite':True},'independent_source_provenance_missing'),
    ({'source_kind':'upscaled_concept'},'independent_native_source_kind_required'),
    ({'pose_key':'happy'},'state_pose_identity_mismatch'),
    ({'generator_job_id':''},'generator_job_id_missing'),
])
def test_invalid_provenance_or_owner_claim_rejected(tmp_path,monkeypatch,extra,reason):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    with pytest.raises(ValueError,match=reason):
        review.import_art(ROOT,make_batch(row_overrides={'neutral':extra}))

def test_unsafe_zip_and_failed_image_shas_do_not_write_review_index(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    archive=BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('../state.png',b'malicious')
        z.writestr('review_batch_manifest.json','{}')
    with pytest.raises(ValueError,match='unsafe_or_duplicate_zip_member'):
        review.import_art(ROOT,archive.getvalue())
    assert not (tmp_path/'review'/'review_index.json').exists()
    corrupted=make_batch(row_overrides={'neutral':{'image_sha256':'f'*64}})
    with pytest.raises(ValueError,match='sha256_mismatch'):
        review.import_art(ROOT,corrupted)
    assert not (tmp_path/'review'/'review_index.json').exists()

def test_art_approval_remains_locked_even_if_review_image_exists(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'_base',lambda root:tmp_path/'review')
    review.import_art(ROOT,make_batch())
    m=review.manifest(ROOT)
    assert m['owner_production_approved_count']==0
    assert m['native_core_five_certified_count']==0
    assert all(x['owner_approved'] is False for x in m['states'].values())
    assert m['states']['neutral']['image_url'] is not None
    assert m['states']['happy']['image_url'] is None
