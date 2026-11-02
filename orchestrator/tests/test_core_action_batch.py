"""No synthetic test portrait may be treated as approved production artwork."""
import json
import sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ingest_core_action_batch import queue_batch,validate_original,load,sha,validate_queue,KEYS
ROOT=Path(__file__).resolve().parents[2]

def test_batch_queue_matches_registry():
    manifest=load(ROOT/'assets/staging_intake/manifest_template.json')
    registry=load(ROOT/'orchestrator/frontend/companions/production/kiko/portrait_registry.json')
    rows=validate_queue(load(ROOT/'assets/staging_intake/core_actions_batch.json'),manifest,registry)
    assert tuple(x['key'] for x in rows)==KEYS

def test_undersized_reference_rejected(tmp_path):
    p=tmp_path/'working.png'
    Image.new('RGB',(1122,1402)).save(p)
    declaration=tmp_path/'working.source.json'
    declaration.write_text(json.dumps(dict(schema='exodia.independent-portrait-source/v1',
        source_kind='independent_standalone_native',derived_from_composite=False,
        native_canvas=[1122,1402],original_filename='working.png',original_sha256=sha(p),
        source_method='standalone_artist_export')))
    try:
        validate_original(p,declaration)
        assert False,'should reject undersized original'
    except ValueError as exc:
        assert 'undersized_original' in str(exc)

def test_draft_not_auto_approved(tmp_path):
    from shutil import copy2
    staging=tmp_path/'assets/staging_intake'
    production=tmp_path/'orchestrator/frontend/companions/production/kiko'
    staging.mkdir(parents=True)
    production.mkdir(parents=True)
    copy2(ROOT/'assets/staging_intake/manifest_template.json',staging/'manifest_template.json')
    registry=load(ROOT/'orchestrator/frontend/companions/production/kiko/portrait_registry.json')
    for entry in registry['states'].values():
        entry['status']='missing';entry['sha256']=None
    (production/'portrait_registry.json').write_text(json.dumps(registry))
    inbox=tmp_path/'new_originals';inbox.mkdir()
    p=inbox/'working.png'
    Image.new('RGB',(1856,2304),(20,40,70)).save(p)
    source={'schema':'exodia.independent-portrait-source/v1','source_kind':'independent_standalone_native',
        'derived_from_composite':False,'native_canvas':[1856,2304],'original_sha256':sha(p),
        'original_filename':'working.png','source_method':'independent_image_render',
        'human_source_review':'pending'}
    (inbox/'working.source.json').write_text(json.dumps(source))
    report=queue_batch(ROOT/'assets/staging_intake/core_actions_batch.json',staging,production,inbox,True,True)
    assert report['states'][0]['status']=='STAGED_PENDING_APPROVAL'
    assert report['committed_this_run']==0
    assert report['verified_total']==0
    assert (staging/'normalized_previews/working.png').is_file()
    assert load(staging/'approvals/working.json')['approved_by'] is None
    assert not (production/'frames/actions/working.png').exists()
    assert load(production/'portrait_registry.json')['release']['enabled'] is False
