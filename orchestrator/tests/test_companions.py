"""Companion registry, UI state transition, and live route wiring."""
from fastapi.testclient import TestClient
from app.api.server import app, director


def test_roster_is_complete_and_unique():
    resp=TestClient(app).get('/api/companions')
    assert resp.status_code==200
    body=resp.json()
    assert len(body['agents'])==10
    assert len({a['id'] for a in body['agents']})==10
    assert all(a['persona'] and a['lines']['alert'] for a in body['agents'])
    # Liu Bei has no approved native source/clip after the identity rename;
    # do not relabel the historical Riven animation as Liu Bei production art.
    assert all('idle' in a['clips'] for a in body['agents']
               if a['id'] not in ('nova','liu_bei'))
    liu_bei=next(a for a in body['agents'] if a['id']=='liu_bei')
    assert liu_bei['name']=='Liu Bei'
    assert liu_bei['portrait'] is None and liu_bei['thumbnail'] is None
    assert liu_bei['clips']=={}
    assert all(a['id']!='router' for a in body['agents'])
    assert next(a for a in body['agents'] if a['id']=='nova')['clips']=={}


def test_reactions_validate_states_and_roster():
    with TestClient(app) as client:
        assert client.post('/api/companions/kiko/react',json={'state':'thinking'}).json()['state']=='thinking'
        assert client.post('/api/companions/kiko/react',json={'state':'warp'}).status_code==422
        assert client.post('/api/companions/not-real/react',json={'state':'idle'}).status_code==422
        assert client.get('/api/companions').json()['states']['kiko']=='thinking'


def test_system_task_updates_director():
    with TestClient(app) as client:
        res=client.post('/api/ask',json={'question':'check system status', 'channel':'auto'})
        assert res.status_code==200
        assert res.json()['route']=='system'
        snapshot=client.get('/api/companions').json()['states']
        assert snapshot['kiko']=='success'
        assert snapshot['strategy']=='success'


def test_studio_assets_respond():
    with TestClient(app) as client:
        assert client.get('/companions').status_code==200
        assert client.get('/assets/companions/portraits/kiko.webp').status_code==200
        assert client.get('/assets/companions/clips/kiko/idle.mp4').status_code==200


def test_emotion_range_for_true_rig_contract():
    with TestClient(app) as client:
        for emotion in ('wonder','angry','hurt','disappointed','sleeping','processing','speaking','celebrating'):
            assert client.post('/api/companions/nova/react',json={'state':emotion}).status_code==200


def test_a11_motion_studio():
    with TestClient(app) as client:
        assert client.get('/puppet-lab').status_code == 200
        assert client.get('/assets/puppet_engine.mjs').status_code == 200
        body = client.get('/api/rigs').json()['rigs']
        assert len(body) == 10
        assert all(x['production_ready'] is False for x in body.values())
