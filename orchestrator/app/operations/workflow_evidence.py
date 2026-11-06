"""Phase 14: local operator DAG execution evidence and safe next-step guidance.

Read-only evidence over the existing Phase 13 workflow store and Inbox.
No task creation, provider dispatch, automatic approvals, browser actions or
portrait mutations. An answered Inbox state is not authenticated-provider
acceptance; evidence preserves that explicit distinction.
"""
from __future__ import annotations

import re
from typing import Any

from app.operations.workflow_plans import AGENTS, SCHEMA as PLAN_SCHEMA, project_plan

SCHEMA = "exodia.phase14.workflow-task-evidence/v1"
ALLOWED = frozenset({
    "ready_for_operator_link", "blocked_on_dependencies",
    "linked_task_in_progress", "answered_pending_review", "linked_task_failed"
})
_SAFE_TASK = re.compile(r"^[A-Za-z0-9-]{1,128}$")


class WorkflowEvidenceError(ValueError):
    """A stored plan or task record cannot pass the immutable evidence policy."""


def collect_workflow_evidence(plan: dict, inbox) -> dict:
    """Independent per-step Inbox-event corroboration; no private task text."""
    if (not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA
            or plan.get("status") not in {"operator_planning", "reviewed_local_only"}):
        raise WorkflowEvidenceError("Invalid persisted operator plan")
    summary = project_plan(plan, inbox)
    if (summary.get("schema") != PLAN_SCHEMA or
        summary.get("external_dispatch_performed") is not False or
        summary.get("social_publishing_performed") is not False or
        summary.get("production_release_enabled") is not False):
        raise WorkflowEvidenceError("Operator review policy drift")
    steps = summary.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise WorkflowEvidenceError("Invalid workflow step count")

    evidence_steps = []
    answered_count = 0
    event_confirmed_count = 0
    ready_count = 0
    failures = 0
    for step in steps:
        key = step.get("key")
        owner = step.get("agent_id")
        status = step.get("status")
        task_id = step.get("linked_task_id")
        if (not isinstance(key, str) or
            not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", key)
            or owner not in AGENTS or status not in ALLOWED
            or (task_id is not None and
                (not isinstance(task_id, str) or
                 _SAFE_TASK.fullmatch(task_id) is None))):
            raise WorkflowEvidenceError("Unknown task/step evidence")
        proof = "no_linked_task"
        history_state = "unlinked"
        last_event_type = None
        if task_id is not None:
            task = inbox.get(task_id)
            if task.get("agent_id") != owner:
                raise WorkflowEvidenceError("Linked task owner drift")
            state = task.get("state")
            if status == "answered_pending_review":
                if state != "answered":
                    raise WorkflowEvidenceError("Answered projection contradicted by task")
                answered_count += 1
            history = inbox.events(task_id, limit=500)
            # Preserve uncertainty if history was truncated and the terminal
            # event is not visible; never manufacture a successful event.
            terminal_events = [
                evt for evt in history if evt.get("to_state") == "answered"
                and evt.get("event") in {"state_change", "legacy_snapshot"}
            ]
            if state == "answered":
                if terminal_events:
                    proof = "answered_event_recorded"
                    last_event_type = terminal_events[-1]["event"]
                    event_confirmed_count += 1
                else:
                    proof = "answered_without_event_proof"
                history_state = "answered"
            elif state in {"failed", "cancelled"}:
                proof = "terminal_unsuccessful"
                history_state = "terminal_unsuccessful"
            elif state in {"draft", "queued", "cooldown", "opening", "typing",
                           "submitting", "running", "researching",
                           "waiting_for_reply", "rendering_media",
                           "awaiting_operator"}:
                proof = "task_active_or_draft"
                history_state = "in_progress"
            else:
                proof = "unknown_task_state"
                history_state = "unverified"
        if status == "ready_for_operator_link":
            ready_count += 1
        if status == "linked_task_failed":
            failures += 1
        evidence_steps.append({
            "key": key, "agent_id": owner, "task_id": task_id,
            "step_status": status, "task_lifecycle": history_state,
            "audit_evidence": proof, "answer_event_kind": last_event_type,
            "provider_authentication_verified": False,
            "owner_external_action_approval": False,
        })
    if answered_count != summary["completed_task_count"]:
        raise WorkflowEvidenceError("Task completion count drift")
    return {
        "schema": SCHEMA,
        "workflow_id": summary["id"],
        "revision": summary["revision"],
        "workflow_status": summary["status"],
        "step_count": len(evidence_steps),
        "answered_task_count": answered_count,
        "answered_event_recorded_count": event_confirmed_count,
        "operator_link_ready_count": ready_count,
        "failed_linked_task_count": failures,
        "operator_review_confirmed": summary["operator_review_confirmed"],
        "all_tasks_answered": answered_count == len(evidence_steps),
        "all_answered_events_corroborrated": (
            event_confirmed_count == len(evidence_steps)
        ),
        "steps": evidence_steps,
        "next_operator_action": (
            "inspect_failed_tasks_and_create_new_plan" if failures
            else "link_existing_tasks_manually" if ready_count
            else "await_existing_task_results" if answered_count < len(evidence_steps)
            else "confirm_or_inspect_local_review"
        ),
        "authenticated_provider_acceptance": "not_established",
        "external_dispatch_performed": False,
        "social_publishing_performed": False,
        "production_release_enabled": False,
        "read_only": True,
    }
