"""Phase 13: durable local DAG task plans with no autonomous provider dispatch."""
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
    AGENTS, OperatorWorkflowStore, WorkflowConflictError,
    WorkflowInputError, project_plan, validate_steps, SCHEMA
)


@pytest.fixture
def setup(tmp_path):
    store = OperatorWorkflowStore(tmp_path / "operator_workflows.sqlite")
    inbox = Inbox(tmp_path / "tasks.sqlite")
    return store, inbox


def plan_steps():
    return [
        {"key":"research","agent_id":"archives","label":"Check the evidence",
         "depends_on":[]},
        {"key":"strategy","agent_id":"strategy","label":"Assess options",
         "depends_on":["research"]},
        {"key":"draft","agent_id":"nova","label":"Draft an operator review",
         "depends_on":["strategy"]},
    ]


def test_dag_creation_is_durable_ordered_and_never_dispatches_tasks(setup, tmp_path):
    store, inbox = setup
    first = store.create(title="Research then draft", steps=plan_steps())
    assert first["schema"] == SCHEMA
    assert first["revision"] == 1
    assert first["status"] == "operator_planning"
    fresh = OperatorWorkflowStore(tmp_path / "operator_workflows.sqlite")
    projected = project_plan(fresh.get(first["id"]), inbox)
    assert projected["step_count"] == 3
    assert [s["status"] for s in projected["steps"]] == [
        "ready_for_operator_link", "blocked_on_dependencies",
        "blocked_on_dependencies"
    ]
    assert projected["external_dispatch_performed"] is False
    assert projected["social_publishing_performed"] is False
    assert projected["production_release_enabled"] is False
    assert inbox.list() == []


def test_real_linked_task_dependencies_then_explicit_review(setup):
    store, inbox = setup
    created = store.create(title="Three-agent pipeline", steps=plan_steps())
    a = inbox.create("archives", "ollama", "SECRET_ARCHIVE_PROMPT")
    b = inbox.create("strategy", "ollama", "SECRET_STRATEGY_PROMPT")
    c = inbox.create("nova", "ollama", "SECRET_NOVA_PROMPT")
    with pytest.raises(WorkflowConflictError, match="dependency"):
        store.bind(created["id"], step_key="strategy", task_id=b["id"],
                   expected_revision=1, inbox=inbox)
    first = store.bind(created["id"], step_key="research", task_id=a["id"],
                       expected_revision=1, inbox=inbox)
    assert first["revision"] == 2
    # Idempotent retries cannot link the same task twice or bump the revision.
    assert store.bind(created["id"], step_key="research", task_id=a["id"],
                      expected_revision=1, inbox=inbox)["revision"] == 2
    with pytest.raises(WorkflowConflictError, match="dependency"):
        store.bind(created["id"], step_key="strategy", task_id=b["id"],
                   expected_revision=2, inbox=inbox)
    inbox.update(a["id"], "state", "answered")
    second = store.bind(created["id"], step_key="strategy", task_id=b["id"],
                        expected_revision=2, inbox=inbox)
    assert second["revision"] == 3
    with pytest.raises(WorkflowConflictError, match="dependency"):
        store.bind(created["id"], step_key="draft", task_id=c["id"],
                   expected_revision=3, inbox=inbox)
    inbox.update(b["id"], "state", "answered")
    third = store.bind(created["id"], step_key="draft", task_id=c["id"],
                       expected_revision=3, inbox=inbox)
    assert third["revision"] == 4
    report = project_plan(third, inbox)
    assert report["completed_task_count"] == 2
    assert report["steps"][2]["status"] == "linked_task_in_progress"
    for private in ("SECRET_ARCHIVE_PROMPT", "SECRET_STRATEGY_PROMPT",
                    "SECRET_NOVA_PROMPT"):
        assert private not in json.dumps(report)
    with pytest.raises(WorkflowInputError, match="confirmation"):
        store.confirm_review(created["id"], expected_revision=4,
                             confirmation="APPROVE PUBLISHING", inbox=inbox)
    with pytest.raises(WorkflowConflictError, match="answered"):
        store.confirm_review(created["id"], expected_revision=4,
                             confirmation="CONFIRM LOCAL WORKFLOW REVIEW", inbox=inbox)
    inbox.update(c["id"], "state", "answered")
    reviewed = store.confirm_review(
        created["id"], expected_revision=4,
        confirmation="CONFIRM LOCAL WORKFLOW REVIEW", inbox=inbox)
    final = project_plan(reviewed, inbox)
    assert final["completed_task_count"] == 3
    assert final["operator_review_confirmed"] is True
    assert final["status"] == "reviewed_local_only"
    assert final["social_publishing_performed"] is False
    assert final["external_dispatch_performed"] is False
    assert store.confirm_review(created["id"], expected_revision=4,
                                 confirmation="CONFIRM LOCAL WORKFLOW REVIEW",
                                 inbox=inbox)["revision"] == 5


def test_unknown_task_agent_mismatch_and_double_assignment_are_blocked(setup):
    store, inbox = setup
    first = store.create(title="First", steps=[
        {"key":"a","label":"A1","agent_id":"vault","depends_on":[]}
    ])
    wrong = inbox.create("ninja", "ollama", "WRONG_AGENT")
    with pytest.raises(WorkflowConflictError, match="Companion"):
        store.bind(first["id"],step_key="a",task_id=wrong["id"],
                   expected_revision=1,inbox=inbox)
    actual = inbox.create("vault", "ollama", "VAULT_TASK")
    other = store.create(title="Second", steps=[
        {"key":"a","label":"A2","agent_id":"vault","depends_on":[]}
    ])
    store.bind(first["id"],step_key="a",task_id=actual["id"],
               expected_revision=1,inbox=inbox)
    with pytest.raises(WorkflowConflictError, match="already assigned"):
        store.bind(other["id"],step_key="a",task_id=actual["id"],
                   expected_revision=1,inbox=inbox)
    with pytest.raises(WorkflowConflictError, match="revision"):
        store.bind(first["id"],step_key="a",task_id=wrong["id"],
                   expected_revision=1,inbox=inbox)
    inbox.update(wrong["id"], "state", "failed")
    another = store.create(title="Third", steps=[
        {"key":"a","label":"A3","agent_id":"ninja","depends_on":[]}
    ])
    with pytest.raises(WorkflowConflictError, match="Terminal"):
        store.bind(another["id"], step_key="a", task_id=wrong["id"],
                   expected_revision=1,inbox=inbox)


@pytest.mark.parametrize("bad", [
    [],
    [{}],
    [{"key":"a","agent_id":"vault","label":"X","depends_on":["b"]}],
    [
      {"key":"a","agent_id":"vault","label":"A","depends_on":[]},
      {"key":"a","agent_id":"vault","label":"B","depends_on":[]}
    ],
    [
      {"key":"a","agent_id":"vault","label":"A","depends_on":[]},
      {"key":"b","agent_id":"vault","label":"B","depends_on":["b"]}
    ],
    [{"key":"a","agent_id":"router","label":"Old ID","depends_on":[]}],
    [{"key":"a","agent_id":"vault","label":"No\nNewline\n","depends_on":[]}],
    [{"key":"a","agent_id":"vault","label":"X","depends_on":[],
      "secret_payload":"blocked"}],
])
def test_invalid_dags_and_unknown_companion_keys_fail_closed(bad):
    with pytest.raises(WorkflowInputError):
        validate_steps(bad)


def test_12_node_limit_and_all_ten_stable_agents_are_supported(setup):
    store, _ = setup
    all_ten = sorted(AGENTS)
    steps = [{"key":f"stage_{idx}","agent_id":agent,
              "label":f"Run {agent}","depends_on":[]}
             for idx, agent in enumerate(all_ten)]
    assert len(store.create(title="Ten agents", steps=steps)["steps"]) == 10
    with pytest.raises(WorkflowInputError, match="1–12"):
        validate_steps(steps * 2)


def test_concurrent_bind_only_one_unique_link_wins_and_no_corruption(setup):
    store, inbox = setup
    workflow = store.create(title="Concurrent", steps=[
        {"key":"step","agent_id":"vault","label":"Inspect","depends_on":[]}
    ])
    tasks = [inbox.create("vault","ollama",f"Synthetic task {i}") for i in range(24)]
    def bind(task):
        try:
            return store.bind(workflow["id"],step_key="step",task_id=task["id"],
                              expected_revision=1,inbox=inbox)["revision"]
        except WorkflowConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(bind, tasks))
    assert results.count(2) == 1
    assert results.count("conflict") == 23
    assert store.get(workflow["id"])["revision"] == 2
    with store._connect() as c:
        assert c.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
        assert c.execute("SELECT count(*) FROM operator_workflow_task_links").fetchone()[0] == 1


def test_http_workflow_api_is_guarded_durable_and_never_sends_to_providers(setup, monkeypatch):
    async def run():
        store, inbox = setup
        monkeypatch.setattr(server, "operator_workflows", store)
        monkeypatch.setattr(server, "inbox", inbox)
        h = {"X-Exodia-Client": "exodia-dashboard"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            url = "/api/command/workflows"
            data = {"title":"Local bounded task plan", "steps":plan_steps()}
            assert (await client.post(url,json=data)).status_code == 403
            made = await client.post(url,headers=h,json=data)
            assert made.status_code == 201,made.text
            work = made.json()
            wid = work["id"]
            assert work["step_count"] == 3
            assert len(inbox.list()) == 0
            listed = await client.get(url,headers=h)
            assert listed.status_code == 200
            assert len(listed.json()["workflows"]) == 1
            assert (await client.get(url+"/"+wid,headers=h)).status_code == 200
            assert (await client.get(url+"/nonexistent",headers=h)).status_code == 404
            assert (await client.post(url,headers=h,json={
                "title":"X","steps":[{"key":"x","agent_id":"router","label":"X",
                                     "depends_on":[]}]
            })).status_code == 422
            task_a=inbox.create("archives","ollama","PROMPT_NOT_FOR_NETWORK")
            task_b=inbox.create("strategy","ollama","PROMPT_NO_LEAK")
            delayed=await client.post(url+"/"+wid+"/bind",headers=h,json={
                "step_key":"strategy","task_id":task_b["id"],
                "expected_revision":1
            })
            assert delayed.status_code == 409
            linked=await client.post(url+"/"+wid+"/bind",headers=h,json={
                "step_key":"research","task_id":task_a["id"],
                "expected_revision":1
            })
            assert linked.status_code == 200,linked.text
            assert linked.json()["revision"] == 2
            assert (await client.post(url+"/"+wid+"/review",headers=h,json={
                "expected_revision":2,"confirmation":"APPROVE PUBLISHING"
            })).status_code == 422
            assert (await client.post(url+"/"+wid+"/review",headers=h,json={
                "expected_revision":2,"confirmation":"CONFIRM LOCAL WORKFLOW REVIEW"
            })).status_code == 409
            assert "PROMPT_NOT_FOR_NETWORK" not in linked.text
            assert "PROMPT_NO_LEAK" not in listed.text
            assert linked.json()["external_dispatch_performed"] is False
            assert linked.json()["production_release_enabled"] is False
            assert (await client.post(url+"/"+wid+"/link",headers=h,json={})).status_code == 404
    asyncio.run(run())


def test_multiple_store_instances_serialise_linking_and_leave_no_orphan_rows(setup):
    store, inbox = setup
    one = OperatorWorkflowStore(store.path)
    plan = store.create(title="Multiprocess lock", steps=[
        {"key":"a","agent_id":"vault","label":"Safe shared step","depends_on":[]}
    ])
    tasks = [inbox.create("vault","ollama","Parallel source") for _ in range(16)]
    def attempt(pair):
        instance, task = pair
        try:
            instance.bind(plan["id"], step_key="a", task_id=task["id"],
                          expected_revision=1, inbox=inbox)
            return "linked"
        except WorkflowConflictError:
            return "conflict"
    jobs = [(store if index % 2 else one, task)
            for index, task in enumerate(tasks)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(attempt, jobs))
    assert outcomes.count("linked") == 1
    assert outcomes.count("conflict") == 15
    with sqlite3.connect(store.path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM operator_workflow_task_links"
        ).fetchone()[0] == 1
    assert store.get(plan["id"])["revision"] == 2


def test_operator_console_served_from_existing_local_application(setup):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            result = await client.get("/workflow-planner")
            assert result.status_code == 200
            assert "Operator Workflow Console" in result.text
            assert 'id="stepEditors"' in result.text
            assert "operator_workflow_console.mjs" in result.text
            assert "no model dispatch" in result.text.lower()
            assert "<img" not in result.text
    asyncio.run(run())
