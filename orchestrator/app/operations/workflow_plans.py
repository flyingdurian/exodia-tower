"""Phase 13: durable, dependency-aware *operator-controlled* multi-agent plans.

No models, browser sessions, tools, media or social publishers are executed.
A plan binds EXISTING command tasks after verifying agent ownership. Only actual
answered task states unblock downstream steps; operator review closes a plan,
not a publishing or external-action approval. Prompts/answers are never copied.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

SCHEMA = "exodia.phase13.operator-workflow/v1"
AGENTS = frozenset({
    "kiko", "liu_bei", "memory", "archives", "inventory",
    "vault", "ninja", "cache", "strategy", "nova"
})
STEP_KEY = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class WorkflowInputError(ValueError):
    pass


class WorkflowConflictError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _label(value, limit):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise WorkflowInputError("Workflow label length invalid")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise WorkflowInputError("Workflow label control characters rejected")
    return value.strip()


def validate_steps(steps):
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise WorkflowInputError("Workflow requires 1–12 explicit steps")
    seen = set()
    output = []
    for index, s in enumerate(steps):
        if not isinstance(s, dict) or set(s) != {
            "key", "agent_id", "label", "depends_on"
        }:
            raise WorkflowInputError("Workflow step schema invalid")
        key, agent = s["key"], s["agent_id"]
        deps = s["depends_on"]
        if (not isinstance(key, str) or not STEP_KEY.fullmatch(key)
                or key in seen or agent not in AGENTS
                or not isinstance(deps, list) or len(deps) > 11
                or len(set(deps)) != len(deps)
                or any(not isinstance(d, str) or d not in seen for d in deps)):
            # A dependency must point to an earlier step; cycles and forward
            # references cannot enter the persistent graph.
            raise WorkflowInputError("Invalid, duplicate or cyclic step dependency")
        output.append({
            "key": key, "agent_id": agent,
            "label": _label(s["label"], 80),
            "depends_on": list(deps),
            "linked_task_id": None,
        })
        seen.add(key)
    return output


class OperatorWorkflowStore:
    """Separate additive SQLite store; never changes Inbox or EditorialStore."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""CREATE TABLE IF NOT EXISTS operator_workflows(
                id TEXT PRIMARY KEY, document TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS operator_workflow_task_links(
                task_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL,
                step_key TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_operator_workflows_updated ON operator_workflows(updated_at DESC)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _get(c, ident):
        row = c.execute(
            "SELECT document FROM operator_workflows WHERE id=?", (ident,)
        ).fetchone()
        if row is None:
            raise KeyError("Unknown local workflow plan")
        return json.loads(row[0])

    @staticmethod
    def _save(c, item):
        item["updated_at"] = _now()
        c.execute("UPDATE operator_workflows SET document=?,updated_at=? WHERE id=?",
                  (json.dumps(item, sort_keys=True), item["updated_at"], item["id"]))

    def create(self, *, title: str, steps: list):
        normalized = validate_steps(steps)
        item = {
            "schema": SCHEMA, "id": str(uuid4()), "title": _label(title, 120),
            "revision": 1, "status": "operator_planning",
            "steps": normalized,
            "review_confirmed_at": None,
            "created_at": _now(), "updated_at": _now(),
        }
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT INTO operator_workflows(id,document,updated_at) VALUES(?,?,?)",
                (item["id"], json.dumps(item, sort_keys=True), item["updated_at"])
            )
        return item

    def get(self, ident):
        with self._lock, self._connect() as c:
            return self._get(c, ident)

    def list(self, limit=20):
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            raise WorkflowInputError("Workflow listing limit invalid")
        with self._lock, self._connect() as c:
            rows = c.execute(
                "SELECT document FROM operator_workflows "
                "ORDER BY updated_at DESC,id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def bind(self, ident: str, *, step_key: str, task_id: str,
             expected_revision: int, inbox):
        if (not isinstance(step_key, str) or not STEP_KEY.fullmatch(step_key)
                or not isinstance(task_id, str) or
                not re.fullmatch(r"[A-Za-z0-9-]{1,128}", task_id)
                or not isinstance(expected_revision, int) or
                isinstance(expected_revision, bool) or expected_revision < 1):
            raise WorkflowInputError("Invalid workflow link request")
        with self._lock, self._connect() as c:
            plan = self._get(c, ident)
            step = next((s for s in plan["steps"] if s["key"] == step_key), None)
            if step is None:
                raise WorkflowInputError("Unknown workflow step")
            # Duplicate operator retries are no-ops even with an old revision.
            if step["linked_task_id"] == task_id:
                return plan
            if (plan["status"] != "operator_planning"
                    or plan["revision"] != expected_revision):
                raise WorkflowConflictError("Workflow revision or state changed")
            if step["linked_task_id"] is not None:
                raise WorkflowConflictError("Workflow step already bound")
            predecessors = {s["key"]: s for s in plan["steps"]}
            for dependency in step["depends_on"]:
                linked = predecessors[dependency]["linked_task_id"]
                if linked is None or inbox.get(linked)["state"] != "answered":
                    raise WorkflowConflictError("A dependency is not answered")
            try:
                task = inbox.get(task_id)
            except KeyError:
                raise WorkflowInputError("Unknown local task")
            if task["agent_id"] != step["agent_id"]:
                raise WorkflowConflictError("Companion assignment mismatch")
            if task["state"] in {"failed", "cancelled"}:
                raise WorkflowConflictError("Terminal unsuccessful task cannot be bound")
            if c.execute(
                "SELECT task_id FROM operator_workflow_task_links WHERE task_id=?",
                (task_id,)
            ).fetchone():
                raise WorkflowConflictError("Task already assigned to a workflow")
            c.execute(
                "INSERT INTO operator_workflow_task_links(task_id,workflow_id,step_key)"
                " VALUES(?,?,?)", (task_id, ident, step_key)
            )
            step["linked_task_id"] = task_id
            plan["revision"] += 1
            self._save(c, plan)
            return plan

    def confirm_review(self, ident: str, *, expected_revision: int,
                       confirmation: str, inbox):
        if confirmation != "CONFIRM LOCAL WORKFLOW REVIEW":
            raise WorkflowInputError("Explicit local review confirmation required")
        if (not isinstance(expected_revision, int) or
                isinstance(expected_revision, bool) or expected_revision < 1):
            raise WorkflowInputError("Invalid review revision")
        with self._lock, self._connect() as c:
            plan = self._get(c, ident)
            if plan["status"] == "reviewed_local_only":
                return plan
            if plan["status"] != "operator_planning" or plan["revision"] != expected_revision:
                raise WorkflowConflictError("Workflow revision changed")
            if any(
                s["linked_task_id"] is None
                or inbox.get(s["linked_task_id"])["state"] != "answered"
                for s in plan["steps"]
            ):
                raise WorkflowConflictError("All linked tasks must have answered")
            plan["revision"] += 1
            plan["status"] = "reviewed_local_only"
            plan["review_confirmed_at"] = _now()
            self._save(c, plan)
            return plan


def project_plan(plan: dict, inbox) -> dict:
    """Safe projection uses real persisted task states, never their contents."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise WorkflowInputError("Invalid stored workflow plan")
    outcomes = {}
    steps = []
    complete = 0
    for s in plan["steps"]:
        linked = s["linked_task_id"]
        state = None if linked is None else inbox.get(linked)["state"]
        if state == "answered":
            status = "answered_pending_review"
            complete += 1
        elif state in {"failed", "cancelled"}:
            status = "linked_task_failed"
        elif linked:
            status = "linked_task_in_progress"
        elif any(outcomes.get(key) != "answered_pending_review"
                 for key in s["depends_on"]):
            status = "blocked_on_dependencies"
        else:
            status = "ready_for_operator_link"
        outcomes[s["key"]] = status
        steps.append({
            "key": s["key"], "label": s["label"],
            "agent_id": s["agent_id"], "depends_on": s["depends_on"],
            "linked_task_id": linked, "status": status,
        })
    return {
        "schema": SCHEMA,
        "id": plan["id"], "title": plan["title"], "revision": plan["revision"],
        "status": plan["status"], "steps": steps,
        "completed_task_count": complete, "step_count": len(steps),
        "operator_review_confirmed": plan["status"] == "reviewed_local_only",
        "external_dispatch_performed": False,
        "social_publishing_performed": False,
        "production_release_enabled": False,
    }
