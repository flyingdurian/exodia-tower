"""Read-only, fail-closed Phase 7 intake preflight for four Liu Bei state variants.

Candidate sources, if any, live only in ignored orchestrator/app_data/
liu_bei_variant_inbox/{confident,angered,working,pointing}.png. No image is
copied into production, registered, served, approved or automatically promoted.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.fleet.liu_bei_preflight import liu_bei_a0_preflight, PILOT_STATES
from tools.liu_bei_native_identity_gate import LOCKED, audit_identity, sha256
from tools.liu_bei_manual_dropin import audit_pixel_annotations

SCHEMA = "exodia.phase7.liu-bei-variant-preflight/v1"
REGISTRY_SCHEMA = "exodia.liu-bei-variant-intake-registry/v1"
A0_APPROVED_VISUAL_ORIGINAL_SHA = (
    "46e0a125a31586994f11e6660a55617ba50c5f073f6d882c671177ca8042a352"
)
VARIANTS = {
    "confident": "expression",
    "angered": "expression",
    "working": "action",
    "pointing": "action",
}


def _validate_registry(root: Path):
    path = root.parent / "assets/review/liu_bei_pilot/variant_registry.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    if (registry.get("schema") != REGISTRY_SCHEMA
            or registry.get("character_id") != "liu_bei"
            or registry.get("parent_state") != "neutral"
            or registry.get("approved_a0_original_visual_sha256")
                != A0_APPROVED_VISUAL_ORIGINAL_SHA
            or registry.get("native_canvas") != list(LOCKED)
            or registry.get("intake_policy") != "independent_standalone_png_per_state"
            or registry.get("automatic_registration_enabled") is not False
            or registry.get("production_release_enabled") is not False):
        raise ValueError("Liu Bei variant registry contract changed")

    states = registry.get("states")
    if not isinstance(states, dict) or tuple(states) != tuple(VARIANTS):
        raise ValueError("Liu Bei variant state keys or order changed")
    if tuple(PILOT_STATES) != ("neutral", *VARIANTS):
        raise ValueError("Canonical Liu Bei five-state set changed")
    for name, category in VARIANTS.items():
        item = states[name]
        if (not isinstance(item, dict)
                or item.get("category") != category
                or item.get("status") != "awaiting_independent_state_source"
                or item.get("source_file") is not None
                or item.get("source_sha256") is not None
                or item.get("landmark_evidence") is not None
                or item.get("owner_approval_reference") is not None
                or item.get("production_release_enabled") is not False):
            raise ValueError("Unapproved Liu Bei variant registry mutation")
    return registry


def _candidate_preflight(root: Path, inbox: Path, name: str, pilot: dict):
    result = {
        "key": name,
        "category": VARIANTS[name],
        "status": "awaiting_independent_state_source",
        "technical_source_pass": False,
        "image_bound_annotation_consistency": False,
        "geometry_ready_for_owner_review": False,
        "candidate_sha256": None,
        "source_authenticity_verified": False,
        "owner_state_approval": "pending",
        "asset_url": None,
        "production_release_enabled": False,
    }
    candidate = inbox / (name + ".png")
    sidecar = inbox / (name + ".landmarks.json")
    if candidate.is_symlink() or sidecar.is_symlink():
        result["status"] = "unsafe_candidate_or_sidecar"
        return result
    if not candidate.exists():
        if sidecar.exists():
            result["status"] = "orphaned_annotations"
        return result
    if not candidate.is_file():
        result["status"] = "unsafe_candidate_or_sidecar"
        return result
    try:
        # Reject huge, incomplete and wrong-size files *before* sampling pixels.
        before = candidate.stat()
        if not 0 < before.st_size <= 64 * 1024 * 1024:
            result["status"] = "rejected_source_file"
            return result
        with Image.open(candidate) as image:
            if image.format != "PNG" or image.size != LOCKED:
                result["status"] = "rejected_native_dimensions"
                return result
        candidate_sha = sha256(candidate)
        tech = audit_identity(pilot, root, candidate.relative_to(root), candidate_sha)
        after = candidate.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            result["status"] = "candidate_copy_unstable"
            return result
        if not tech.get("technical_source_pass"):
            result["status"] = "rejected_source_file"
            return result
        result["candidate_sha256"] = candidate_sha
        result["technical_source_pass"] = True
        result["status"] = "awaiting_image_bound_annotations"
        if not sidecar.exists():
            return result
        if not sidecar.is_file() or sidecar.stat().st_size > 262144:
            result["status"] = "rejected_annotations"
            return result
        annotations = json.loads(sidecar.read_text(encoding="utf-8"))
        evidence = audit_pixel_annotations(candidate, annotations, pilot)
        # Source can change during measurement: rehash before accepting any geometry.
        if sha256(candidate) != candidate_sha:
            result["status"] = "candidate_copy_unstable"
            result["technical_source_pass"] = False
            result["candidate_sha256"] = None
            return result
        if evidence.get("annotated_geometry_consistency_pass") is not True:
            result["status"] = "rejected_annotations"
            return result
        result["image_bound_annotation_consistency"] = True
        result["geometry_ready_for_owner_review"] = True
        result["status"] = "technical_geometry_ready_for_human_review"
        return result
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            json.JSONDecodeError, UnidentifiedImageError):
        result["status"] = "source_or_annotations_unavailable"
        return result


def liu_bei_variant_preflight(root: Path):
    """Sanitized GET-only projection; original approved SHA != formatted native SHA."""
    root = Path(root).resolve()
    _validate_registry(root)
    a0 = liu_bei_a0_preflight(root)  # Also validates frozen roster + pilot registry.
    if (a0.get("character_id") != "liu_bei"
            or a0.get("production_release_enabled") is not False
            or a0.get("native_production_certified") is not False
            or a0.get("owner_identity_approval") != "pending"):
        raise ValueError("Liu Bei A0 provenance or release lock changed")
    pilot = json.loads(
        (root.parent / "assets/review/liu_bei_pilot/pilot_manifest.json")
        .read_text(encoding="utf-8")
    )
    inbox = root / "app_data/liu_bei_variant_inbox"
    if inbox.is_symlink() or not inbox.resolve().is_relative_to(root):
        raise ValueError("Unsafe variant intake folder")
    if inbox.exists() and not inbox.is_dir():
        raise ValueError("Invalid variant intake folder")
    if inbox.is_dir():
        actual = {p.name for p in inbox.iterdir() if p.name.lower().endswith(".png")}
        if not actual.issubset({name + ".png" for name in VARIANTS}):
            raise ValueError("Unexpected Liu Bei variant source name")

    return {
        "schema": SCHEMA,
        "character_id": "liu_bei",
        "parent_identity_state": "neutral",
        "approved_a0_original_visual_sha256": A0_APPROVED_VISUAL_ORIGINAL_SHA,
        "formatted_a0_native_sha256":
            a0.get("original_sha256") if a0.get("technical_source_pass") is True else None,
        "a0_native_technical_pass": a0.get("technical_source_pass") is True,
        "a0_image_bound_geometry_pass":
            a0.get("image_bound_annotation_consistency") is True,
        "states": [_candidate_preflight(root, inbox, name, pilot)
                   for name in VARIANTS],
        "five_state_staging_authorized": False,
        "automatic_registration_enabled": False,
        "production_release_enabled": False,
    }
