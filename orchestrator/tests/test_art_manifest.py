"""Kiko production-layer registration and admitted QA limitations."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.api.server import app
from app.config import Settings
ROOT=Settings().root
ART=ROOT/'frontend/artwork/kiko_prime'
def test_identity_and_production_gate():
    m=json.loads((ART/'manifest.json').read_text())
    assert m['agent_id']=='kiko'
    assert m['approved_source']=='/assets/companions/source_masters/kiko.png'
    assert m['production_ready'] is False
    assert len(m['quality_notes'])>=4
def test_source_registered_layers():
    m=json.loads((ART/'manifest.json').read_text()); w,h=m['source_size']
    assert (w,h)==(1122,1402)
    moving=[v for v in m['layers'].values() if 'polygons' in v]
    assert len(moving)>=13
    for layer in moving:
        assert layer['pivot'] and len(layer['pivot'])==2
        assert all(len(poly)>=3 for poly in layer['polygons'])
        assert all(0<=x<w and 0<=y<h for poly in layer['polygons'] for x,y in poly)
def test_source_assets_exist():
    m=json.loads((ART/'manifest.json').read_text())
    assert (ROOT/'frontend'/m['approved_source'].removeprefix('/assets/')).is_file()
    for layer in m['layers'].values():
        assert (ROOT/'frontend'/layer['src'].removeprefix('/assets/')).is_file()
def test_art_studio_serves():
    r=TestClient(app).get('/art-studio')
    assert r.status_code==200
    assert 'Living Art' in r.text
