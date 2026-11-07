"""Autonomous local inference tests: no cloud accounts, no Playwright scraping."""
import asyncio
import httpx
from fastapi.testclient import TestClient
from app.automation.local_llm import OllamaBackend, LocalModelError
from app.operations.inbox import Inbox
from app.api.server import app

def test_local_llm_generates_from_loopback_without_key():
    async def go():
        def respond(request):
            assert request.url.host=='127.0.0.1'
            assert request.url.path=='/api/chat'
            body=__import__('json').loads(request.content)
            assert body['stream'] is False and body['messages'][1]['content']=='Hello'
            return httpx.Response(200,json={'message':{'content':'Hello from the local model!'},'eval_count':12})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as c:
            result=await OllamaBackend('llama3.2:3b',client=c).generate('Hello',companion='Nova')
            assert result['answer']=='Hello from the local model!'
            assert result['source']=='local_inference'
    asyncio.run(go())

def test_local_llm_missing_model_has_actionable_error():
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(404,json={'error':'not found'}))) as c:
            try:await OllamaBackend(client=c).generate('Hi',companion='Kiko')
            except LocalModelError as e:assert 'ollama list' in str(e)
            else:assert False,'Expected missing-model error'
    asyncio.run(go())

def test_persistent_running_tasks_fail_cleanly_after_restart(tmp_path):
    store=Inbox(tmp_path/'jobs.sqlite')
    t=store.create('nova','ollama','Explain this concept')
    store.update(t['id'],'state','running')
    Inbox(tmp_path/'jobs.sqlite').fail_interrupted()
    restored=Inbox(tmp_path/'jobs.sqlite').get(t['id'])
    assert restored['state']=='failed'
    assert 'restart' in restored['error']
    assert restored['answer']==''

def test_autonomous_task_delivered_without_manual_copy(monkeypatch):
    from app.api import server
    async def simulated(prompt,*,companion):
        await asyncio.sleep(.01)
        return {'answer':'A locally generated plan for '+companion,'source':'local_inference'}
    monkeypatch.setattr(server.local_model,'generate',simulated)
    h={'x-exodia-client':'exodia-dashboard'}
    with TestClient(app) as c:
        r=c.post('/api/command/tasks',headers=h,json={'prompt':'Write a content plan','model_choice':'ollama','agent_id':'nova'})
        assert r.status_code==201
        task=r.json()
        assert task['state']=='running'
        for i in range(40):
            finished=c.get('/api/command/tasks').json()
            job=next(t for t in finished['tasks'] if t['id']==task['id'])
            if job['state']=='answered':break
            import time;time.sleep(.025)
        assert job['state']=='answered'
        assert 'Nova' not in job['answer'] or 'nova' in job['answer']
        assert job['answer'].startswith('A locally generated plan')
        assert job['error']==''

def test_autonomous_failure_does_not_fake_success(monkeypatch):
    from app.api import server
    async def unavailable(prompt,*,companion):
        raise LocalModelError('Ollama not installed')
    monkeypatch.setattr(server.local_model,'generate',unavailable)
    h={'x-exodia-client':'exodia-dashboard'}
    with TestClient(app) as c:
        r=c.post('/api/command/tasks',headers=h,json={'prompt':'Test unavailable','model_choice':'ollama','agent_id':'kiko'})
        assert r.status_code==201
        task=r.json()
        for i in range(40):
            job=next(t for t in c.get('/api/command/tasks').json()['tasks'] if t['id']==task['id'])
            if job['state']=='failed':break
            import time;time.sleep(.025)
        assert job['state']=='failed'
        assert 'Ollama not installed' in job['error']
        assert not job['answer']
