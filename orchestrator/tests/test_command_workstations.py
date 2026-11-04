from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.operations.inbox import Inbox
from app.api.server import app

def test_inbox_is_persistent_and_truthful(tmp_path):
    f=tmp_path/'t.sqlite'
    s=Inbox(f)
    item=s.create('nova','gemini','Research short-form videos')
    assert item['state']=='draft'
    assert item['answer']==''
    assert s.update(item['id'],'state','awaiting_operator')['state']=='awaiting_operator'
    assert s.update(item['id'],'answer','Copied by operator')['answer']=='Copied by operator'
    assert Inbox(f).get(item['id'])['answer']=='Copied by operator'

def test_bad_models_rejected(tmp_path):
    s=Inbox(tmp_path/'t.sqlite')
    with pytest.raises(ValueError):s.create('kiko','not-a-model','Try this')

def test_new_dashboard_and_nova_agent():
    client=TestClient(app)
    r=client.get('/')
    assert r.status_code==200 and 'ALBEDO' in r.text
    legacy=client.get('/operations-legacy')
    assert legacy.status_code==200
    assert 'Media Division' in legacy.text and 'NOVA' in legacy.text
    agents=client.get('/api/companions').json()['agents']
    assert 'nova' in {x['id'] for x in agents}

def test_task_requires_operator_and_cannot_skip_prepare():
    client=TestClient(app)
    body={'prompt':'Write a video brief','model_choice':'deepseek','agent_id':'nova'}
    assert client.post('/api/command/tasks',json=body).status_code==403
    task=client.post('/api/command/tasks',json=body,headers={'x-exodia-client':'exodia-dashboard'}).json()
    assert task['state']=='draft'
    premature=client.post('/api/command/tasks/'+task['id']+'/response',
       json={'answer':'Unverified fake'},headers={'x-exodia-client':'exodia-dashboard'})
    assert premature.status_code==409
    assert client.get('/api/command/tasks').json()['automatic_extraction']['gemini'] is True


def test_full_operator_handoff_updates_companion_screen(monkeypatch):
    from app.api.server import router
    async def fake_prepare(prompt, model):
        return {'model_choice':model,'status':'awaiting_operator','automatic_output':False}
    monkeypatch.setattr(router.models, 'generate', fake_prepare)
    monkeypatch.setattr(router.models, 'record_operator_response',
                        lambda model, response: {'answer':response,'source':'manual_copy'})
    client=TestClient(app)
    headers={'x-exodia-client':'exodia-dashboard'}
    task=client.post('/api/command/tasks',json={
      'prompt':'Propose video titles','model_choice':'deepseek','agent_id':'nova'},headers=headers).json()
    prepared=client.post('/api/command/tasks/'+task['id']+'/prepare',headers=headers)
    assert prepared.status_code==200
    assert prepared.json()['task']['state']=='awaiting_operator'
    delivered=client.post('/api/command/tasks/'+task['id']+'/response',
                json={'answer':'Three titles (operator copied)'},headers=headers)
    assert delivered.status_code==200
    assert delivered.json()['state']=='answered'
    assert delivered.json()['answer'].startswith('Three titles')
    assert client.get('/api/command/tasks').json()['automatic_extraction']['chatgpt'] is True
