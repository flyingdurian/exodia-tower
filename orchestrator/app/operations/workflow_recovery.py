"""Phase 16 — operator-confirmed local recovery forks for immutable DAG plans.

A failed/locally reviewed multi-agent workflow can be copied into a *new*
unlinked DAG without reusing task IDs, prompts, responses, approvals, providers,
browser sessions, artwork or publishing permissions. No tasks are created.
One fork per source revision is idempotent, including across SQLite processes.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from app.operations.workflow_plans import (
    SCHEMA as WORKFLOW_SCHEMA, WorkflowConflictError, WorkflowInputError,
    validate_steps, project_plan,
)

SCHEMA = "exodia.phase16.local-workflow-recovery/v1"
CONFIRMATION = "CREATE LOCAL RECOVERY PLAN"
_ID = re.compile(r"^[a-zA-Z0-9-]{1,128}$")


def _now():
    return datetime.now(timezone.utc).isoformat()


class WorkflowRecovery:
    def __init__(self, store):
        self.store = store
        with store._lock, store._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS operator_workflow_recovery(
                source_workflow_id TEXT NOT NULL,
                source_revision INTEGER NOT NULL,
                new_workflow_id TEXT NOT NULL UNIQUE,
                reason_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(source_workflow_id,source_revision)
            )""")

    @staticmethod
    def _verify_source(plan, inbox):
        if (not isinstance(plan, dict) or plan.get("schema") != WORKFLOW_SCHEMA
                or plan.get("status") not in {
                    "operator_planning", "reviewed_local_only"
                }):
            raise WorkflowInputError("Invalid recovery source plan")
        steps = plan.get("steps")
        if not isinstance(steps, list):
            raise WorkflowInputError("Invalid source steps")
        # This re-validates graph acyclicity, stable companion identities and
        # author-authored labels before allowing a copy into an active store.
        graph = validate_steps([{
            "key": s["key"], "label": s["label"],
            "agent_id": s["agent_id"], "depends_on": s["depends_on"]
        } for s in steps])
        fail_count = 0
        for step in steps:
            linked = step.get("linked_task_id")
            if linked is None:
                continue
            if not isinstance(linked, str) or not _ID.fullmatch(linked):
                raise WorkflowInputError("Invalid linked task ID")
            try:
                task = inbox.get(linked)
            except KeyError:
                raise WorkflowConflictError("Source task no longer exists")
            if task.get("agent_id") != step["agent_id"]:
                raise WorkflowConflictError("Source task ownership changed")
            fail_count += task.get("state") in {"failed", "cancelled"}
        if fail_count:
            reason = "linked_task_failed"
        elif plan["status"] == "reviewed_local_only":
            # Reviewing a completed local DAG is not publishing or provider
            # acceptance; a fresh plan is still an explicit operator decision.
            reason = "reviewed_plan_revision"
        else:
            raise WorkflowConflictError("Recovery requires a failed task or reviewed local plan")
        return graph, reason

    def fork(self, workflow_id, *, expected_revision, confirmation, inbox):
        if confirmation != CONFIRMATION:
            raise WorkflowInputError("Explicit local recovery confirmation required")
        if (not isinstance(workflow_id, str) or not _ID.fullmatch(workflow_id)
                or type(expected_revision) is not int or expected_revision < 1):
            raise WorkflowInputError("Invalid recovery identifier or revision")
        with self.store._lock, self.store._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            source = self.store._get(conn, workflow_id)
            if source.get("revision") != expected_revision:
                raise WorkflowConflictError("Recovery source revision changed")
            graph, reason = self._verify_source(source, inbox)
            prior = conn.execute(
                "SELECT new_workflow_id FROM operator_workflow_recovery "
                "WHERE source_workflow_id=? AND source_revision=?",
                (workflow_id, expected_revision)
            ).fetchone()
            if prior:
                existing = self.store._get(conn, prior[0])
                return existing, self.lineage_record(
                    workflow_id, expected_revision, prior[0], reason)
            name = "Recovery: " + str(source["title"])[:110]
            now = _now()
            created = {
                "schema": WORKFLOW_SCHEMA,
                "id": str(uuid4()),
                "title": name,
                "revision": 1,
                "status": "operator_planning",
                "steps": graph,
                "review_confirmed_at": None,
                "created_at": now,
                "updated_at": now,
            }
            conn.execute(
                "INSERT INTO operator_workflows(id,document,updated_at) VALUES(?,?,?)",
                (created["id"], json.dumps(created, sort_keys=True), now)
            )
            conn.execute(
                "INSERT INTO operator_workflow_recovery "
                "(source_workflow_id,source_revision,new_workflow_id,reason_code,created_at) "
                "VALUES(?,?,?,?,?)",
                (workflow_id, expected_revision, created["id"], reason, now)
            )
            return created, self.lineage_record(
                workflow_id, expected_revision, created["id"], reason)

    @staticmethod
    def lineage_record(source, revision, fork_id, reason):
        return {
            "schema": SCHEMA,
            "source_workflow_id": source,
            "source_revision": revision,
            "recovery_workflow_id": fork_id,
            "reason_code": reason,
            "source_unmodified": True,
            "copied_task_id_count": 0,
            "remote_dispatch_performed": False,
            "production_release_enabled": False,
            "social_publishing_performed": False,
            "artwork_registration_performed": False,
        }


def safe_fork_result(store, recovery, workflow_id, expected_revision,
                     confirmation, inbox):
    """Operator-facing projection never contains prompt/reply text."""
    created, proof = recovery.fork(
        workflow_id, expected_revision=expected_revision,
        confirmation=confirmation, inbox=inbox)
    view = project_plan(created, inbox)
    if (view["completed_task_count"] != 0
            or any(step["linked_task_id"] is not None for step in view["steps"])
            or view["operator_review_confirmed"] is not False):
        raise WorkflowConflictError("Recovery fork carries prohibited approval/task links")
    return {"schema": SCHEMA, "workflow": view, "lineage": proof}
