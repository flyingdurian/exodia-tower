"""Liu Bei (liu_bei) five-state REVIEW ONLY runtime projection.

The existing poster is a style reference, not a native source. This module
never registers artwork, fabricates approval receipts or changes the production
portrait registry. It can drive a truthful pending-art fallback in the actual
EXODIA command center when Liu Bei is selected.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.fleet.liu_bei_preflight import LIU_BEI_ID, PILOT_STATES, liu_bei_a0_preflight

SCHEMA = "exodia.phase7.liu_bei-five-state-review/v1"
STATES = {
    "neutral": {"category": "expression", "behavior": "Idle readiness"},
    "confident": {"category": "expression", "behavior": "Decisive gaze"},
    "angered": {"category": "expression", "behavior": "Blocked-route frustration"},
    "working": {"category": "action", "behavior": "Active route planning"},
    "pointing": {"category": "action", "behavior": "Connected directional gesture"},
}
ACTIVE = frozenset({
    "queued", "cooldown", "opening", "typing", "submitting",
    "waiting_for_reply", "researching", "running", "rendering_media"
})


def desired_state(task=None, *, manual_preview=None):
    """Never infer blocked-route anger or pointing from a generic failure."""
    if manual_preview is not None:
        if manual_preview not in STATES:
            raise ValueError("Unknown Liu Bei review state")
        return manual_preview, "explicit_review_preview"
    if not task:
        return "neutral", "no_selected_liu_bei_task"
    if task.get("agent_id") != LIU_BEI_ID:
        raise ValueError("Selected task is not owned by Liu Bei")
    state = task.get("state")
    metrics = task.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    # These are explicit, safely structured future task signals. No parser
    # guesses intent from private prompt/answer text or provider exceptions.
    if state in ACTIVE and metrics.get("route_gesture") == "pointing":
        return "pointing", "explicit_route_gesture"
    if state == "failed" and metrics.get("route_blocked") is True:
        return "angered", "explicit_blocked_route"
    if state == "answered":
        return "confident", "completed_liu_bei_task"
    if state in ACTIVE:
        return "working", "active_liu_bei_task"
    return "neutral", "idle_or_uncertified_routing_state"


def runtime_projection(root: Path, *, task=None, manual_preview=None):
    """Strict source-lock preflight + task-dliu_bei fallback, never image serving."""
    # The preflight public projection deliberately returns locked release
    # flags; verify the underlying immutable pilot manifest independently.
    root = Path(root).resolve()
    manifest = json.loads((root.parent / "assets/review/liu_bei_pilot/pilot_manifest.json").read_text("utf-8"))
    if (manifest.get("production_release_enabled") is not False or
        manifest.get("native_production_certified") is not False):
        raise ValueError("Liu Bei production release requires separate owner authorization")
    preflight = liu_bei_a0_preflight(root)
    names = tuple(preflight["pilot_states"][i]["state"] for i in range(len(PILOT_STATES)))
    if names != PILOT_STATES:
        raise ValueError("Liu Bei pilot manifest order is not canonical")
    state, reason = desired_state(task, manual_preview=manual_preview)
    if preflight["production_release_enabled"] is not False or preflight["native_production_certified"] is not False:
        raise ValueError("Liu Bei art release contract changed")
    return {
        "schema": SCHEMA,
        "character_id": LIU_BEI_ID,
        "character_name": "Liu Bei",
        "selected_state": state,
        "state_reason": reason,
        "review_preview": manual_preview is not None,
        "task_id": task.get("id") if task else None,
        "task_state": task.get("state") if task else "idle",
        "native_a0_intake": {
            "status": preflight["intake_status"],
            "technical_source_pass": preflight["technical_source_pass"],
            "image_bound_annotation_consistency": preflight["image_bound_annotation_consistency"],
        },
        "states": [
            {"key": name, **STATES[name], "art_status": "awaiting_exact_sha_owner_approval",
             "asset_url": None, "fallback": "NATIVE LIU_BEI ART PENDING"}
            for name in PILOT_STATES
        ],
        "display": {
            "mode": "review_only_fallback",
            "asset_url": None,
            "placeholder_kind": "typographic_status_not_character_art",
            "status": "Five native Liu Bei states are awaiting owner-approved sources",
            "current_behavior": STATES[state]["behavior"],
        },
        "independent_original_authorship_verified": False,
        "owner_identity_approval": "pending",
        "five_state_pilot": "locked_pending_exact_sha_owner_approval",
        "production_release_enabled": False,
    }
