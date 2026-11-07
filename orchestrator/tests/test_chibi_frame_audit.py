"""Chibi native sprite staging must never transform a composite into approved art."""
import json
from pathlib import Path
import pytest
from tools.audit_chibi_frames import audit

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'frontend'/'albedo_chibi_manifest.json'

def test_pending_40_chibi_frames_remain_production_locked():
    report=audit(MANIFEST)
    assert report['frame_count']==40
    assert report['byte_verified']==0
    assert report['native_owner_certified'] is False
    assert report['status']=='PENDING_INDEPENDENT_ART_AND_OWNER_APPROVAL'

def test_partial_source_and_unapproved_status_fail_closed(tmp_path):
    m=json.loads(MANIFEST.read_text())
    m['frames']['walk_ne_02']['src']='/assets/albedo_chibi/frames/walk_ne_02.png'
    doc=tmp_path/'bad.json';doc.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='Partial art promotion'):audit(doc)
    m['asset_status']='approved_40_frame_set'
    doc.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='source path|Approval SHA|source SHA'):audit(doc)

def test_missing_direction_frame_detected(tmp_path):
    m=json.loads(MANIFEST.read_text());del m['frames']['walk_sw_03']
    doc=tmp_path/'bad.json';doc.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='40'):audit(doc)
