"""Albedo-only operations sprite scaffold, not a native production-art claim."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.api.server import app

ROOT=Path(__file__).resolve().parents[1]
FRONT=ROOT/'frontend'


def test_chibi_manifest_is_complete_40_slot_nonart_scaffold():
    j=json.loads((FRONT/'albedo_chibi_manifest.json').read_text())
    assert j['schema']=='exodia.albedo-chibi/v1'
    assert j['character_id']=='kiko'
    assert j['production_release_enabled'] is False
    assert j['asset_status']=='pending_production_frames'
    directions=('n','ne','e','se','s','sw','w','nw')
    assert tuple(j['directions'])==directions
    assert set(j['frames']) == {
        key for direction in directions for key in
        [f'idle_{direction}']+[f'walk_{direction}_{i:02}' for i in range(4)]
    }
    assert all(f['src'] is None and f['sha256'] is None and
               f['approval_sha256'] is None for f in j['frames'].values())
    assert j['source_policy']['composite_slicing_prohibited']
    assert j['source_policy']['owner_sha_bound_approval_required']
    assert j['anchors']['foot']==[.5,.94]
    assert j['anchors']['shadow']==[.5,.96]
    assert all(0 <= z['x'] <= 1 and 0 <= z['y'] <= 1 for z in j['zones'].values())


def test_real_command_app_serves_motion_contract_and_status_modules():
    with TestClient(app) as client:
        front=client.get('/');assert front.status_code==200
        for key in ('commandStatusStrip','buildChannel','buildShortSha',
                    'summaryAgent','summarySelectedCompanion','summaryTask','summaryProvider','summaryState',
                    'summaryResult','summaryLatency','summaryBackground','chibiOperations',
                    'chibiActor','chibiFrame','chibiArtStatus'):
            assert f'id="{key}"' in front.text
        assert '/assets/albedo_chibi_boot.mjs' in front.text
        for name in ('albedo_chibi_controller.mjs','albedo_chibi_renderer.mjs',
                     'albedo_chibi_boot.mjs','albedo_chibi_manifest.json',
                     'command_status.mjs'):
            assert client.get('/assets/'+name).status_code==200
        j=client.get('/assets/albedo_chibi_manifest.json').json()
        assert j['production_release_enabled'] is False and len(j['frames'])==40
        b=client.get('/api/build-info').json()
        assert b['channel'] in ('local','development','release')


def test_existing_portrait_release_remains_locked_separate_from_chibi():
    path=FRONT/'companions/production/kiko/portrait_registry.json'
    data=json.loads(path.read_text())
    assert data['release']['enabled'] is False
    assert len(data['states'])==33
    assert all(s['status']=='pending_production_art' for s in data['states'].values())
    for other in ('liu_bei','memory','archives','inventory','vault','ninja','cache','strategy','nova'):
        assert other not in (FRONT/'albedo_chibi_manifest.json').read_text()
