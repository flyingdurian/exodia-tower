"""Companion registry, UI state transition, and live route wiring."""
from fastapi.testclient import TestClient
from app.api.server import app, director


def test_roster_is_complete_and_unique():
    resp=TestClient(app).get('/api/companions')
    assert resp.status_code==200
    body=resp.json()
    assert len(body['agents'])==9
    assert len({a['id'] for a in body['agents']})==9
    assert all(a['persona'] and a['lines']['alert'] for a in body['agents'])
    assert all('idle' in a['clips'] for a in body['agents'])


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
