"""Albedo production command layout and stateful delivery smoke test."""
from fastapi.testclient import TestClient
from app.api.server import app

def test_albedo_is_the_primary_dashboard():
    with TestClient(app) as c:
        result=c.get('/')
        assert result.status_code==200
        assert 'agentStageName' in result.text and 'taskComputer' in result.text
        assert 'Holographic terminal' in result.text
        assert 'moodList' not in result.text
        assert 'albedo_experience.mjs' in result.text
        assert 'albedo_command.js' in result.text
        assert c.get('/operations-legacy').status_code==200

def test_albedo_name_preserves_existing_kiko_internal_id():
    with TestClient(app) as c:
        data=c.get('/api/companions').json()
        albedo=next(a for a in data['agents'] if a['id']=='kiko')
        assert albedo['name']=='Albedo'
        assert albedo['portrait'].endswith('kiko.webp')
        assert not data['articulated_rigs_ready']

def test_albedo_layout_assets_are_served():
    with TestClient(app) as c:
        for url,token in [
            ('/assets/albedo_command.css','@keyframes haloPulse'),
            ('/assets/albedo_command.js','renderAnswer('),
            ('/assets/companions/clips/kiko/idle.mp4',None)
        ]:
            response=c.get(url)
            assert response.status_code==200,url
            if token:assert token in response.text
