"""Synthetic acceptance tests; do not represent completed production portraits."""
import json,shutil,sys
from pathlib import Path
from PIL import Image
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from portrait_registry_audit import audit
from ingest_static_portraits import ingest
REG=Path(__file__).resolve().parents[1]/'frontend/companions/production/kiko/portrait_registry.json'

def test_animation_hooks_are_deferred_for_static_release():
    r=audit(REG)
    assert r['release_mode']=='static_portraits'
    assert r['status']=='FAILED' and r['states_verified']==0 and r['loops_verified']==0
    assert all(v['status']=='DEFERRED' for v in r['loops'].values())

def test_no_ingest_with_incomplete_owner_ledger(tmp_path):
    src=tmp_path/'src';src.mkdir();dst=tmp_path/'production';dst.mkdir()
    shutil.copyfile(REG,dst/'portrait_registry.json')
    ledger=tmp_path/'ledger.json'
    ledger.write_text(json.dumps({'schema':'exodia.portrait-static-approval-ledger/v1','states':{}}))
    with pytest.raises(ValueError,match='all_33_states'):
        ingest(src,dst,ledger,commit=True)
    assert not (dst/'frames').exists()

def test_missing_registration_blocks_even_native_image(tmp_path):
    src=tmp_path/'src';dst=tmp_path/'production';dst.mkdir()
    shutil.copyfile(REG,dst/'portrait_registry.json')
    image=src/'frames/expressions/neutral.png';image.parent.mkdir(parents=True)
    Image.new('RGB',(1536,1920),(8,9,11)).save(image)
    states=json.loads(REG.read_text())['states']
    ledger=tmp_path/'ledger.json'
    ledger.write_text(json.dumps({'schema':'exodia.portrait-static-approval-ledger/v1',
                                  'states':{k:{} for k in states}}))
    r=ingest(src,dst,ledger,commit=True)
    assert r['status']=='FAILED' and not r['staged']
    assert not (dst/'frames').exists()
