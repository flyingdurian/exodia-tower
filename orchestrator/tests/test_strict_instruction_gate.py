"""The fixtures are synthetic technical tests, never owner-approved artwork."""
import importlib.util
from pathlib import Path

import pytest
from PIL import Image

MOD = Path(__file__).resolve().parents[1] / "tools" / "strict_instruction_gate.py"
spec = importlib.util.spec_from_file_location("strict_instruction_gate", MOD)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.fixture
def sample(tmp_path):
    ref = tmp_path / "approved_source.png"
    Image.new("RGB", (1024, 1536), "purple").save(ref)
    data = {"schema": gate.SCHEMA, "rule": gate.RULE,
            "agent_id": "kiko", "state": "idle",
            "requested": {"canvas_px": [1536, 1920], "aspect": "4:5"},
            "effective": {"canvas_px": [1536, 1920], "aspect": "4:5"},
            "model_adjustments": {}, "camera": gate.CAMERA,
            "master_requires_owner_approval": True,
            "approved_reference": {"file": ref.name, "sha256": gate.digest_file(ref),
                                   "owner_approved_source": True}}
    return tmp_path, data


def anchor_data():
    return {"state": "idle", "kind": "independent_native_master",
            "camera": gate.CAMERA,
            "anchors_px": {
                "left_eye_corner": [604, 610], "right_eye_corner": [920, 610],
                "face_center": [768, 634], "ornament_attachment": [1110, 244],
                "left_shoulder": [390, 950], "right_shoulder": [1146, 950]}}


def valid_master(sample):
    folder, data = sample
    receipt = gate.preflight(data, folder)
    path = folder / "master.png"
    Image.new("RGB", gate.CANVAS, "purple").save(path)
    anchors = anchor_data()
    checked = gate.master_check(data, folder, receipt, path, anchors)
    return receipt, path, anchors, checked


def test_preflight_grants_single_master_only(sample):
    folder, data = sample
    result = gate.preflight(data, folder)
    assert result["master_keyframe_generation_allowed"]
    assert not result["sequence_generation_allowed"]


@pytest.mark.parametrize("key,value,error", [
    ("requested", {"canvas_px": [1536, 1920], "aspect": "3:4"}, "requested_spec_deviation"),
    ("effective", {"canvas_px": [1536, 2048], "aspect": "4:5"}, "effective_spec_deviation"),
    ("effective", {"canvas_px": [1536, 1920], "aspect": "3:4"}, "effective_spec_deviation"),
    ("model_adjustments", {"aspect_ratio": "3:4"}, "generator_altered_locked_spec"),
    ("camera", {"translate_px": [1, 0], "zoom": 1, "rotation_deg": 0, "crop": None},
     "camera_not_pixel_locked")])
def test_locked_spec_deviation_blocks_before_image_generation(sample, key, value, error):
    folder, data = sample
    data[key] = value
    with pytest.raises(gate.GateBlocked, match=error):
        gate.preflight(data, folder)


def test_approved_reference_has_to_match_real_sha(sample):
    folder, data = sample
    data["approved_reference"]["sha256"] = "0"*64
    with pytest.raises(gate.GateBlocked, match="reference_sha256_mismatch"):
        gate.preflight(data, folder)


def test_master_requires_receipt_and_native_frame(sample):
    folder, data = sample
    receipt = gate.preflight(data, folder)
    image = folder / "master.png"
    Image.new("RGB", (1024, 1536), "purple").save(image)
    with pytest.raises(gate.GateBlocked, match="master_not_native_1536x1920"):
        gate.master_check(data, folder, receipt, image, anchor_data())
    Image.new("RGB", gate.CANVAS, "purple").save(image)
    receipt["spec_sha256"] = "changed"
    with pytest.raises(gate.GateBlocked, match="preflight_receipt_missing_or_stale"):
        gate.master_check(data, folder, receipt, image, anchor_data())


def test_master_passes_technical_check_but_does_not_grant_approval(sample):
    pre, path, anchors, master = valid_master(sample)
    assert master["status"] == "technical_check_passed_pending_owner_signoff"
    assert not master["owner_approved"] and not master["sequence_generation_allowed"]


def test_explicit_matching_owner_approval_is_mandatory(sample):
    folder, data = sample
    pre, path, anchors, master = valid_master(sample)
    approval = {"decision": "pending", "approved_by": "owner", "state": "idle",
                "spec_sha256": master["spec_sha256"], "master_sha256": master["master_sha256"],
                "anchors_sha256": master["anchors_sha256"],
                "confirmation_reference": "SYNTHETIC_NOT_REAL_USER_APPROVAL"}
    with pytest.raises(gate.GateBlocked, match="master_not_approved"):
        gate.authorize_sequence(data, folder, pre, master, path, anchors, approval)
    approval["decision"] = "approved"
    approval["master_sha256"] = "0"*64
    with pytest.raises(gate.GateBlocked, match="approval_master_sha256_mismatch"):
        gate.authorize_sequence(data, folder, pre, master, path, anchors, approval)


def test_verified_receipt_allows_sequence_but_never_production(sample):
    folder, data = sample
    pre, path, anchors, master = valid_master(sample)
    approval = {"decision": "approved", "approved_by": "owner", "state": "idle",
                "spec_sha256": master["spec_sha256"], "master_sha256": master["master_sha256"],
                "anchors_sha256": master["anchors_sha256"],
                "confirmation_reference": "SYNTHETIC_TEST_RECORD_ONLY"}
    permit = gate.authorize_sequence(data, folder, pre, master, path, anchors, approval)
    assert permit["sequence_generation_allowed"]
    assert not permit["production_release_allowed"]
    assert "authenticity" in permit["warning"]


def test_tampered_anchor_grid_invalidates_master_receipt(sample):
    folder, data = sample
    pre, path, anchors, master = valid_master(sample)
    anchors["anchors_px"]["face_center"] = [780, 650]
    with pytest.raises(gate.GateBlocked, match="master_receipt_missing_or_stale"):
        gate.authorize_sequence(data, folder, pre, master, path, anchors, {})
