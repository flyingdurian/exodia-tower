"""Fail-closed, non-registering manual Riven A0 intake from an ignored local folder.

This augments PR #14's native technical gate. Pixel-anchored annotation checks
validate the supplied coordinates and actual image patches, NOT iris detection
or artistic identity. A review-ready report cannot authorize five-state art.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

# Running `python tools/riven_manual_dropin.py` does not put orchestrator/
# on sys.path. Match the documented direct Windows operator command without
# depending on the developer's PYTHONPATH or an editable pip install.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.riven_native_identity_gate import (
    ROOT, LOCKED, PILOT_MANIFEST, audit_identity, sha256,
)

SCHEMA = "exodia.riven-a0-image-landmarks/v1"
POINTS = (
    "left_iris_center", "right_iris_center",
    "left_shoulder_joint", "right_shoulder_joint",
    "head_left", "head_right",
)
PATCH_RADIUS = 9
INBOX = ROOT / "app_data" / "riven_a0_inbox"


def reject_linked_paths(candidate: Path, sidecar: Path | None = None):
    """A manual intake may neither follow linked art nor link an annotation outside inbox."""
    if candidate.is_symlink():
        raise ValueError("symbolic_candidate_rejected")
    if sidecar is not None:
        if sidecar != candidate.with_suffix(".landmarks.json") or sidecar.is_symlink():
            raise ValueError("unsafe_or_linked_annotation_sidecar")
        if sidecar.parent.resolve() != candidate.parent.resolve():
            raise ValueError("annotation_must_be_sibling_of_candidate")


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def checked_point(value):
    if not isinstance(value, list) or len(value) != 2 or not all(is_number(x) for x in value):
        raise ValueError("landmark_must_be_numeric_xy")
    x, y = map(float, value)
    if not (PATCH_RADIUS <= x < LOCKED[0] - PATCH_RADIUS and
            PATCH_RADIUS <= y < LOCKED[1] - PATCH_RADIUS):
        raise ValueError("landmark_outside_original_pixel_canvas")
    return (x, y)


def pixel_patch_sha256(image: Image.Image, point: tuple[float, float]) -> str:
    x, y = (round(point[0]), round(point[1]))
    patch = image.convert("RGB").crop((
        x-PATCH_RADIUS, y-PATCH_RADIUS, x+PATCH_RADIUS+1, y+PATCH_RADIUS+1
    ))
    return hashlib.sha256(patch.tobytes()).hexdigest()


def audit_pixel_annotations(candidate: Path, annotations: dict, manifest: dict) -> dict:
    """Verify coordinate and patch evidence without claiming to recognize a face."""
    if not isinstance(annotations, dict):
        raise ValueError("annotation_document_must_be_object")
    errors = []
    result = {
        "annotation_schema": annotations.get("schema"),
        "annotation_source_sha256": annotations.get("source_sha256"),
        "pixel_patch_binding_verified": False,
        "annotated_geometry_consistency_pass": False,
        "automated_iris_detection": False,
        "human_anatomy_identity_review": "pending",
        "errors": errors,
    }
    if annotations.get("schema") != SCHEMA:
        errors.append("annotation_schema_invalid")
    if annotations.get("source_sha256") != sha256(candidate):
        errors.append("annotation_source_sha_mismatch")
    positions = annotations.get("landmarks")
    hashes = annotations.get("pixel_patch_sha256")
    if not isinstance(positions, dict) or not isinstance(hashes, dict):
        errors.append("measured_landmarks_and_pixel_patches_required")
        return result
    try:
        points = {key: checked_point(positions.get(key)) for key in POINTS}
    except ValueError as exc:
        errors.append(str(exc))
        return result
    if any(not isinstance(hashes.get(name), str) or len(hashes[name]) != 64
           for name in POINTS):
        errors.append("image_patch_hashes_required")
        return result
    with Image.open(candidate) as original:
        if original.format != "PNG" or original.size != LOCKED:
            errors.append("native_original_required_for_pixel_review")
            return result
        for name in POINTS:
            if pixel_patch_sha256(original, points[name]) != hashes[name]:
                errors.append("pixel_patch_mismatch_" + name)
    result["pixel_patch_binding_verified"] = not any(
        err.startswith("pixel_patch_mismatch_") for err in errors
    )
    iris_left, iris_right = points["left_iris_center"], points["right_iris_center"]
    shoulder_left, shoulder_right = points["left_shoulder_joint"], points["right_shoulder_joint"]
    head_left, head_right = points["head_left"], points["head_right"]
    iris_y = (iris_left[1] + iris_right[1]) / 2
    shoulder_y = (shoulder_left[1] + shoulder_right[1]) / 2
    head_width = head_right[0] - head_left[0]
    head_x = (head_left[0] + head_right[0]) / 2
    result["measured_annotations_px"] = {
        "iris_midline_y": iris_y,
        "shoulder_midline_y": shoulder_y,
        "head_width": head_width,
        "head_center_x": head_x,
    }
    if not (iris_left[0] < iris_right[0] and
            head_left[0] < iris_left[0] < iris_right[0] < head_right[0]):
        errors.append("iris_or_head_horizontal_order_invalid")
    if shoulder_left[0] >= shoulder_right[0]:
        errors.append("shoulder_horizontal_order_invalid")
    if abs(iris_y - manifest["eye_midline_y_px"]) > 2:
        errors.append("iris_midline_outside_two_pixel_tolerance")
    if abs(shoulder_y - manifest["shoulder_baseline_y_px"]) > 2:
        errors.append("shoulder_midline_outside_two_pixel_tolerance")
    if abs(head_width - manifest["head_width_px"]) > 4:
        errors.append("head_width_outside_four_pixel_tolerance")
    if abs(head_x - manifest["head_center_x_px"]) > 8:
        errors.append("head_center_outside_eight_pixel_tolerance")
    result["annotated_geometry_consistency_pass"] = not errors
    return result


def template_for(candidate: Path) -> dict:
    return {
        "schema": SCHEMA,
        "source_sha256": sha256(candidate),
        "landmarks": {name: None for name in POINTS},
        "pixel_patch_sha256": {name: None for name in POINTS},
        "review_note": "Mark actual iris, anatomical shoulder and head boundary pixels; targets are not measurements.",
    }


def stamp_patches(candidate: Path, sidecar: Path) -> dict:
    """Explicit helper only: hashes user-annotated pixels, not automated face detection."""
    reject_linked_paths(candidate, sidecar)
    original = json.loads(sidecar.read_text(encoding="utf-8"))
    if not isinstance(original, dict):
        raise ValueError("annotation_document_must_be_object")
    if original.get("source_sha256") != sha256(candidate):
        raise ValueError("annotation_source_sha_mismatch")
    positions = original.get("landmarks")
    if not isinstance(positions, dict):
        raise ValueError("measured_landmarks_required_before_stamping")
    points = {name: checked_point(positions.get(name)) for name in POINTS}
    with Image.open(candidate) as image:
        if image.format != "PNG" or image.size != LOCKED:
            raise ValueError("native_png_required")
        original["pixel_patch_sha256"] = {
            name: pixel_patch_sha256(image, points[name]) for name in POINTS
        }
    # Atomic replacement never follows a newly swapped symbolic-link destination.
    tmp_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=sidecar.parent,
                                prefix=".riven-a0-", suffix=".tmp", delete=False) as tmp:
            tmp.write(json.dumps(original, indent=2) + "\n")
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, sidecar)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
    return original


def scan_dropin(root: Path = ROOT, inbox: Path | None = None,
                *, make_template: bool = False, stamp: bool = False) -> dict:
    root = root.resolve()
    inbox = (inbox or root / "app_data" / "riven_a0_inbox").resolve()
    if not inbox.is_relative_to(root):
        raise ValueError("riven_intake_must_be_within_isolated_worktree")
    manifest = json.loads((root.parent / "assets/review/riven_pilot/pilot_manifest.json").read_text("utf-8"))
    report = {
        "schema": "exodia.riven-a0-manual-intake/v1",
        "character_id": "router",
        "inbox": str(inbox),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "awaiting_manual_png",
        "candidate_sha256": None,
        "technical_source_pass": False,
        "annotated_geometry_consistency_pass": False,
        "owner_identity_approval": "pending",
        "source_authenticity_verified": False,
        "five_state_pilot": "blocked_until_exact_sha_owner_approval",
        "production_release_enabled": False,
        "errors": [],
    }
    if not inbox.is_dir():
        return report
    pngs = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not pngs:
        return report
    if len(pngs) != 1:
        report["status"] = "ambiguous_dropin"
        report["errors"].append("exactly_one_riven_a0_png_required")
        return report
    candidate = pngs[0]
    try:
        reject_linked_paths(candidate)
    except ValueError as exc:
        report["status"] = "unsafe_dropin"
        report["errors"].append(str(exc))
        return report
    actual_sha = sha256(candidate)
    report["candidate_sha256"] = actual_sha
    source = audit_identity(manifest, root, candidate.relative_to(root), actual_sha)
    report["technical_source_pass"] = source["technical_source_pass"]
    report["errors"].extend(source["errors"])
    report["candidate"] = source["identity_candidate"]
    sidecar = candidate.with_suffix(".landmarks.json")
    try:
        reject_linked_paths(candidate, sidecar)
    except ValueError as exc:
        report["status"] = "unsafe_annotations"
        report["errors"].append(str(exc))
        return report
    if not source["technical_source_pass"] and (make_template or stamp):
        report["status"] = "source_rejected"
        return report
    if make_template and not sidecar.exists():
        # Exclusive create: cannot follow a previously nonexistent linked sidecar.
        with sidecar.open("x", encoding="utf-8") as f:
            f.write(json.dumps(template_for(candidate), indent=2) + "\n")
    if stamp and sidecar.exists():
        stamp_patches(candidate, sidecar)
    if not sidecar.is_file():
        report["status"] = "awaiting_image_bound_annotations" if source["technical_source_pass"] else "source_rejected"
        return report
    try:
        annotations = json.loads(sidecar.read_text(encoding="utf-8"))
        # A generated, SHA-bound blank template is awaiting real human
        # anatomical coordinates; do not misclassify the native PNG as bad.
        if (isinstance(annotations, dict)
                and annotations.get("schema") == SCHEMA
                and annotations.get("source_sha256") == actual_sha
                and isinstance(annotations.get("landmarks"), dict)
                and all(annotations["landmarks"].get(name) is None for name in POINTS)):
            report["errors"].append("landmarks_pending_human_measurement")
            report["status"] = "awaiting_image_bound_annotations"
            return report
        evidence = audit_pixel_annotations(candidate, annotations, manifest)
        report["landmark_evidence"] = evidence
        report["errors"].extend(evidence["errors"])
        report["annotated_geometry_consistency_pass"] = evidence["annotated_geometry_consistency_pass"]
    except (ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
        report["errors"].append("annotation_invalid_" + str(exc))
    report["status"] = ("technical_and_annotated_geometry_ready_for_human_review"
                        if report["technical_source_pass"] and report["annotated_geometry_consistency_pass"]
                        else "source_or_annotations_rejected")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inbox", type=Path)
    parser.add_argument("--watch", action="store_true",
                        help="Operator starts foreground local file watcher; Ctrl+C stops it")
    parser.add_argument("--write-annotation-template", action="store_true")
    parser.add_argument("--stamp-patches", action="store_true",
                        help="Stamp patches from annotated original pixels only, never infer landmarks")
    args = parser.parse_args(argv)
    try:
        if not args.watch:
            report = scan_dropin(args.root, args.inbox,
                                 make_template=args.write_annotation_template,
                                 stamp=args.stamp_patches)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 2 if report["errors"] else 0
        # Stable file signatures: do not read a partially copied PNG.
        last_signature = None
        stable_count = 0
        last_reported = None
        print("Watching local Riven A0 inbox (foreground); Ctrl+C exits.", flush=True)
        while True:
            folder = (args.inbox or args.root / "app_data" / "riven_a0_inbox")
            entries = sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                             for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
            signature = tuple(entries)
            stable_count = stable_count + 1 if signature == last_signature else 0
            last_signature = signature
            if stable_count >= 2 and signature != last_reported:
                report = scan_dropin(args.root, args.inbox)
                print(json.dumps(report, indent=2, sort_keys=True), flush=True)
                last_reported = signature
            time.sleep(0.65)
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "schema": "exodia.riven-a0-manual-intake/v1",
            "status": "intake_error", "error": str(exc),
            "owner_identity_approval": "pending",
            "production_release_enabled": False,
        }, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
