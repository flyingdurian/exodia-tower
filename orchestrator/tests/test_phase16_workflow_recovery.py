"""Phase 16: explicit local-only recovery with immutable provenance."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.api import server
from app.operations.inbox import Inbox
from app.operations.workflow_plans import (
    OperatorWorkflowStore, WorkflowConflictError, WorkflowInputError
)
from app.operations.workflow_recovery import (
    WorkflowRecovery, safe_fork_result, CONFIRMATION, SCHEMA,
)


@pytest.fixture
def stores(tmp_path):
    db = tmp_path / "operator_workflows.sqlite"
    store = OperatorWorkflowStore(db)
    inbox = Inbox(tmp_path / "tasks.sqlite")
    recovery = WorkflowRecovery(store)
    return store, inbox, recovery


def graph():
    return [
        {"key":"research","agent_id":"archives","label":"Gather references",
         "depends_on":[]},
        {"key":"review","agent_id":"vault","label":"Check policy",
         "depends_on":["research"]},
        {"key":"draft","agent_id":"nova","label":"Prepare draft",
         "depends_on":["review"]},
    ]


def failed_plan(store, inbox):
    p=store.create(title="Original plan",steps=graph())
    a=inbox.create("archives","ollama","PRIVATE_RESEARCH_PROMPT")
    store.bind(p["id"],step_key="research",task_id=a["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(a["id"],"state","failed")
    return store.get(p["id"]), a


def test_failed_plan_forks_only_after_confirm_and_preserves_original(stores):
    store,inbox,recovery=stores
    source,task=failed_plan(store,inbox)
    with pytest.raises(WorkflowInputError,match="confirmation"):
        recovery.fork(source["id"],expected_revision=2,confirmation="APPROVE",inbox=inbox)
    result=safe_fork_result(store,recovery,source["id"],
                            2,CONFIRMATION,inbox)
    clone=result["workflow"]
    lineage=result["lineage"]
    assert result["schema"]==SCHEMA
    assert lineage["reason_code"]=="linked_task_failed"
    assert lineage["source_unmodified"] is True
    assert lineage["copied_task_id_count"]==0
    assert lineage["remote_dispatch_performed"] is False
    assert lineage["social_publishing_performed"] is False
    assert lineage["production_release_enabled"] is False
    assert clone["revision"]==1
    assert clone["status"]=="operator_planning"
    assert clone["step_count"]==3
    assert [s["depends_on"] for s in clone["steps"]]==[
        [],["research"],["review"]]
    assert all(s["linked_task_id"] is None for s in clone["steps"])
    assert all(s["agent_id"]==o["agent_id"]
               for s,o in zip(clone["steps"],source["steps"]))
    assert store.get(source["id"])==source
    assert store.get(source["id"])["steps"][0]["linked_task_id"]==task["id"]
    assert "PRIVATE_RESEARCH_PROMPT" not in json.dumps(result)


def test_exact_retry_is_idempotent_and_cross_store_concurrent_races_serialize(stores):
    store,inbox,recovery=stores
    source,_=failed_plan(store,inbox)
    instances=[WorkflowRecovery(OperatorWorkflowStore(store.path))
               for _ in range(3)]
    def invoke(index):
        return instances[index%3].fork(
            source["id"],expected_revision=2,
            confirmation=CONFIRMATION,inbox=inbox)[0]["id"]
    with ThreadPoolExecutor(max_workers=9) as pool:
        ids=list(pool.map(invoke,range(30)))
    assert len(set(ids))==1
    assert len(store.list(limit=50))==2
    with sqlite3.connect(store.path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM operator_workflow_recovery").fetchone()[0]==1
        assert conn.execute("PRAGMA quick_check(1)").fetchone()[0]=="ok"


def test_stale_revision_wrong_id_and_unreviewed_active_plan_fail_closed(stores):
    store,inbox,recovery=stores
    plan=store.create(title="Unreviewed work",steps=graph())
    with pytest.raises(WorkflowConflictError,match="requires"):
        recovery.fork(plan["id"],expected_revision=1,
                      confirmation=CONFIRMATION,inbox=inbox)
    failed,_=failed_plan(store,inbox)
    with pytest.raises(WorkflowConflictError,match="revision"):
        recovery.fork(failed["id"],expected_revision=1,
                      confirmation=CONFIRMATION,inbox=inbox)
    with pytest.raises(WorkflowInputError):
        recovery.fork("../private",expected_revision=1,
                      confirmation=CONFIRMATION,inbox=inbox)
    with pytest.raises(WorkflowInputError):
        recovery.fork(failed["id"],expected_revision=True,
                      confirmation=CONFIRMATION,inbox=inbox)


def test_locally_reviewed_plan_can_fork_but_not_inherit_review(stores):
    store,inbox,recovery=stores
    p=store.create(title="Reviewed",steps=[{
        "key":"stage","agent_id":"vault","label":"Check","depends_on":[]}])
    t=inbox.create("vault","ollama","PRIVATE_INPUT")
    store.bind(p["id"],step_key="stage",task_id=t["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(t["id"],"state","answered")
    reviewed=store.confirm_review(
        p["id"],expected_revision=2,
        confirmation="CONFIRM LOCAL WORKFLOW REVIEW",inbox=inbox)
    result=safe_fork_result(store,recovery,p["id"],
                            reviewed["revision"],CONFIRMATION,inbox)
    assert result["lineage"]["reason_code"]=="reviewed_plan_revision"
    assert result["workflow"]["operator_review_confirmed"] is False
    assert result["workflow"]["completed_task_count"]==0
    assert result["workflow"]["steps"][0]["linked_task_id"] is None


def test_missing_link_and_forged_agent_or_graph_cannot_fork(stores):
    store,inbox,recovery=stores
    src,_=failed_plan(store,inbox)
    with sqlite3.connect(store.path) as conn:
        fake=json.loads(json.dumps(src))
        fake["steps"][0]["agent_id"]="ninja"
        conn.execute("UPDATE operator_workflows SET document=? WHERE id=?",
                     (json.dumps(fake),src["id"]))
    with pytest.raises(WorkflowConflictError,match="ownership"):
        recovery.fork(src["id"],expected_revision=2,
                      confirmation=CONFIRMATION,inbox=inbox)


def test_local_fork_endpoint_never_dispatches_or_exposes_task_prompts(stores,monkeypatch):
    async def run():
        store,inbox,recovery=stores
        monkeypatch.setattr(server,"operator_workflows",store)
        monkeypatch.setattr(server,"inbox",inbox)
        source,_=failed_plan(store,inbox)
        url="/api/command/workflows/"+source["id"]+"/fork"
        body={"expected_revision":2,"confirmation":CONFIRMATION}
        h={"X-Exodia-Client":"exodia-dashboard"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                    base_url="http://testserver") as client:
            assert (await client.post(url,json=body)).status_code==403
            bad=await client.post(url,headers=h,json={
                "expected_revision":2,"confirmation":"PUBLISH"})
            assert bad.status_code==422
            ok=await client.post(url,headers=h,json=body)
            assert ok.status_code==201,ok.text
            result=ok.json()
            assert result["schema"]==SCHEMA
            assert result["workflow"]["revision"]==1
            assert result["workflow"]["production_release_enabled"] is False
            assert result["lineage"]["remote_dispatch_performed"] is False
            assert "PRIVATE_RESEARCH_PROMPT" not in ok.text
            retry=await client.post(url,headers=h,json=body)
            assert retry.status_code==201
            assert retry.json()["workflow"]["id"]==result["workflow"]["id"]
            assert (await client.get(url,headers=h)).status_code==405
            unknown=await client.post(
                "/api/command/workflows/not-found/fork",headers=h,json=body)
            assert unknown.status_code==404
    asyncio.run(run())
