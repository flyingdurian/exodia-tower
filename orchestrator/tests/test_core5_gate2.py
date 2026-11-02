"""Gate 2 review-import/API tests: no production mutation; synthetic images are NOT production samples."""
from __future__ import annotations
from io import BytesIO
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.api.server import app
from app.companions import core5_review_assets as review

def image_bytes(size, rgb):
    im=Image.new('RGB',size,rgb);b=BytesIO();im.save(b,format='PNG');return b.getvalue()

def fixture(tmp,monkeypatch):
    originals={};previews={};records={}
    for i,state in enumerate(review.STATES):
        name=state+'_fixture.png'
        orig=image_bytes((1122,1402),(30+i*26,20+i*11,60+i*8))
        candidate=image_bytes((1536,1920),(25+i*24,45+i*9,90+i*7))
        originals['originals/'+name]=orig
        previews['aligned_previews/'+state+'_aligned_review.png']=candidate
        records[state]={
          'source_filename':name,
          'original_source_sha256':hashlib.sha256(orig).hexdigest(),
          'review_preview_sha256':hashlib.sha256(candidate).hexdigest(),
          'measured_output_eye_y_px':633.6,'measured_output_shoulder_y_px':980.0,
          'eye_delta_px':0.,'shoulder_delta_px':0.,
          'estimated_head_width_px':614.4,'provisional_numeric_pass':True}
    monkeypatch.setattr(review,'_locations',lambda root:tmp/'core5_review')
    monkeypatch.setattr(review,'expected_telemetry',lambda root:{'states':records})
    archive=BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        for name,data in {**originals,**previews}.items():z.writestr(name,data)
    return archive.getvalue(),records

def test_live_review_manifest_fails_closed_until_all_five_imported(tmp_path,monkeypatch):
    archive,records=fixture(tmp_path,monkeypatch)
    with TestClient(app) as c:
        before=c.get('/api/albedo/core5/review-manifest')
        assert before.status_code==200
        assert before.json()['all_five_loaded'] is False
        assert c.get('/api/albedo/core5/review-assets/pointing').status_code==404
        assert c.get('/core5-review').status_code==200
        assert 'Core Five' in c.get('/core5-review').text

def test_auth_required_then_imports_exact_five_sha_verified_concept_reviews(tmp_path,monkeypatch):
    archive,records=fixture(tmp_path,monkeypatch)
    with TestClient(app) as c:
        assert c.post('/api/albedo/core5/review-import',content=archive,
                      headers={'content-type':'application/zip'}).status_code==403
        response=c.post('/api/albedo/core5/review-import',content=archive,
                        headers={'content-type':'application/zip',
                                 'x-exodia-client':'exodia-dashboard'})
        assert response.status_code==200,response.text
        body=response.json()
        assert body['all_five_loaded'] is True
        assert body['production_masters_loaded']==0
        assert body['generated_28_states']==0
        assert body['release_enabled'] is False
        for state in review.STATES:
            item=body['states'][state]
            assert item['production_status']=='pending_production_art'
            assert item['owner_approved'] is False
            assert item['native_master'] is False
            data=c.get('/api/albedo/core5/review-assets/'+state)
            assert data.status_code==200
            assert hashlib.sha256(data.content).hexdigest()==item['sha256']

def test_tampered_review_image_rejected_without_writing_any_images(tmp_path,monkeypatch):
    archive,records=fixture(tmp_path,monkeypatch)
    with zipfile.ZipFile(BytesIO(archive)) as z:
        changed={name:z.read(name) for name in z.namelist()}
    changed['aligned_previews/pointing_aligned_review.png']=image_bytes((1536,1920),(3,4,5))
    bad=BytesIO()
    with zipfile.ZipFile(bad,'w') as z:
        for name,data in changed.items():z.writestr(name,data)
    with pytest.raises(ValueError,match='source_sha256_mismatch_pointing'):
        review.import_review_zip(Path('/placeholder'),bad.getvalue())
    assert not (tmp_path/'core5_review').exists()

def test_duplicate_zip_entry_and_path_traversal_rejected(tmp_path,monkeypatch):
    archive,records=fixture(tmp_path,monkeypatch)
    for name in ('../escape.png','originals/idle_fixture.png'):
        altered=BytesIO()
        with zipfile.ZipFile(altered,'w') as z:
            if name.startswith('../'):
                z.writestr(name,'x')
            else:
                z.writestr(name,b'a');z.writestr(name,b'b')
        with pytest.raises(ValueError,match='unsafe_or_duplicated_zip_member'):
            review.import_review_zip(Path('/placeholder'),altered.getvalue())

def test_review_manifest_does_not_treat_corrupted_file_as_available(tmp_path,monkeypatch):
    archive,records=fixture(tmp_path,monkeypatch)
    review.import_review_zip(Path('/placeholder'),archive)
    (tmp_path/'core5_review'/'idle.png').write_bytes(b'changed')
    item=review.current_manifest(Path('/placeholder'))['states']['idle']
    assert item['availability']=='missing_review_asset'
    assert item['image_url'] is None

def test_geometry_rejects_source_ratio_that_uniform_transform_cannot_fix():
    import sys
    sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
    from core5_geometry_gate import feasibility,validate_independent_measurements
    working={
      'left_eye_xy':[497,393],'right_eye_xy':[628,382],
      'left_shoulder_xy':[384,588],'right_shoulder_xy':[719,593],
      'head_width_px':415}
    result=feasibility(working)
    assert result['requires_native_composition_reauthoring']
    assert result['shared_scale_range'] is None
    assert result['nominal_head_width_px']>690
    fake={'pixel_measurement_independent':True,'anatomical_labels_human_verified':False,
          'eyes':[(669,631),(862,636)],'shoulders':[(500,978),(1000,982)],
          'head_width_px':614.4,'center_x_px':768}
    rejected=validate_independent_measurements(fake,source_approved=True)
    assert rejected['status']=='FAIL'
    assert 'anatomical_identity_unverified' in rejected['errors']

def test_geometry_rejects_false_shoulders_clone_anatomy_and_asymmetry():
    import sys
    sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
    from core5_geometry_gate import validate_independent_measurements
    base={'pixel_measurement_independent':True,'anatomical_labels_human_verified':True,
          'eyes':[(680,633.6),(856,633.6)],'shoulders':[(505,980),(1031,980)],
          'head_width_px':614.4,'center_x_px':768}
    assert validate_independent_measurements(base,source_approved=False)['status']=='FAIL'
    fake={**base,'shoulders':[(505,960),(1031,1000)]}
    r=validate_independent_measurements(fake,source_approved=True)
    assert 'shoulder_asymmetric_drift' in r['errors']
    bad={**base,'head_width_px':691,'eyes':[(680,615),(856,652)]}
    r=validate_independent_measurements(bad,source_approved=True)
    assert 'head_width_out_of_range' in r['errors']
    assert 'eye_asymmetric_drift' in r['errors']
