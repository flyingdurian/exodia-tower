"""EXODIA_STRICT_INSTRUCTION_COMPLIANCE: sequential art-production authorization.

No image or frame generation is performed here. Gate results are evidence of
technical checks, NOT proof of artistry or authentic owner consent.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

RULE = "EXODIA_STRICT_INSTRUCTION_COMPLIANCE"
SCHEMA = "exodia.strict-instruction/v1"
CANVAS = (1536, 1920)
STATES = ("idle", "working", "explaining")
ANCHORS = ("left_eye_corner", "right_eye_corner", "face_center",
           "ornament_attachment", "left_shoulder", "right_shoulder")
CAMERA = {"translate_px": [0, 0], "zoom": 1, "rotation_deg": 0, "crop": None}


class GateBlocked(ValueError):
    pass


def ensure(condition, reason):
    if not condition:
        raise GateBlocked(reason)


def digest_json(record):
    packed = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_dimensions(path):
    ensure(path.is_file(), "image_missing")
    with Image.open(path) as im:
        ensure(im.format == "PNG", "png_required")
        size = im.size
        im.verify()
    return size


def read_json(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    ensure(isinstance(obj, dict), "json_object_required")
    return obj


def preflight(spec, directory):
    """Pre-generation gate. No speculative master images allowed before PASS."""
    ensure(spec.get("schema") == SCHEMA and spec.get("rule") == RULE,
           "strict_rule_or_schema_missing")
    ensure(spec.get("agent_id") == "kiko", "unrecognized_albedo_id")
    ensure(spec.get("state") in STATES, "state_must_be_idle_working_explaining")
    for key in ("requested", "effective"):
        ensure(spec.get(key) == {"canvas_px": [1536, 1920], "aspect": "4:5"},
               key + "_spec_deviation_or_unknown")
    ensure(spec.get("model_adjustments") == {}, "generator_altered_locked_spec")
    ensure(spec.get("camera") == CAMERA, "camera_not_pixel_locked")
    ensure(spec.get("master_requires_owner_approval") is True, "approval_gate_disabled")
    ref = spec.get("approved_reference")
    ensure(isinstance(ref, dict), "reference_missing")
    name = ref.get("file")
    ensure(isinstance(name, str) and bool(name), "reference_path_missing")
    path = (directory / name).resolve()
    ensure(path.is_relative_to(directory.resolve()), "reference_outside_working_directory")
    ensure(path.is_file() and image_dimensions(path)[0] >= 512, "reference_not_verified")
    actual = digest_file(path)
    ensure(ref.get("sha256") == actual, "reference_sha256_mismatch")
    ensure(ref.get("owner_approved_source") is True, "approved_benchmark_required")
    return {"schema": SCHEMA, "rule": RULE, "stage": "preflight",
            "status": "pass", "state": spec["state"],
            "spec_sha256": digest_json(spec), "reference_sha256": actual,
            "master_keyframe_generation_allowed": True,
            "sequence_generation_allowed": False}


def master_check(spec, directory, preflight_receipt, master_path, anchors):
    """Master can be checked only with a matching successful preflight receipt."""
    expected = preflight(spec, directory)
    ensure(preflight_receipt == expected, "preflight_receipt_missing_or_stale")
    ensure(image_dimensions(master_path) == CANVAS, "master_not_native_1536x1920")
    ensure(anchors.get("state") == spec["state"], "master_state_mismatch")
    ensure(anchors.get("camera") == CAMERA, "master_camera_changed")
    ensure(anchors.get("kind") == "independent_native_master", "cropped_or_upscaled_art")
    points = anchors.get("anchors_px")
    ensure(isinstance(points, dict) and set(points) == set(ANCHORS),
           "six_pixel_anchor_coordinates_required")
    for name, point in points.items():
        ensure(isinstance(point, list) and len(point) == 2 and
               all(type(x) is int for x in point) and
               0 <= point[0] < CANVAS[0] and 0 <= point[1] < CANVAS[1],
               "anchor_invalid_" + name)
    x, y = points["face_center"]
    ensure(abs(x - 768) <= 61 and abs(y - 634) <= 87, "face_anchor_off_standard")
    return {"schema": SCHEMA, "rule": RULE, "stage": "master",
            "status": "technical_check_passed_pending_owner_signoff",
            "state": spec["state"], "spec_sha256": digest_json(spec),
            "master_sha256": digest_file(master_path),
            "anchors_sha256": digest_json(anchors),
            "owner_approved": False, "sequence_generation_allowed": False}


def authorize_sequence(spec, directory, pre_receipt, master_receipt,
                       master_path, anchors, owner_decision):
    """Never authorize frames without an explicit matching master-specific decision."""
    expected = master_check(spec, directory, pre_receipt, master_path, anchors)
    ensure(master_receipt == expected, "master_receipt_missing_or_stale")
    ensure(owner_decision.get("decision") == "approved", "master_not_approved_by_owner")
    ensure(owner_decision.get("approved_by") == "owner", "approval_actor_missing")
    ensure(owner_decision.get("state") == spec["state"], "approval_state_mismatch")
    for key in ("spec_sha256", "master_sha256", "anchors_sha256"):
        ensure(owner_decision.get(key) == expected[key], "approval_" + key + "_mismatch")
    evidence = owner_decision.get("confirmation_reference")
    ensure(isinstance(evidence, str) and len(evidence.strip()) >= 8,
           "real_user_confirmation_reference_required")
    return {"schema": SCHEMA, "rule": RULE, "stage": "sequence",
            "status": "technical_permit_after_recorded_owner_decision",
            "state": spec["state"], "spec_sha256": expected["spec_sha256"],
            "master_sha256": expected["master_sha256"],
            "anchors_sha256": expected["anchors_sha256"],
            "confirmation_reference": evidence, "sequence_generation_allowed": True,
            "production_release_allowed": False,
            "warning": "Record authenticity must be checked manually against the actual "
                       "user confirmation; no auto-generated approval is trustworthy."}


def main():
    parser = argparse.ArgumentParser(description="Exact-order Exodia asset gate")
    sub = parser.add_subparsers(dest="stage", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("spec", type=Path)
    pre.add_argument("--out", type=Path, required=True)
    master = sub.add_parser("master-check")
    master.add_argument("spec", type=Path)
    master.add_argument("preflight_receipt", type=Path)
    master.add_argument("master_image", type=Path)
    master.add_argument("anchors", type=Path)
    master.add_argument("--out", type=Path, required=True)
    seq = sub.add_parser("authorize-sequence")
    for name in ("spec", "preflight_receipt", "master_receipt",
                 "master_image", "anchors", "owner_decision"):
        seq.add_argument(name, type=Path)
    seq.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    try:
        spec = read_json(opts.spec)
        root = opts.spec.resolve().parent
        if opts.stage == "preflight":
            result = preflight(spec, root)
        elif opts.stage == "master-check":
            result = master_check(spec, root, read_json(opts.preflight_receipt),
                                  opts.master_image, read_json(opts.anchors))
        else:
            result = authorize_sequence(spec, root, read_json(opts.preflight_receipt),
                                        read_json(opts.master_receipt), opts.master_image,
                                        read_json(opts.anchors), read_json(opts.owner_decision))
        opts.out.parent.mkdir(parents=True, exist_ok=True)
        opts.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"rule": RULE, "status": "halted",
                          "reason": str(exc), "art_generation_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
