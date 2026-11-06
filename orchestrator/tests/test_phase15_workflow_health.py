"""Phase 15: persistently grounded multi-agent workflow health, no egress."""
from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.operations.inbox import Inbox
from app.operations.workflow_plans import OperatorWorkflowStore
from app.operations.workflow_health import SCHEMA, workflow_health


@pytest.fixture
def stores(tmp_path):
    return (OperatorWorkflowStore(tmp_path / "operator_workflows.sqlite"),
            Inbox(tmp_path / "tasks.sqlite"))


def test_real_ten_companion_plan_count_and_task_outcome_evidence(stores):
    plan_store,inbox=stores
    agents=("kiko","liu_bei","memory","archives","inventory",
            "vault","ninja","cache","strategy","nova")
    steps=[{"key":f"s{i}","agent_id":a,"label":f"Owned task {i}",
            "depends_on":[]} for i,a in enumerate(agents)]
    plan=plan_store.create(title="Ten identity evidence check",steps=steps)
    revision=1
    linked=[]
    for i, agent in enumerate(agents[:5]):
        task=inbox.create(agent,"ollama","PRIVATE_ORIGINAL_PROMPT")
        plan_store.bind(plan["id"],step_key=f"s{i}",task_id=task["id"],
                        expected_revision=revision,inbox=inbox)
        revision+=1
        linked.append(task)
    inbox.update(linked[0]["id"],"state","answered")
    inbox.update(linked[1]["id"],"state","failed")
    inbox.update(linked[2]["id"],"state","running")
    report=workflow_health(plan_store,inbox)
    assert report["schema"] == SCHEMA
    assert report["status"] == "operational"
    assert report["total_workflow_plans"] == 1
    assert report["total_persisted_task_links"] == 5
    assert report["sampled_workflow_plans"] == 1
    assert report["sampled_step_counts"] == {
        "unlinked":5,"answered":1,"failed":1,"active":3,"unverified":0}
    assert report["remote_dispatch_performed"] is False
    assert report["production_release_enabled"] is False
    assert "PRIVATE_ORIGINAL_PROMPT" not in json.dumps(report)


def test_corrupt_workflow_docs_and_task_links_degrade_health_not_fabricate_success(stores):
    plan_store,inbox=stores
    plan=plan_store.create(title="X",steps=[
        {"key":"inspect","agent_id":"vault","label":"Inspect","depends_on":[]}
    ])
    with sqlite3.connect(plan_store.path) as c:
        c.execute("UPDATE operator_workflows SET document='PRIVATE_UNSAFE_JSON' WHERE id=?",
                  (plan["id"],))
    report=workflow_health(plan_store,inbox)
    assert report["status"] == "review_required"
    assert report["invalid_workflow_documents"] == 1
    assert "PRIVATE_UNSAFE_JSON" not in json.dumps(report)


def test_no_workflows_is_not_reported_as_healthy_running_pipeline(stores):
    plan_store,inbox=stores
    report=workflow_health(plan_store,inbox)
    assert report["status"] == "no_plans"
    assert report["total_workflow_plans"] == 0
    assert report["total_persisted_task_links"] == 0
    assert sum(report["sampled_step_counts"].values()) == 0


def test_100_plan_sample_is_honest_and_fixed_size(stores):
    plan_store,inbox=stores
    for i in range(106):
        plan_store.create(title=f"Plan {i}",steps=[
            {"key":"x","agent_id":"ninja","label":"Verify","depends_on":[]}
        ])
    report=workflow_health(plan_store,inbox)
    assert report["total_workflow_plans"] == 106
    assert report["sampled_workflow_plans"] == 100
    assert report["sample_may_be_incomplete"] is True
    assert report["sampled_step_counts"]["unlinked"] == 100


def test_diagnostics_are_read_only_under_concurrent_sqlite_reads(stores):
    plan_store,inbox=stores
    plan_store.create(title="Health",steps=[
        {"key":"x","agent_id":"vault","label":"Inspect","depends_on":[]}
    ])
    def collect(_):
        return workflow_health(plan_store,inbox)
    with ThreadPoolExecutor(max_workers=8) as pool:
        reports=list(pool.map(collect,range(32)))
    assert all(x["status"]=="operational" and
               x["remote_dispatch_performed"] is False for x in reports)
    assert len(plan_store.list(20))==1
    with sqlite3.connect(plan_store.path) as c:
        assert c.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
