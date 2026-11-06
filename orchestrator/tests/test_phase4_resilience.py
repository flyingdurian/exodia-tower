"""Phase 4 durable history, explicit retry and stale-task recovery.

No authenticated browser, live external provider, or real user instruction is sent.
"""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import httpx
import pytest

from app.operations.inbox import Inbox, TaskCancelled
from app.api import server


def test_legacy_database_migrates_without_inventing_state_history(tmp_path):
    path=tmp_path/'older.sqlite'
    with sqlite3.connect(path) as c:
        c.execute("""CREATE TABLE tasks(id TEXT PRIMARY KEY,agent_id TEXT,provider TEXT,
                 prompt TEXT,state TEXT,answer TEXT DEFAULT '',artifact TEXT,
                 created_at TEXT,updated_at TEXT)""")
        c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
                  ("old-1","kiko","ollama","Legacy request","answered","Done",None,
                   "2025-01-01T00:00:00+00:00","2025-01-01T00:03:00+00:00"))
    inbox=Inbox(path)
    item=inbox.get("old-1")
    assert item['state']=='answered' and item['retry_index']==0 and item['retry_of'] is None
    assert inbox.events("old-1")[0]['event']=='legacy_snapshot'
    assert inbox.events("old-1")[0]['to_state']=='answered'
    assert inbox.events("old-1")[0]['from_state'] is None
    assert Inbox(path).events("old-1")==inbox.events("old-1")
    with sqlite3.connect(path) as c:
        assert c.execute("PRAGMA journal_mode").fetchone()[0].lower()=="wal"


def test_state_events_persist_and_never_store_private_instructions(tmp_path):
    path=tmp_path/'events.sqlite'
    inbox=Inbox(path)
    task=inbox.create("kiko","ollama","Actual task request",private_instructions="SECRET_HISTORY_SENTINEL")
    inbox.update(task['id'],'state','running')
    inbox.update(task['id'],'answer','A model response')
    inbox.update(task['id'],'state','answered')
    assert [event['event'] for event in inbox.events(task['id'])]==[
        'created','state_change','state_change']
    assert [event['to_state'] for event in Inbox(path).events(task['id'])]==[
        'draft','running','answered']
    assert "SECRET_HISTORY_SENTINEL" not in json.dumps(inbox.events(task['id']))
    assert "Actual task request" not in json.dumps(inbox.events(task['id']))
    assert len(inbox.list_page()['tasks'])==1


def test_retry_atomic_idempotent_and_lineage_is_restart_safe(tmp_path):
    path=tmp_path/'retry.sqlite'
    inbox=Inbox(path)
    parent=inbox.create("router","deepseek","Retry from original",
                        private_instructions="SECRET_RETRY_SENTINEL")
    inbox.update(parent['id'],'state','failed')
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda _:inbox.retry(parent['id']),range(5)))
    ids={r[0]['id'] for r in results}
    assert len(ids)==1 and sum(created for _,created in results)==1
    child=results[0][0]
    assert child['retry_of']==parent['id'] and child['retry_index']==1
    assert child['private_instructions']=='SECRET_RETRY_SENTINEL'
    assert len(Inbox(path).list_page()['tasks'])==2
    assert [e['event'] for e in inbox.events(parent['id'])][-1]=='retry_requested'
    assert 'SECRET_RETRY_SENTINEL' not in json.dumps(inbox.events(child['id']))
    for step in (2,3):
        inbox.update(child['id'],'state','failed')
        child,created=inbox.retry(child['id'])
        assert created and child['retry_index']==step
    inbox.update(child['id'],'state','failed')
    with pytest.raises(ValueError,match='Retry limit'):
        inbox.retry(child['id'])
    assert len(Inbox(path).list_page(limit=50)['tasks'])==4


def test_invalid_retries_and_terminal_late_callbacks_are_rejected(tmp_path):
    inbox=Inbox(tmp_path/'terminal.sqlite')
    task=inbox.create('kiko','ollama','Do not retry active tasks')
    with pytest.raises(ValueError,match='Only failed'):
        inbox.retry(task['id'])
    inbox.cancel(task['id'])
    with pytest.raises(TaskCancelled):
        inbox.update(task['id'],'answer','Late consumer result')
    child,created=inbox.retry(task['id'])
    assert created
    inbox.update(child['id'],'state','failed')
    with pytest.raises(TaskCancelled):
        inbox.update(child['id'],'state','answered')
    with pytest.raises(TaskCancelled):
        inbox.update(child['id'],'answer','Impossible late success')
    assert inbox.get(child['id'])['answer']==''


def test_stale_cleanup_preserves_manual_and_completed_tasks(tmp_path):
    inbox=Inbox(tmp_path/'stale.sqlite')
    stalled=inbox.create('kiko','gemini','A stalled browser job')
    manual=inbox.create('router','chatgpt','A manual handoff')
    completed=inbox.create('kiko','ollama','A completed answer')
    inbox.update(stalled['id'],'state','waiting_for_reply')
    inbox.update(manual['id'],'state','awaiting_operator')
    inbox.update(completed['id'],'state','answered')
    future=datetime.now(timezone.utc)+timedelta(hours=2)
    expired=inbox.cleanup_stale(maximum_idle_seconds=3600,now=future)
    assert expired==[stalled['id']]
    assert inbox.get(stalled['id'])['state']=='failed'
    assert inbox.get(manual['id'])['state']=='awaiting_operator'
    assert inbox.get(completed['id'])['state']=='answered'
    assert inbox.events(stalled['id'])[-1]['event']=='stale_cleanup'
    assert inbox.cleanup_stale(maximum_idle_seconds=3600,now=future)==[]
    with pytest.raises(TaskCancelled):
        inbox.update(stalled['id'],'answer','A late completed provider response')


def test_restart_recovery_has_auditable_state_and_no_cancel_regression(tmp_path):
    path=tmp_path/'restart.sqlite'
    inbox=Inbox(path)
    active=inbox.create('kiko','ollama','Interrupted query')
    cancelled=inbox.create('router','gemini','Cancellation survives restart')
    inbox.update(active['id'],'state','running')
    inbox.cancel(cancelled['id'])
    inbox.fail_interrupted()
    again=Inbox(path)
    assert again.get(active['id'])['state']=='failed'
    assert again.get(cancelled['id'])['state']=='cancelled'
    assert [e['event'] for e in again.events(active['id'])][-1]=='restart_interrupted'
    assert [e['event'] for e in again.events(cancelled['id'])][-1]=='cancelled'
    with pytest.raises(TaskCancelled):
        again.update(active['id'],'answer','Late result')


def test_pagination_is_bounded_and_history_is_not_truncated(tmp_path):
    inbox=Inbox(tmp_path/'pages.sqlite')
    for n in range(81):
        inbox.create('kiko','ollama',f'Historical task {n}')
    first=inbox.list_page(limit=30,offset=0)
    second=inbox.list_page(limit=30,offset=30)
    third=inbox.list_page(limit=30,offset=60)
    assert first['total']==81 and len(first['tasks'])==30
    assert len(second['tasks'])==30 and len(third['tasks'])==21
    assert len({x['id'] for x in first['tasks']+second['tasks']+third['tasks']})==81
    with pytest.raises(ValueError,match='pagination'):
        inbox.list_page(limit=201)


def test_retry_api_external_confirmation_is_explicit_and_no_secrets_leak(tmp_path,monkeypatch):
    async def run():
        isolated=Inbox(tmp_path/'api.sqlite')
        monkeypatch.setattr(server,'inbox',isolated)
        old=isolated.create('kiko','gemini','Synthetic browser source',
                            private_instructions='NEVER_EXPOSE_PRIVATE_INSTRUCTIONS')
        isolated.update(old['id'],'state','failed')
        called=[]
        async def fake_browser(provider,prompt,*,phase=None):
            called.append(provider)
            if phase:phase('waiting_for_reply')
            return {'answer':'Synthetic browser reply','timings':{},'media':[]}
        monkeypatch.setattr(server.router.sessions,'send_prompt_robust',fake_browser)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                      base_url='http://testserver') as client:
            h={'x-exodia-client':'exodia-dashboard'}
            url=f"/api/command/tasks/{old['id']}/retry"
            blocked=await client.post(url,headers=h,json={})
            assert blocked.status_code==409 and not called
            assert len(isolated.list_page()['tasks'])==1
            created=await client.post(url,headers=h,json={'confirm_external_redelivery':True})
            assert created.status_code==201,created.text
            obj=created.json()
            assert obj['retry_of']==old['id'] and obj['retry_index']==1
            assert 'private_instructions' not in obj
            await asyncio.wait_for(server.active_command_jobs[obj['id']],3)
            assert called==['gemini']
            assert isolated.get(obj['id'])['state']=='answered'
            duplicate=await client.post(url,headers=h,json={'confirm_external_redelivery':True})
            assert duplicate.status_code==201 and duplicate.json()['id']==obj['id']
            assert called==['gemini']
            history=await client.get('/api/command/tasks/history?limit=10&offset=0',headers=h)
            assert history.status_code==200
            assert history.json()['total']==2
            assert 'NEVER_EXPOSE_PRIVATE_INSTRUCTIONS' not in history.text
            events=await client.get(f"/api/command/tasks/{obj['id']}/events",headers=h)
            assert events.status_code==200
            assert 'NEVER_EXPOSE_PRIVATE_INSTRUCTIONS' not in events.text
            assert (await client.get('/api/command/tasks/history')).status_code==403
    asyncio.run(run())


def test_local_retry_does_not_require_browser_confirmation(tmp_path,monkeypatch):
    async def run():
        isolated=Inbox(tmp_path/'local.sqlite')
        monkeypatch.setattr(server,'inbox',isolated)
        old=isolated.create('kiko','ollama','Synthetic local retry')
        isolated.update(old['id'],'state','failed')
        calls=[]
        async def fake_model(prompt,*,companion):
            calls.append(prompt)
            return {'answer':'Local recovered'}
        monkeypatch.setattr(server.local_model,'generate',fake_model)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                      base_url='http://testserver') as client:
            reply=await client.post('/api/command/tasks/'+old['id']+'/retry',
                                    headers={'x-exodia-client':'exodia-dashboard'},json={})
            assert reply.status_code==201,reply.text
            child=reply.json()['id']
            await asyncio.wait_for(server.active_command_jobs[child],3)
            assert isolated.get(child)['answer']=='Local recovered'
            assert len(calls)==1
    asyncio.run(run())


def test_stale_reaper_cancels_local_job_without_remote_revoke_claim(tmp_path,monkeypatch):
    async def run():
        isolated=Inbox(tmp_path/'reaper.sqlite')
        monkeypatch.setattr(server,'inbox',isolated)
        task=isolated.create('kiko','gemini','Long running synthetic task')
        isolated.update(task['id'],'state','waiting_for_reply')
        with isolated.db() as c:
            c.execute("UPDATE tasks SET updated_at=? WHERE id=?",
                      ('2020-01-01T00:00:00+00:00',task['id']))
        stopped=asyncio.Event()
        async def sleeper():
            try:await asyncio.sleep(60)
            except asyncio.CancelledError:
                stopped.set()
                raise
        job=asyncio.create_task(sleeper())
        monkeypatch.setitem(server.active_command_jobs,task['id'],job)
        await asyncio.sleep(0)
        ids=await server.run_stale_task_cleanup_once()
        assert ids==[task['id']]
        await asyncio.wait_for(stopped.wait(),3)
        assert isolated.get(task['id'])['state']=='failed'
        assert 'may continue' in isolated.get(task['id'])['error']
        assert isolated.events(task['id'])[-1]['event']=='stale_cleanup'
        try:await job
        except asyncio.CancelledError:pass
        server.active_command_jobs.pop(task['id'],None)
    asyncio.run(run())
