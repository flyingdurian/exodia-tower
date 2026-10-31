"""Persistent editorial store and API security regression gates."""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from app.social.workflow import EditorialStore, WorkflowError
from app.api.server import app


def test_durable_queue_and_stage_guards(tmp_path):
    path=tmp_path/'social.sqlite'
    store=EditorialStore(path)
    job=store.create('A Vancouver travel story',['youtube','tiktok'],'Original travel analysis')
    assert EditorialStore(path).get(job['id'])['stage']=='idea'
    with pytest.raises(WorkflowError):store.advance(job['id'],'published')
    for target in ('research','script','assets','edit','review'):
        store.advance(job['id'],target)
    with pytest.raises(WorkflowError):store.approve(job['id'],'APPROVE CONTENT')
    store.update(job['id'],{'script':'Original tested outline'})
    approved=store.approve(job['id'],'APPROVE CONTENT')
    assert approved['stage']=='approved'
    with pytest.raises(WorkflowError):store.advance(job['id'],'scheduled')
    revoked=store.update(job['id'],{'caption':'New caption requires fresh review'})
    assert revoked['approval'] is None and revoked['stage']=='review'


def test_source_and_platform_validation(tmp_path):
    store=EditorialStore(tmp_path/'e.sqlite')
    for p in (['youtube','bsky'],[],['tiktok','invalid']):
        with pytest.raises(WorkflowError):store.create('Title',p)
    with pytest.raises(WorkflowError):store.create('Title',['youtube'],source_urls=['http://unsafe.example'])


def test_api_editorial_does_not_publish():
    with TestClient(app) as client:
        assert client.get('/api/social/status').status_code==200
        assert client.post('/api/social/jobs',json={'title':'No CSRF header','platforms':['youtube']}).status_code==403
        created=client.post('/api/social/jobs',headers={'X-Exodia-Client':'exodia-dashboard'},json={'title':'Editorial integration test','platforms':['youtube','tiktok','instagram']})
        assert created.status_code==201
        j=created.json()
        assert j['analytics']['status']=='not_connected'
        assert client.get(f"/api/social/jobs/{j['id']}/brief").json()['status']=='template_only'
        published=client.post(f"/api/social/jobs/{j['id']}/publish",headers={'X-Exodia-Client':'exodia-dashboard'})
        assert published.status_code==409
        assert client.get(f"/api/social/jobs/{j['id']}").json()['published_at'] is None
