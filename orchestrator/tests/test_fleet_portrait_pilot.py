"""Riven A0 preparation must not certify poster crops, upscales or clones."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from PIL import Image
from tools.fleet_portrait_pilot import canonical, make_riven_manifest, audit_pilot, PILOT_KEYS, ROOT


def test_riven_pilot_preserves_locked_roster_states_and_actual_reference():
    source = canonical()
    assert len(source['roster'])==10
    assert len(source['registry']['states'])==33
    manifest=make_riven_manifest()
    assert manifest['name']=='Riven'
    assert manifest['identity_reference']['dimensions']==[1122,1402]
    assert manifest['identity_reference']['native_identity_owner_approved'] is False
    assert manifest['identity_reference']['sha256']==hashlib.sha256(
        (ROOT/manifest['identity_reference']['path']).read_bytes()).hexdigest()
    assert set(manifest['states'])==set(PILOT_KEYS)
    result=audit_pilot(manifest,ROOT)
    assert result['technical_source_passed']==0
    assert result['native_production_certified']==0
    assert result['production_release_enabled'] is False
    assert all(v['source']=='missing' for v in result['states'].values())


def test_reject_non_native_and_duplicate_sources(tmp_path):
    m=make_riven_manifest()
    file=tmp_path/'not_native.png'
    Image.new('RGB',(1122,1402)).save(file)
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    for key in ('neutral','confident'):
        m['states'][key].update({'source_file':file.name,'source_sha256':digest,
            'source_kind':'independent_standalone_native'})
    result=audit_pilot(m,tmp_path)
    assert result['technical_source_passed']==0
    assert 'neutral:non_native_source' in result['failures']
    assert 'confident:duplicate_bytes_with_neutral' in result['failures']


def test_native_pixel_dimensions_are_not_owner_approval(tmp_path):
    m=make_riven_manifest()
    p=tmp_path/'candidate.png'
    Image.new('RGB',(1536,1920)).save(p)
    m['states']['pointing'].update({'source_file':p.name,
       'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
       'source_kind':'independent_standalone_native'})
    res=audit_pilot(m,tmp_path)
    assert res['states']['pointing']['technical_preflight']=='PASS'
    assert res['states']['pointing']['native_certified'] is False
    assert res['native_production_certified']==0


def test_manifest_refuses_unauthorized_release_and_traversal(tmp_path):
    m=make_riven_manifest()
    m['production_release_enabled']=True
    with pytest.raises(ValueError):audit_pilot(m,tmp_path)
    m['production_release_enabled']=False
    m['states']['neutral']['source_file']='../../something.png'
    assert 'neutral:invalid_source_path' in audit_pilot(m,tmp_path)['failures']
