"""Phase 10: canonical 33-state *review-only* Liu Bei runtime contract.

There is no art synthesis, production registry import, approval, permission
change or provider dispatch. The historical Albedo registry supplies the
immutable 20-expression/13-action *vocabulary*, never Albedo pixels or identity.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.fleet.liu_bei_runtime import runtime_projection

SCHEMA = "exodia.phase10.liu-bei-33-review/v1"
MANIFEST_SCHEMA = "exodia.phase10.liu-bei-33-review-registry/v1"
EXPECTED_EXPRESSION_COUNT = 20
EXPECTED_ACTION_COUNT = 13
EXPECTED_TOTAL = 33

def validate_library(root: Path) -> tuple[dict, tuple[str, ...]]:
    root = Path(root).resolve()
    expected_path = "orchestrator/frontend/companions/production/kiko/portrait_registry.json"
    manifest = json.loads(
        (root.parent / "assets/review/liu_bei_pilot/phase10_33_state_registry.json")
        .read_text(encoding="utf-8")
    )
    albedo = json.loads(
        (root / "frontend/companions/production/kiko/portrait_registry.json")
        .read_text(encoding="utf-8")
    )
    if (manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("character_id") != "liu_bei"
        or manifest.get("status") != "architecture_only_artwork_pending"
        or manifest.get("canonical_vocab_source") != expected_path
        or manifest.get("native_canvas") != [1536, 1920]
        or manifest.get("planned_count") != EXPECTED_TOTAL
        or manifest.get("expression_count") != EXPECTED_EXPRESSION_COUNT
        or manifest.get("action_count") != EXPECTED_ACTION_COUNT
        or manifest.get("automatic_native_registration") is not False
        or manifest.get("production_release_enabled") is not False
        or manifest.get("owner_production_approval") is not None
        or manifest.get("identity_reference_kind") !=
            "liu_bei_a0_original_sha_and_native_file_have_separate_identity"):
        raise ValueError("Phase 10 immutable source and release policy drift")
    anchors = manifest.get("anchors")
    if anchors != {
        "iris_midline_y": 633.6,
        "shoulder_baseline_y": 980,
        "head_width": 614.4,
        "head_center_x": 768,
    }:
        raise ValueError("Phase 10 portrait geometry policy drift")
    if (albedo.get("schema") != "exodia.portrait-state-registry/v1"
        or albedo.get("character_id") != "kiko"
        or albedo.get("release", {}).get("enabled") is not False):
        raise ValueError("Canonical reference registry changed or released")
    vocabulary = albedo.get("states")
    states = manifest.get("states")
    if (not isinstance(vocabulary, dict) or not isinstance(states, list)
        or len(vocabulary) != EXPECTED_TOTAL or len(states) != EXPECTED_TOTAL):
        raise ValueError("Phase 10 canonical 33-state shape changed")
    keys = tuple(vocabulary)
    if len(set(keys)) != EXPECTED_TOTAL:
        raise ValueError("Duplicate canonical state name")
    counts = {"expression": 0, "action": 0}
    for item, (name, reference) in zip(states, vocabulary.items()):
        if (not isinstance(item, dict) or not isinstance(reference, dict)
            or item.get("key") != name
            or item.get("label") != reference.get("label")
            or item.get("category") != reference.get("category")
            or item.get("signal_overlay") != reference.get("signal_overlay")
            or item.get("source_file") is not None
            or item.get("source_sha256") is not None
            or item.get("landmark_evidence") is not None
            or item.get("owner_approval_reference") is not None
            or item.get("asset_url") is not None
            or item.get("source_status") != "awaiting_independent_native_source"
            or item.get("art_status") != "not_production_certified"):
            raise ValueError("Unapproved 33-state art, provenance or vocabulary drift")
        if item["category"] not in counts:
            raise ValueError("Unknown native state category")
        counts[item["category"]] += 1
    if counts != {"expression": EXPECTED_EXPRESSION_COUNT,
                  "action": EXPECTED_ACTION_COUNT}:
        raise ValueError("Canonical 20+13 categories drift")
    if not {"neutral", "confident", "angered", "working", "pointing"}.issubset(keys):
        raise ValueError("Phase 7 five-state compatibility lost")
    return manifest, keys


def phase10_projection(root: Path, *, task=None, preview_state=None) -> dict:
    """Review projections only: all 33 states are pending distinct native art."""
    manifest, keys = validate_library(root)
    # Independent Phase 7 native A0/pilot preflight and exact task ownership
    # remain authoritative. This check happens *even for manual preview*.
    base = runtime_projection(root, task=task)
    if (base.get("production_release_enabled") is not False
        or base.get("display", {}).get("asset_url") is not None
        or base.get("owner_identity_approval") != "pending"):
        raise ValueError("Phase 10 tried to bypass Phase 7 lock")
    if preview_state is not None and preview_state not in keys:
        raise ValueError("Unsupported canonical Liu Bei review state")
    selected = preview_state or base["selected_state"]
    return {
        "schema": SCHEMA,
        "character_id": "liu_bei",
        "task_id": base.get("task_id"),
        "task_state": base.get("task_state"),
        "selected_state": selected,
        "state_reason": "explicit_review_preview" if preview_state else base["state_reason"],
        "review_preview": preview_state is not None,
        "canonical_source": "existing_albedo_state_keys_not_albedo_artwork",
        "planned_states": EXPECTED_TOTAL,
        "planned_expressions": EXPECTED_EXPRESSION_COUNT,
        "planned_actions": EXPECTED_ACTION_COUNT,
        "source_count": 0,
        "approved_native_state_count": 0,
        "artwork_status": "pending_distinct_standalone_sources",
        "native_a0_intake": base["native_a0_intake"],
        "states": [
            {"key": item["key"], "label": item["label"], "category": item["category"],
             "art_status": "awaiting_independent_native_art",
             "source_verified": False, "owner_approved": False, "asset_url": None}
            for item in manifest["states"]
        ],
        "display": {
            "mode": "review_only_typographic_33_state",
            "asset_url": None,
            "selected_label": manifest["states"][keys.index(selected)]["label"],
            "status": "Not a 33-state art delivery or portrait production release",
        },
        "owner_identity_approval": "pending",
        "independent_original_authorship_verified": False,
        "automatic_native_registration": False,
        "production_release_enabled": False,
    }
