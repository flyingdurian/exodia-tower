import time
from fastapi.testclient import TestClient
from app.api import server
from app.automation.model_instructions import InstructionStore, compose_model_prompt
from app.operations.inbox import Inbox

HEADERS={'x-exodia-client':'exodia-dashboard'}

def test_compose_leaves_plain_prompt_unchanged_and_hides_private_text():
    assert compose_model_prompt('  Hello there  ','')=='Hello there'
    composed=compose_model_prompt('What does the Fool suggest?','Stay under 400 characters.')
    assert composed.startswith('Private operator instructions')
    assert 'Stay under 400 characters.' in composed
    assert composed.endswith('What does the Fool suggest?')

def test_deepseek_receives_saved_and_task_instructions_but_api_hides_them(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'inbox',Inbox(tmp_path/'tasks.sqlite'))
    monkeypatch.setattr(server,'model_instructions',InstructionStore(tmp_path/'model_instructions.json'))
    server.model_instructions.save('deepseek','Answer as JuHua Speaks.')
    seen={}
    async def fake_send(platform, prompt, *, phase=None):
        seen['platform']=platform
        seen['prompt']=prompt
        if phase: phase('waiting_for_reply')
        return {'answer':'The Fool suggests a careful new beginning.','automatic_output':True,'media':[]}
    monkeypatch.setattr(server.router.sessions,'send_prompt_robust',fake_send)
    with TestClient(server.app) as client:
        created=client.post('/api/command/tasks',headers=HEADERS,json={
            'model_choice':'deepseek','transport':'browser','agent_id':'nova',
            'prompt':'What does the Fool suggest?','custom_instructions':'Theme: crossroads. Stay under 400 characters.'})
        assert created.status_code==201, created.text
        body=created.json()
        assert body['prompt']=='What does the Fool suggest?'
        assert 'private_instructions' not in body and 'custom_instructions' not in body
        dumped=created.text
        assert 'Answer as JuHua Speaks' not in dumped
        assert 'Stay under 400 characters' not in dumped
        latest=None
        for _ in range(40):
            latest=client.get('/api/command/tasks').json()['tasks'][0]
            if latest['state']=='answered': break
            time.sleep(.02)
        assert latest['state']=='answered'
        assert latest['answer'].startswith('The Fool suggests')
        listed=client.get('/api/command/tasks').text
        assert 'Answer as JuHua Speaks' not in listed
        assert 'Theme: crossroads' not in listed
    assert seen['platform']=='deepseek'
    assert 'Answer as JuHua Speaks.' in seen['prompt']
    assert 'Theme: crossroads. Stay under 400 characters.' in seen['prompt']
    assert 'User request:\nWhat does the Fool suggest?' in seen['prompt']
