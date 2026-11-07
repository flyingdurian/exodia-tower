"""Phase 5: read-only, fail-closed Liu Bei A0 fleet pilot integration hook.

No artwork registration, image delivery, owner approval, state release or
external provider dispatch occurs here. This only projects the existing
Liu Bei manual-intake technical evidence into a safe local control-plane view.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.liu_bei_manual_dropin import scan_dropin
from tools.liu_bei_native_identity_gate import LOCKED, verify_reference

SCHEMA = "exodia.phase5.liu_bei-a0-preflight/v1"
LIU_BEI_ID = "liu_bei"
FROZEN_IDS = ("memory", "archives", "inventory", "vault", "ninja",
              "cache", "strategy", "nova")
EXPECTED_ROSTER = set(FROZEN_IDS) | {"kiko", LIU_BEI_ID}
PILOT_STATES = ("neutral", "confident", "angered", "working", "pointing")


def liu_bei_a0_preflight(root: Path) -> dict:
    """Check immutable state locks and report only sanitized intake readiness."""
    root = Path(root).resolve()
    manifest_path = root.parent / "assets" / "review" / "liu_bei_pilot" / "pilot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_reference(manifest, root)

    if manifest.get("native_production_certified") is not False:
        raise ValueError("Native production release is not authorized")
    states = manifest.get("states")
    if not isinstance(states, dict) or set(states) != set(PILOT_STATES):
        raise ValueError("Liu Bei pilot state set drift")
    for state in PILOT_STATES:
        record = states[state]
        if not isinstance(record, dict) or (
            record.get("source_file") is not None or
            record.get("source_sha256") is not None or
            record.get("owner_approval_reference") is not None or
            record.get("actual_landmark_evidence") is not None or
            record.get("status") != "awaiting_native_source" or
            record.get("derived_from_composite") is not False or
            record.get("source_kind") != "pending_native_independent_standalone"
        ):
            raise ValueError("Unapproved Liu Bei state artwork mutation")
    roster = json.loads((root / "app" / "companions" / "roster.json").read_text("utf-8"))
    identities = {entry.get("id") for entry in roster}
    if identities != EXPECTED_ROSTER:
        raise ValueError("Fleet companion roster drift")
    if len(roster) != len(EXPECTED_ROSTER):
        raise ValueError("Duplicate companion identity")

    # The existing A0 scan is explicitly read-only without CLI write flags.
    # Its full report contains local paths and technical internals: never send
    # that report to a browser, or imply authoring/landmark review is complete.
    intake = scan_dropin(root)
    safe_statuses = {
        "awaiting_manual_png", "ambiguous_dropin", "unsafe_dropin",
        "unsafe_annotations", "source_rejected", "awaiting_image_bound_annotations",
        "source_or_annotations_rejected",
        "technical_and_annotated_geometry_ready_for_human_review",
    }
    status = intake.get("status")
    if status not in safe_statuses:
        raise ValueError("Unknown Liu Bei intake status")

    technical = intake.get("technical_source_pass") is True
    annotation = intake.get("annotated_geometry_consistency_pass") is True
    return {
        "schema": SCHEMA,
        "character_id": LIU_BEI_ID,
        "character_name": "Liu Bei",
        "pilot_scope": "identity_a0_only",
        "intake_status": status,
        "original_sha256": intake.get("candidate_sha256") if technical else None,
        "canonical_canvas": list(LOCKED),
        "technical_source_pass": technical,
        "image_bound_annotation_consistency": annotation,
        "independent_original_authorship_verified": False,
        "human_anatomy_review": "pending",
        "owner_identity_approval": "pending",
        "five_state_pilot": "locked_pending_exact_sha_owner_approval",
        "pilot_states": [
            {"state": name, "production_status": "locked"}
            for name in PILOT_STATES
        ],
        "frozen_other_companion_ids": list(FROZEN_IDS),
        "production_release_enabled": False,
        "native_production_certified": False,
    }
