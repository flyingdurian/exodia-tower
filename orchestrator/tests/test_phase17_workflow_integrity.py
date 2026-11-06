"""Phase 17: verify DAG/index ownership, restart and recovery integrity."""
from __future__ import annotations
import asyncio
import json
import sqlite3
import httpx
import pytest
from app.api import server
from app.operations.inbox import Inbox
from app.operations.workflow_plans import OperatorWorkflowStore
from app.operations.workflow_recovery import WorkflowRecovery, CONFIRMATION
from app.operations.workflow_integrity import audit_workflows, SCHEMA


@pytest.fixture
def stores(tmp_path):
    store=OperatorWorkflowStore(tmp_path/"operator_workflows.sqlite")
    inbox=Inbox(tmp_path/"tasks.sqlite")
    return store,inbox


def one_step(store,owner="vault"):
    return store.create(title="TOP_SECRET_INTERNAL_PLAN",steps=[
        {"key":"inspect","agent_id":owner,
         "label":"PRIVATE_OPERATOR_STAGE","depends_on":[]}])


def test_clean_workflow_and_recovery_fork_both_pass_read_only_audit(stores):
    store,inbox=stores
    plan=one_step(store)
    t=inbox.create("vault","ollama","PRIVATE_TASK_DO_NOT_LEAK")
    store.bind(plan["id"],step_key="inspect",task_id=t["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(t["id"],"state","failed")
    recovery=WorkflowRecovery(store)
    new,proof=recovery.fork(plan["id"],expected_revision=2,
                            confirmation=CONFIRMATION,inbox=inbox)
    result=audit_workflows(store,inbox)
    assert result["schema"]==SCHEMA
    assert result["status"]=="sample_consistent"
    assert result["total_plans"]==2
    assert result["total_task_links"]==1
    assert result["total_recovery_forks"]==1
    assert result["total_failures"]==0
    assert result["sampling_incomplete"] is False
    assert result["external_dispatch_performed"] is False
    assert result["social_publishing_performed"] is False
    assert result["native_art_approved"] is False
    assert result["production_release_enabled"] is False
    assert "TOP_SECRET_INTERNAL_PLAN" not in json.dumps(result)
    assert "PRIVATE_TASK_DO_NOT_LEAK" not in json.dumps(result)


def test_missing_link_index_fails_closed_with_redacted_count(stores):
    store,inbox=stores
    plan=one_step(store)
    task=inbox.create("vault","ollama","SENSITIVE")
    store.bind(plan["id"],step_key="inspect",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    with sqlite3.connect(store.path) as db:
        db.execute("DELETE FROM operator_workflow_task_links WHERE task_id=?",
                   (task["id"],))
    result=audit_workflows(store,inbox)
    assert result["status"]=="requires_operator_review"
    assert result["failure_counts"]["link_index_mismatch"]>=1
    assert result["owner_review_required"] is True
    assert task["id"] not in json.dumps(result)


def test_orphan_index_link_and_forged_owner_are_detected(stores):
    store,inbox=stores
    plan=one_step(store)
    task=inbox.create("ninja","ollama","PRIVATE_NINJA_PROMPT")
    with sqlite3.connect(store.path) as db:
        db.execute(
            "INSERT INTO operator_workflow_task_links VALUES(?,?,?)",
            (task["id"],"missing-workflow","inspect"))
    failed=audit_workflows(store,inbox)
    assert failed["failure_counts"]["orphan_link"]==1
    with sqlite3.connect(store.path) as db:
        db.execute("DELETE FROM operator_workflow_task_links")
        doc=store.get(plan["id"])
        doc["steps"][0]["linked_task_id"]=task["id"]
        db.execute("UPDATE operator_workflows SET document=? WHERE id=?",
                   (json.dumps(doc),plan["id"]))
        db.execute("INSERT INTO operator_workflow_task_links VALUES(?,?,?)",
                   (task["id"],plan["id"],"inspect"))
    failed=audit_workflows(store,inbox)
    assert failed["failure_counts"]["owner_mismatch"]==1


def test_fake_reviewed_status_and_invalid_dag_do_not_report_integrity(stores):
    store,inbox=stores
    plan=one_step(store)
    task=inbox.create("vault","ollama","SENSITIVE")
    store.bind(plan["id"],step_key="inspect",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    with sqlite3.connect(store.path) as db:
        doc=store.get(plan["id"])
        doc["status"]="reviewed_local_only"
        db.execute("UPDATE operator_workflows SET document=? WHERE id=?",
                   (json.dumps(doc),plan["id"]))
    result=audit_workflows(store,inbox)
    assert result["failure_counts"]["review_drift"]>0
    with sqlite3.connect(store.path) as db:
        doc["steps"][0]["depends_on"]=["inspect"]
        db.execute("UPDATE operator_workflows SET document=? WHERE id=?",
                   (json.dumps(doc),plan["id"]))
    result=audit_workflows(store,inbox)
    assert result["failure_counts"]["invalid_document"]>0


def test_bad_lineage_rejected_without_mutating_original(stores):
    store,inbox=stores
    plan=one_step(store)
    task=inbox.create("vault","ollama","PRIVATE")
    store.bind(plan["id"],step_key="inspect",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(task["id"],"state","failed")
    recovery=WorkflowRecovery(store)
    fork,_=recovery.fork(plan["id"],expected_revision=2,
                         confirmation=CONFIRMATION,inbox=inbox)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE operator_workflow_recovery SET reason_code='published'")
    result=audit_workflows(store,inbox)
    assert result["failure_counts"]["invalid_lineage"]==1


def test_bounded_sample_never_claims_a_complete_integrity_audit(stores):
    store,inbox=stores
    for i in range(103):
        store.create(title=f"Plan {i}",steps=[
            {"key":"stage","agent_id":"vault","label":"Plan","depends_on":[]}])
    result=audit_workflows(store,inbox)
    assert result["total_plans"]==103
    assert result["sampled_plans"]==100
    assert result["status"]=="partial_sample"
    assert result["sampling_incomplete"] is True
    assert result["owner_review_required"] is True


def test_http_integrity_gate_requires_local_header_no_mutation(monkeypatch,stores):
    async def run():
        store,inbox=stores
        monkeypatch.setattr(server,"operator_workflows",store)
        monkeypatch.setattr(server,"inbox",inbox)
        one_step(store)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver") as client:
            url="/api/operations/workflow-integrity"
            assert (await client.get(url)).status_code==403
            result=await client.get(url,headers={
                "X-Exodia-Client":"exodia-dashboard"})
            assert result.status_code==200,result.text
            data=result.json()
            assert data["status"]=="sample_consistent"
            assert data["production_release_enabled"] is False
            assert "TOP_SECRET_INTERNAL_PLAN" not in result.text
            assert (await client.post(url,headers={
                "X-Exodia-Client":"exodia-dashboard"})).status_code==405
    asyncio.run(run())


def test_private_recovery_snapshot_includes_workflow_lineage_and_task_state(tmp_path):
    from tools.phase12_local_backup import backup_local
    root=tmp_path/"orchestrator"
    data=root/"app_data"
    data.mkdir(parents=True)
    store=OperatorWorkflowStore(data/"operator_workflows.sqlite")
    inbox=Inbox(data/"companion_tasks.sqlite")
    plan=one_step(store)
    task=inbox.create("vault","ollama","PRIVATE_DO_NOT_EXPORT")
    store.bind(plan["id"],step_key="inspect",task_id=task["id"],
               expected_revision=1,inbox=inbox)
    inbox.update(task["id"],"state","failed")
    recovery=WorkflowRecovery(store)
    recovery.fork(plan["id"],expected_revision=2,
                  confirmation=CONFIRMATION,inbox=inbox)
    report=backup_local(root,confirmed=True)
    assert "operator_workflows.sqlite" in report["databases_snapshotted"]
    assert "companion_tasks.sqlite" in report["databases_snapshotted"]
    assert report["network_upload_performed"] is False
    assert report["snapshots_private_unencrypted"] is True
    assert report["cross_database_atomic_snapshot"] is False
    assert "PRIVATE_DO_NOT_EXPORT" not in json.dumps(report)
    backup_dir=data/"phase12_private_backups"
    snap=next(backup_dir.glob("operator_workflows-*.sqlite"))
    with sqlite3.connect(snap) as conn:
        assert conn.execute("PRAGMA quick_check(1)").fetchone()==("ok",)
        assert conn.execute("SELECT COUNT(*) FROM operator_workflows").fetchone()[0]==2
        assert conn.execute(
            "SELECT COUNT(*) FROM operator_workflow_recovery").fetchone()[0]==1
