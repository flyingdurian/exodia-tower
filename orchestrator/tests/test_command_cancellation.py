"""Local command-cancel contract, isolated from authenticated provider sessions."""
import asyncio
import pytest
import httpx

from app.operations.inbox import Inbox, TaskCancelled
from app.api import server


def test_inbox_cancel_is_atomic_idempotent_and_restart_safe(tmp_path):
    path = tmp_path / 'tasks.sqlite'
    inbox = Inbox(path)
    task = inbox.create('router', 'gemini', 'Inspect this route', private_instructions='Private direction')
    assert inbox.cancel(task['id'])['state'] == 'cancelled'
    assert inbox.cancel(task['id'])['state'] == 'cancelled'
    with pytest.raises(TaskCancelled):
        inbox.update(task['id'], 'answer', 'Late browser callback')
    with pytest.raises(TaskCancelled):
        inbox.update(task['id'], 'state', 'answered')
    assert Inbox(path).get(task['id'])['state'] == 'cancelled'
    inbox.fail_interrupted()
    assert Inbox(path).get(task['id'])['state'] == 'cancelled'


def test_finished_tasks_cannot_be_cancelled(tmp_path):
    inbox = Inbox(tmp_path / 'tasks.sqlite')
    task = inbox.create('kiko', 'ollama', 'Hello')
    inbox.update(task['id'], 'answer', 'Hello back')
    inbox.update(task['id'], 'state', 'answered')
    with pytest.raises(ValueError, match='cannot be cancelled'):
        inbox.cancel(task['id'])


def test_gemini_task_cancellation_suppresses_late_response(tmp_path, monkeypatch):
    async def run():
        isolated = Inbox(tmp_path / 'tasks.sqlite')
        monkeypatch.setattr(server, 'inbox', isolated)
        began, interrupted = asyncio.Event(), asyncio.Event()

        async def mock_provider(provider, prompt, *, phase=None):
            assert provider == 'gemini'
            if phase:
                phase('waiting_for_reply')
            began.set()
            try:
                await asyncio.sleep(20)
            except asyncio.CancelledError:
                interrupted.set()
                raise
            return {'answer': 'This should never be persisted'}

        monkeypatch.setattr(server.router.sessions, 'send_prompt_robust', mock_provider)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url='http://testserver') as client:
            headers = {'X-Exodia-Client': 'exodia-dashboard'}
            response = await client.post('/api/command/tasks', headers=headers, json={
                'agent_id': 'router', 'model_choice': 'gemini', 'transport': 'browser',
                'prompt': 'Safe synthetic local cancellation test',
                'custom_instructions': 'Do not log this private test instruction',
            })
            assert response.status_code == 201, response.text
            task = response.json()
            assert 'private_instructions' not in task
            await asyncio.wait_for(began.wait(), timeout=3)
            result = await client.post(f"/api/command/tasks/{task['id']}/cancel", headers=headers)
            assert result.status_code == 200, result.text
            assert result.json()['state'] == 'cancelled'
            await asyncio.wait_for(interrupted.wait(), timeout=3)
            await asyncio.sleep(.02)
            persisted = isolated.get(task['id'])
            assert persisted['state'] == 'cancelled' and persisted['answer'] == ''
            assert 'Do not log' not in str(result.json())
            assert (await client.post(f"/api/command/tasks/{task['id']}/cancel", headers=headers)).status_code == 200
            assert (await client.post(f"/api/command/tasks/{task['id']}/response", headers=headers,
                        json={'answer': 'Forged response'})).status_code == 409
            assert (await client.post('/api/command/tasks/no-such-id/cancel',headers=headers)).status_code == 404
            assert (await client.post('/api/command/tasks',json={
                'agent_id': 'kiko', 'model_choice': 'chatgpt', 'prompt': 'Missing header'
            })).status_code == 403
    asyncio.run(run())


@pytest.mark.parametrize('model',('chatgpt','gemini','deepseek','ollama'))
def test_cancelled_provider_job_releases_local_slot_and_cannot_deliver(tmp_path, monkeypatch, model):
    async def run():
        isolated=Inbox(tmp_path/(model+'.sqlite'))
        monkeypatch.setattr(server,'inbox',isolated)
        began=asyncio.Event()
        stopped=asyncio.Event()
        async def wait_then_cancel(*args, **kwargs):
            phase=kwargs.get('phase')
            if phase:phase('waiting_for_reply')
            began.set()
            try:await asyncio.sleep(20)
            except asyncio.CancelledError:
                stopped.set()
                raise
        if model=='chatgpt':
            monkeypatch.setattr(server.chatgpt_tasks,'submit',wait_then_cancel)
        elif model=='ollama':
            monkeypatch.setattr(server.local_model,'generate',wait_then_cancel)
        else:
            monkeypatch.setattr(server.router.sessions,'send_prompt_robust',wait_then_cancel)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
             base_url='http://testserver') as client:
            headers={'x-exodia-client':'exodia-dashboard'}
            r=await client.post('/api/command/tasks',headers=headers,json={
                'model_choice':model,'agent_id':'kiko','prompt':'Keep this synthetic test waiting'})
            assert r.status_code==201, r.text
            id=r.json()['id']
            await asyncio.wait_for(began.wait(),3)
            assert id in server.active_command_jobs
            cancelled=await client.post('/api/command/tasks/'+id+'/cancel',headers=headers)
            assert cancelled.status_code==200
            await asyncio.wait_for(stopped.wait(),3)
            await asyncio.sleep(.02)
            assert id not in server.active_command_jobs
            assert isolated.get(id)['state']=='cancelled'
            assert isolated.get(id)['answer']==''
    asyncio.run(run())
