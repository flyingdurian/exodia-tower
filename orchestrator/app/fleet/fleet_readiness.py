"""Phase 11: read-only state-contract readiness across all TEN EXODIA companions.

Never imports, replaces, displays or releases any other companion's frozen
images. The Albedo 33-key registry is a vocabulary contract only, not artwork
to apply across identities. No model provider dispatch or publish action.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = "exodia.phase11.fleet-state-readiness/v1"
POLICY_SCHEMA = "exodia.phase11.fleet-review-rollout/v1"
EXPECTED_IDS = (
    "kiko", "liu_bei", "memory", "archives", "inventory",
    "vault", "ninja", "cache", "strategy", "nova"
)
ACTIVE = frozenset({
    "queued", "cooldown", "opening", "typing", "submitting",
    "running", "researching", "rendering_media",
})
WAITING = frozenset({"waiting_for_reply", "awaiting_operator"})
CANONICAL_LIFECYCLE_STATE = {
    "idle": "neutral",
    "active": "working",
    "waiting": "awaiting_command",
    "completed": "confident",
    "interrupted": "concerned",
    "cancelled": "neutral",
}
ROLLOUT_STATUS = {
    "kiko": "existing_albedo_pipeline_preserved_native_33_release_locked",
    "liu_bei": "a0_intake_unverified_native_33_art_pending",
}


def validate_fleet_policy(root: Path):
    """Load policy + both roster mirrors and fail on identity/release drift."""
    root = Path(root).resolve()
    policy = json.loads(
        (root.parent / "assets/review/fleet/phase11_rollout_policy.json")
        .read_text(encoding="utf-8")
    )
    if (
        policy.get("schema") != POLICY_SCHEMA
        or policy.get("status") != "architecture_only_no_artwork_or_provider_mutation"
        or policy.get("canonical_roster_source")
            != "orchestrator/app/companions/roster.json"
        or policy.get("total_companions") != 10
        or policy.get("states_per_companion") != 33
        or policy.get("planned_contract_slots") != 330
        or policy.get("expressions_per_companion") != 20
        or policy.get("actions_per_companion") != 13
        or policy.get("automatic_art_registration") is not False
        or policy.get("automatic_remote_provider_dispatch") is not False
        or policy.get("automatic_social_publishing") is not False
        or policy.get("production_release_enabled") is not False
        or policy.get("owner_release_authorized") is not False
    ):
        raise ValueError("Fleet release and governance policy drift")

    roster = json.loads((root / "app/companions/roster.json").read_text("utf-8"))
    mirror = json.loads((root / "frontend/companions/roster.json").read_text("utf-8"))
    entries = policy.get("companions")
    if not isinstance(roster, list) or not isinstance(mirror, list) or not isinstance(entries, list):
        raise ValueError("Fleet roster types invalid")
    if any(not isinstance(x, dict) for x in (*roster, *mirror, *entries)):
        raise ValueError("Fleet roster includes malformed entry")
    if (len(roster) != 10 or len(mirror) != 10 or len(entries) != 10
        or tuple(x.get("id") for x in roster) != EXPECTED_IDS
        or tuple(x.get("id") for x in mirror) != EXPECTED_IDS
        or tuple(x.get("agent_id") for x in entries) != EXPECTED_IDS
        or len(set(x.get("id") for x in roster)) != 10):
        raise ValueError("Fleet ten-agent stable identity drift")
    for actual, frontend, agreed in zip(roster, mirror, entries):
        identity = actual["id"]
        frozen = ROLLOUT_STATUS.get(identity, "frozen_existing_companion_art_untouched")
        if (
            actual.get("name") != frontend.get("name")
            or agreed.get("name") != actual.get("name")
            or agreed.get("art_rollout_status") != frozen
            or agreed.get("native_33_production_certified") is not False
            or agreed.get("owner_native_release_approval") is not None
            or agreed.get("production_release_enabled") is not False
            or agreed.get("source_master_replacement_authorized") is not False
        ):
            raise ValueError("Companion art ownership or release policy drift")

    albedo = json.loads(
        (root / "frontend/companions/production/kiko/portrait_registry.json")
        .read_text("utf-8")
    )
    if (albedo.get("schema") != "exodia.portrait-state-registry/v1"
        or albedo.get("character_id") != "kiko"
        or albedo.get("release", {}).get("enabled") is not False
        or not isinstance(albedo.get("states"), dict)
        or len(albedo["states"]) != 33):
        raise ValueError("Albedo production registry or native lock changed")
    canonical = albedo["states"]
    counts = {category: sum(item.get("category") == category
                            for item in canonical.values())
              for category in ("expression", "action")}
    if counts != {"expression": 20, "action": 13}:
        raise ValueError("Shared canonical 20+13 vocabulary changed")
    if not set(CANONICAL_LIFECYCLE_STATE.values()).issubset(canonical):
        raise ValueError("Fleet lifecycle state missing from canonical library")

    liu = json.loads(
        (root.parent / "assets/review/liu_bei_pilot/pilot_manifest.json")
        .read_text("utf-8")
    )
    if (liu.get("character_id") != "liu_bei"
        or liu.get("production_release_enabled") is not False
        or liu.get("native_production_certified") is not False
        or not isinstance(liu.get("states"), dict)
        or set(liu["states"]) != {
            "neutral", "confident", "angered", "working", "pointing"
        }):
        raise ValueError("Liu Bei five-state pilot or production lock changed")
    for record in liu["states"].values():
        if (not isinstance(record, dict)
            or record.get("source_file") is not None
            or record.get("source_sha256") is not None
            or record.get("owner_approval_reference") is not None
            or record.get("status") != "awaiting_native_source"):
            raise ValueError("Unapproved Liu Bei source promotion")
    return roster, entries


def lifecycle(task: dict | None):
    """Only persisted task state; never parse private prompts or provider text."""
    if not task:
        return "idle"
    state = task.get("state")
    if state == "answered":
        return "completed"
    if state in ACTIVE:
        return "active"
    if state in WAITING:
        return "waiting"
    if state == "failed":
        return "interrupted"
    if state == "cancelled":
        return "cancelled"
    return "idle"


def fleet_projection(root: Path, *, selected_agent="kiko", task=None):
    roster, policy = validate_fleet_policy(root)
    if selected_agent not in EXPECTED_IDS:
        raise ValueError("Unknown EXODIA companion")
    if task and task.get("agent_id") != selected_agent:
        raise ValueError("Selected task belongs to another companion")
    stage = lifecycle(task)
    task_id = task.get("id") if task else None
    if task_id is not None and (
        not isinstance(task_id, str) or len(task_id) > 128
        or re.fullmatch(r"[A-Za-z0-9-]+", task_id) is None
    ):
        raise ValueError("Invalid local task identifier")
    companions = []
    for actual, rules in zip(roster, policy):
        ident = actual["id"]
        companions.append({
            "agent_id": ident,
            "name": actual["name"],
            "planned_states": 33,
            "planned_expressions": 20,
            "planned_actions": 13,
            "native_33_production_released": False,
            "art_rollout_status": rules["art_rollout_status"],
            "existing_portrait_workflow_unchanged": True,
            # This review endpoint never serves or registers images even if
            # historical live UI portraits still exist elsewhere.
            "review_asset_url": None,
        })
    return {
        "schema": SCHEMA,
        "read_only": True,
        "scope": "ten_companions_review_contract_not_art_release",
        "selected_agent": selected_agent,
        "task_id": task_id,
        "task_lifecycle": stage,
        "canonical_review_state": CANONICAL_LIFECYCLE_STATE[stage],
        "fleet_count": len(companions),
        "states_per_companion": 33,
        "planned_contract_slots": 330,
        "native_33_production_released_count": 0,
        "companions": companions,
        "automatic_art_registration": False,
        "remote_task_dispatch_performed": False,
        "automatic_social_publishing": False,
        "production_release_enabled": False,
    }
