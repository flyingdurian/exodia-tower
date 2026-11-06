"""Manual A0 drop-in scanner is read-only by default and never approves artwork."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from tools.riven_native_identity_gate import ROOT, PILOT_MANIFEST, LOCKED, sha256
from tools.riven_manual_dropin import (
    SCHEMA, POINTS, audit_pixel_annotations, scan_dropin, stamp_patches, template_for
)


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    root.mkdir()
    data = tmp_path / "assets" / "review" / "riven_pilot"
    data.mkdir(parents=True)
    manifest = json.loads(PILOT_MANIFEST.read_text("utf-8"))
    manifest["identity_reference"]["path"] = "ref.png"
    (root/"ref.png").write_bytes((ROOT/"frontend/companions/source_masters/router.png").read_bytes())
    (data/"pilot_manifest.json").write_text(json.dumps(manifest))
    inbox = root / "app_data" / "riven_a0_inbox"
    inbox.mkdir(parents=True)
    return root, inbox, manifest


def candidate_image(inbox):
    path = inbox / "riven_A0_native.png"
    image = Image.new("RGB", LOCKED)
    draw = ImageDraw.Draw(image)
    for y in range(0, LOCKED[1], 70):
        for x in range(0, LOCKED[0], 70):
            draw.rectangle((x, y, x+69, y+69), fill=(x//7%256, y//7%256, (x+y)//12%256))
    image.save(path)
    return path


def landmarks():
    return {
        "left_iris_center": [610, 634], "right_iris_center": [902, 634],
        "left_shoulder_joint": [505, 980], "right_shoulder_joint": [1035, 980],
        "head_left": [461, 620], "head_right": [1075.4, 620],
    }


def test_no_drop_in_is_pending_without_release(isolated):
    root, inbox, _ = isolated
    report = scan_dropin(root, inbox)
    assert report["status"] == "awaiting_manual_png"
    assert report["owner_identity_approval"] == "pending"
    assert report["production_release_enabled"] is False


def test_native_file_provides_real_hash_but_requires_annotations(isolated):
    root, inbox, _ = isolated
    candidate = candidate_image(inbox)
    report = scan_dropin(root, inbox)
    assert report["candidate_sha256"] == sha256(candidate)
    assert report["technical_source_pass"] is True
    assert report["annotated_geometry_consistency_pass"] is False
    assert report["status"] == "awaiting_image_bound_annotations"
    assert report["five_state_pilot"].startswith("blocked")


def test_annotation_template_does_not_fabricate_measurements(isolated):
    root, inbox, _ = isolated
    file = candidate_image(inbox)
    report = scan_dropin(root, inbox, make_template=True)
    annotation = json.loads(file.with_suffix(".landmarks.json").read_text())
    assert annotation["source_sha256"] == sha256(file)
    assert all(annotation["landmarks"][p] is None for p in POINTS)
    assert not report["annotated_geometry_consistency_pass"]
    assert report["errors"]


def test_real_pixel_patch_bindings_and_geometry_still_require_owner_review(isolated):
    root, inbox, manifest = isolated
    file = candidate_image(inbox)
    note = template_for(file)
    note["landmarks"] = landmarks()
    sidecar = file.with_suffix(".landmarks.json")
    sidecar.write_text(json.dumps(note))
    stamped = stamp_patches(file, sidecar)
    assert all(len(stamped["pixel_patch_sha256"][p]) == 64 for p in POINTS)
    report = scan_dropin(root, inbox)
    assert report["technical_source_pass"] is True
    assert report["annotated_geometry_consistency_pass"] is True
    assert report["status"] == "technical_and_annotated_geometry_ready_for_human_review"
    assert report["owner_identity_approval"] == "pending"
    assert report["source_authenticity_verified"] is False
    assert report["production_release_enabled"] is False
    assert report["landmark_evidence"]["automated_iris_detection"] is False


def test_eye_drift_and_tampering_are_rejected(isolated):
    root, inbox, manifest = isolated
    file = candidate_image(inbox)
    note = template_for(file)
    note["landmarks"] = landmarks()
    sidecar = file.with_suffix(".landmarks.json")
    sidecar.write_text(json.dumps(note))
    stamp_patches(file, sidecar)
    annotation = json.loads(sidecar.read_text())
    annotation["landmarks"]["right_iris_center"][1] = 656
    result = audit_pixel_annotations(file, annotation, manifest)
    assert not result["annotated_geometry_consistency_pass"]
    assert any(x.startswith("pixel_patch_mismatch_") for x in result["errors"])
    assert "iris_midline_outside_two_pixel_tolerance" in result["errors"]


def test_ambiguous_folder_and_path_escape_fail(isolated, tmp_path):
    root, inbox, _ = isolated
    file = candidate_image(inbox)
    file2 = inbox / "second.png"
    file2.write_bytes(file.read_bytes())
    report = scan_dropin(root, inbox)
    assert report["status"] == "ambiguous_dropin"
    assert report["errors"] == ["exactly_one_riven_a0_png_required"]
    with pytest.raises(ValueError, match="isolated_worktree"):
        scan_dropin(root, tmp_path.parent)


def test_crop_or_non_native_cannot_pass_original_gate(isolated):
    root, inbox, _ = isolated
    file = inbox / "riven_A0_native.png"
    Image.new("RGB", (1122, 1402), "#161616").save(file)
    report = scan_dropin(root, inbox)
    assert report["technical_source_pass"] is False
    assert "not_native_1536x1920_png" in report["errors"]
    assert report["owner_identity_approval"] == "pending"


def test_linked_candidate_is_rejected_before_reading_external_bytes(isolated, tmp_path):
    root, inbox, _ = isolated
    external = tmp_path / "outside.png"
    Image.new("RGB", LOCKED, "#102030").save(external)
    link = inbox / "riven_A0_native.png"
    try:
        link.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("OS cannot create test symlinks")
    report = scan_dropin(root, inbox)
    assert report["status"] == "unsafe_dropin"
    assert report["errors"] == ["symbolic_candidate_rejected"]
    assert report["candidate_sha256"] is None
    assert report["production_release_enabled"] is False


def test_linked_annotation_never_reads_or_overwrites_external_data(isolated, tmp_path):
    root, inbox, _ = isolated
    candidate = candidate_image(inbox)
    external = tmp_path / "unrelated-sidecar.json"
    external.write_text('{"unrelated":"unchanged"}', encoding="utf-8")
    sidecar = candidate.with_suffix(".landmarks.json")
    try:
        sidecar.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("OS cannot create test symlinks")
    for flags in ({}, {"make_template": True}, {"stamp": True}):
        report = scan_dropin(root, inbox, **flags)
        assert report["status"] == "unsafe_annotations"
        assert report["errors"] == ["unsafe_or_linked_annotation_sidecar"]
        assert report["production_release_enabled"] is False
    with pytest.raises(ValueError, match="unsafe_or_linked_annotation_sidecar"):
        stamp_patches(candidate, sidecar)
    assert external.read_text(encoding="utf-8") == '{"unrelated":"unchanged"}'


def test_rejected_source_cannot_create_landmark_sidecar(isolated):
    root, inbox, _ = isolated
    candidate = inbox / "riven_A0_native.png"
    Image.new("RGB", (1122, 1402), "#202040").save(candidate)
    report = scan_dropin(root, inbox, make_template=True)
    assert not candidate.with_suffix(".landmarks.json").exists()
    assert report["status"] == "source_rejected"
    assert not report["technical_source_pass"]


def test_invalid_annotation_root_is_reported_not_crashed(isolated):
    root, inbox, _ = isolated
    candidate = candidate_image(inbox)
    sidecar = candidate.with_suffix(".landmarks.json")
    sidecar.write_text('["not","a","landmark","object"]', encoding="utf-8")
    report = scan_dropin(root, inbox)
    assert report["status"] == "source_or_annotations_rejected"
    assert "annotation_invalid_annotation_document_must_be_object" in report["errors"]
    assert report["owner_identity_approval"] == "pending"

def test_documented_direct_cli_works_without_pythonpath(isolated):
    root, inbox, _ = isolated
    script = ROOT / "tools" / "riven_manual_dropin.py"
    env = {**os.environ, "PYTHONPATH": ""}
    command = [sys.executable, str(script), "--root", str(root)]
    result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "awaiting_manual_png"
    assert report["production_release_enabled"] is False
    assert report["owner_identity_approval"] == "pending"
    candidate = candidate_image(inbox)
    second = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            capture_output=True, timeout=20)
    assert second.returncode == 0, second.stderr
    report2 = json.loads(second.stdout)
    assert report2["candidate_sha256"] == sha256(candidate)
    assert report2["technical_source_pass"] is True
    assert report2["status"] == "awaiting_image_bound_annotations"
    assert report2["production_release_enabled"] is False
