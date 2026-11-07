"""Phase 15: bounded local multi-agent operations pulse.

Read-only SQLite evidence for the existing Phase 13 operator workflow DAGs.
Aggregates *actual persisted* step links and live Inbox lifecycle without
sending prompts, creating tasks, modifying art or treating approval as dispatch.
Outputs only approved status codes, identifiers and aggregate counts; never
returns plan titles, user text, provider replies or local filesystem paths.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.operations.workflow_plans import SCHEMA as PLAN_SCHEMA, AGENTS

SCHEMA = "exodia.phase15.operator-workflow-health/v1"
MAX_SAMPLED_PLANS = 100
ACTIVE = frozenset({
    "draft", "queued", "cooldown", "opening", "typing", "submitting",
    "running", "researching", "waiting_for_reply", "rendering_media",
    "awaiting_operator",
})
CATEGORIES = ("unlinked", "answered", "failed", "active", "unverified")


def workflow_health(store, inbox) -> dict:
    """Validate stored docs and corroborate task state without raw content."""
    db = Path(store.path)
    if db.is_symlink() or not db.is_file():
        raise ValueError("Unsafe workflow database")
    # A read-only connection cannot trigger schema migrations or checkpoint
    # unrelated connections. Never use the live workflow store's _connect()
    # for diagnostics, because the SQLite open mode must remain explicit.
    with sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro",uri=True,timeout=5) as conn:
        check = conn.execute("PRAGMA quick_check(1)").fetchone()
        if not check or check[0] != "ok":
            raise ValueError("Workflow SQLite integrity failed")
        total = conn.execute("SELECT COUNT(*) FROM operator_workflows").fetchone()[0]
        total_links = conn.execute(
            "SELECT COUNT(*) FROM operator_workflow_task_links"
        ).fetchone()[0]
        records = conn.execute(
            "SELECT document FROM operator_workflows "
            "ORDER BY updated_at DESC,id DESC LIMIT ?",
            (MAX_SAMPLED_PLANS,)
        ).fetchall()
    counts = {key: 0 for key in CATEGORIES}
    plans_reviewed = 0
    invalid = 0
    for (raw,) in records:
        try:
            plan = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            invalid += 1
            continue
        if (not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA
            or plan.get("status") not in
              {"operator_planning", "reviewed_local_only"}
            or not isinstance(plan.get("steps"), list)
            or not 1 <= len(plan["steps"]) <= 12):
            invalid += 1
            continue
        if plan["status"] == "reviewed_local_only":
            plans_reviewed += 1
        seen = set()
        for item in plan["steps"]:
            if (not isinstance(item, dict)
                or not isinstance(item.get("key"), str)
                or item["key"] in seen
                or item.get("agent_id") not in AGENTS):
                invalid += 1
                break
            seen.add(item["key"])
            linked = item.get("linked_task_id")
            if linked is None:
                counts["unlinked"] += 1
                continue
            if not isinstance(linked, str):
                counts["unverified"] += 1
                continue
            try:
                task = inbox.get(linked)
            except (KeyError, ValueError):
                counts["unverified"] += 1
                continue
            if task.get("agent_id") != item["agent_id"]:
                counts["unverified"] += 1
            elif task.get("state") == "answered":
                counts["answered"] += 1
            elif task.get("state") in {"failed", "cancelled"}:
                counts["failed"] += 1
            elif task.get("state") in ACTIVE:
                counts["active"] += 1
            else:
                counts["unverified"] += 1

    # Invalid docs are a *blocker* rather than a background "0 errors".
    status = ("review_required" if invalid or counts["unverified"]
              else "operational" if total else "no_plans")
    return {
        "schema": SCHEMA,
        "read_only": True,
        "status": status,
        "total_workflow_plans": total,
        "total_persisted_task_links": total_links,
        "sampled_workflow_plans": len(records),
        "sample_limit": MAX_SAMPLED_PLANS,
        "sample_may_be_incomplete": total > len(records),
        "invalid_workflow_documents": invalid,
        "sampled_reviewed_plans": plans_reviewed,
        "sampled_step_counts": counts,
        "production_release_enabled": False,
        "remote_dispatch_performed": False,
        "social_publishing_performed": False,
        "authenticated_provider_acceptance": "not_established",
    }
