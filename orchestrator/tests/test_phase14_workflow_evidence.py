"""Phase 14: evidence reconciliation, truthful uncertainty and strict privacy."""
from __future__ import annotations

import json
import sqlite3

import pytest

from app.operations.inbox import Inbox
from app.operations.workflow_plans import (
    OperatorWorkflowStore, WorkflowConflictError
)
from app.operations.workflow_evidence import (
    SCHEMA, WorkflowEvidenceError, collect_workflow_evidence
)


@pytest.fixture
def stores(tmp_path):
    return (OperatorWorkflowStore(tmp_path / "plans.sqlite"),
            Inbox(tmp_path / "tasks.sqlite"))


def steps():
    return [
        {"key":"research","agent_id":"archives","label":"Research findings","depends_on":[]},
        {"key":"review","agent_id":"vault","label":"Permission check","depends_on":["research"]},
        {"key":"draft","agent_id":"nova","label":"Draft proposal","depends_on":["review"]},
    ]


def test_real_task_events_corroborate_answered_dag_without_private_text(stores):
    store,inbox=stores
    plan=store.create(title="No credentials in evidence",steps=steps())
    r=inbox.create("archives","ollama","SECRET_RESEARCH_PROMPT",
                    private_instructions="PRIVATE_TOOL_TOKEN")
    first=store.bind(plan["id"],step_key="research",task_id=r["id"],
                     expected_revision=1,inbox=inbox)
    check=collect_workflow_evidence(first,inbox)
    assert check["schema"] == SCHEMA
    assert check["operator_link_ready_count"] == 0
    assert check["steps"][0]["audit_evidence"] == "task_active_or_draft"
    assert check["steps"][1]["step_status"] == "blocked_on_dependencies"
    assert check["read_only"] is True
    assert check["external_dispatch_performed"] is False
    assert check["production_release_enabled"] is False
    inbox.update(r["id"],"answer","SECRET_ANSWER_NEVER_EXPOSE")
    inbox.update(r["id"],"state","answered")
    proof=collect_workflow_evidence(store.get(plan["id"]),inbox)
    assert proof["answered_task_count"] == 1
    assert proof["answered_event_recorded_count"] == 1
    assert proof["steps"][0]["audit_evidence"] == "answered_event_recorded"
    assert proof["steps"][0]["answer_event_kind"] == "state_change"
    assert proof["operator_link_ready_count"] == 1
    assert proof["next_operator_action"] == "link_existing_tasks_manually"
    for private in ("SECRET_RESEARCH_PROMPT","PRIVATE_TOOL_TOKEN","SECRET_ANSWER_NEVER_EXPOSE"):
        assert private not in json.dumps(proof)


def test_corrupted_or_missing_history_does_not_become_fake_evidence(stores,monkeypatch):
    store,inbox=stores
    plan=store.create(title="Detect uncertainty",steps=[
        {"key":"step","agent_id":"vault","label":"Inspect","depends_on":[]}
    ])
    task=inbox.create("vault","ollama","Prompt")
    store.bind(plan["id"],step_key="step",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(task["id"],"state","answered")
    monkeypatch.setattr(inbox,"events",lambda task_id,limit=500: [])
    report=collect_workflow_evidence(store.get(plan["id"]),inbox)
    assert report["answered_task_count"] == 1
    assert report["answered_event_recorded_count"] == 0
    assert report["all_answered_events_corroborated"] is False
    assert report["steps"][0]["audit_evidence"] == "answered_without_event_proof"
    assert report["authenticated_provider_acceptance"] == "not_established"


def test_failed_task_is_labeled_as_manual_recovery_not_silent_retry(stores):
    store,inbox=stores
    plan=store.create(title="Failed route",steps=[
        {"key":"stage","agent_id":"liu_bei","label":"Route","depends_on":[]}
    ])
    task=inbox.create("liu_bei","ollama","SECRET_PROMPT")
    store.bind(plan["id"],step_key="stage",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(task["id"],"state","failed")
    report=collect_workflow_evidence(store.get(plan["id"]),inbox)
    assert report["failed_linked_task_count"] == 1
    assert report["next_operator_action"] == "inspect_failed_tasks_and_create_new_plan"
    assert report["steps"][0]["audit_evidence"] == "terminal_unsuccessful"
    assert report["steps"][0]["provider_authentication_verified"] is False


def test_stored_agent_drift_and_release_lock_drift_fail_closed(stores):
    store,inbox=stores
    plan=store.create(title="Protect owner",steps=[
        {"key":"stage","agent_id":"vault","label":"Policy","depends_on":[]}
    ])
    task=inbox.create("vault","ollama","SECRET")
    linked=store.bind(plan["id"],step_key="stage",task_id=task["id"],
                      expected_revision=1,inbox=inbox)
    tampered=json.loads(json.dumps(linked))
    tampered["steps"][0]["agent_id"]="ninja"
    with pytest.raises(WorkflowEvidenceError,match="owner"):
        collect_workflow_evidence(tampered,inbox)
    not_plan=json.loads(json.dumps(linked))
    not_plan["schema"]="unsafe.approval/v1"
    with pytest.raises(WorkflowEvidenceError,match="persisted"):
        collect_workflow_evidence(not_plan,inbox)


def test_restart_durability_corroborates_original_existing_task(stores,tmp_path):
    store,inbox=stores
    plan=store.create(title="Durable",steps=[
        {"key":"x","agent_id":"archives","label":"Verify","depends_on":[]}
    ])
    task=inbox.create("archives","ollama","Sensitive persistent task")
    store.bind(plan["id"],step_key="x",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(task["id"],"state","answered")
    freshStore=OperatorWorkflowStore(store.path)
    freshInbox=Inbox(inbox.path)
    output=collect_workflow_evidence(freshStore.get(plan["id"]),freshInbox)
    assert output["answered_event_recorded_count"] == 1
    with sqlite3.connect(store.path) as c:
        assert c.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"


def test_guarded_evidence_http_endpoint_is_non_mutating_and_redacted(stores,monkeypatch):
    import asyncio
    import httpx
    from app.api import server
    async def run():
        store,inbox=stores
        monkeypatch.setattr(server,"operator_workflows",store)
        monkeypatch.setattr(server,"inbox",inbox)
        plan=store.create(title="Private plan",steps=[
            {"key":"inspect","agent_id":"vault","label":"Inspect","depends_on":[]}
        ])
        task=inbox.create("vault","ollama","TOP_SECRET_PROMPT")
        store.bind(plan["id"],step_key="inspect",task_id=task["id"],
                   expected_revision=1,inbox=inbox)
        inbox.update(task["id"],"state","answered")
        async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=server.app),
                base_url="http://testserver") as client:
            url="/api/command/workflows/"+plan["id"]+"/evidence"
            assert (await client.get(url)).status_code==403
            response=await client.get(
                url,headers={"X-Exodia-Client":"exodia-dashboard"})
            assert response.status_code==200,response.text
            body=response.json()
            assert body["answered_event_recorded_count"]==1
            assert body["read_only"] is True
            assert body["external_dispatch_performed"] is False
            assert "TOP_SECRET_PROMPT" not in response.text
            assert (await client.post(url,headers={
                "X-Exodia-Client":"exodia-dashboard"})).status_code==405
            missing=await client.get(
                "/api/command/workflows/missing/evidence",
                headers={"X-Exodia-Client":"exodia-dashboard"})
            assert missing.status_code==404
    asyncio.run(run())
