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

def test_automatic_deepseek_cannot_skip_into_a_manual_response(monkeypatch):
    from app.api import server
    async def hold(platform, prompt, *, phase=None):
        if phase: phase('waiting_for_reply')
        await __import__('asyncio').sleep(.3)
        return {'answer':'DeepSeek held this reply long enough for the assertion.','automatic_output':True,'media':[]}
    monkeypatch.setattr(server.router.sessions,'send_prompt_robust',hold)
    client=TestClient(app)
    body={'prompt':'Write a video brief','model_choice':'deepseek','agent_id':'nova'}
    assert client.post('/api/command/tasks',json=body).status_code==403
    task=client.post('/api/command/tasks',json=body,headers={'x-exodia-client':'exodia-dashboard'}).json()
    assert task['state']=='opening'
    premature=client.post('/api/command/tasks/'+task['id']+'/response',
       json={'answer':'Unverified fake'},headers={'x-exodia-client':'exodia-dashboard'})
    assert premature.status_code==409
    prepared=client.post('/api/command/tasks/'+task['id']+'/prepare',headers={'x-exodia-client':'exodia-dashboard'})
    assert prepared.status_code==409
    assert client.get('/api/command/tasks').json()['automatic_extraction']['deepseek'] is True


def test_full_operator_handoff_updates_companion_screen(monkeypatch):
    from app.api.server import router, inbox
    async def fake_prepare(prompt, model):
        return {'model_choice':model,'status':'awaiting_operator','automatic_output':False}
    monkeypatch.setattr(router.models, 'generate', fake_prepare)
    monkeypatch.setattr(router.models, 'record_operator_response',
                        lambda model, response: {'answer':response,'source':'manual_copy'})
    client=TestClient(app)
    headers={'x-exodia-client':'exodia-dashboard'}
    task=inbox.create('nova','deepseek','Propose video titles')
    prepared=client.post('/api/command/tasks/'+task['id']+'/prepare',headers=headers)
    assert prepared.status_code==409
    inbox.update(task['id'],'state','awaiting_operator')
    delivered=client.post('/api/command/tasks/'+task['id']+'/response',
                json={'answer':'Three titles (operator copied)'},headers=headers)
    assert delivered.status_code==200
    assert delivered.json()['state']=='answered'
    assert delivered.json()['answer'].startswith('Three titles')
    assert client.get('/api/command/tasks').json()['automatic_extraction']['chatgpt'] is True
