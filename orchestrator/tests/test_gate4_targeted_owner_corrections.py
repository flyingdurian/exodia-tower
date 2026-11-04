"""Gate 4 targeted four-state correction contract regression tests.

Real 33-image originals remain in the repository; none of these tests
manufactures a replacement source or grants production approval.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import pytest
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "orchestrator" / "tools"))
from apply_gate4_four_corrections import (TARGETS, verify_locked_29,
                                          check_metadata, validate_original_png,
                                          preflight, sha)
from app.companions.state33_review_assets import manifest
from app.config import Settings


def test_exact_29_owner_accepted_and_four_rejected_states_are_frozen():
    c = json.loads((ROOT / "assets" / "review" / "albedo_core5" /
                    "gate4_four_state_correction_lock.json").read_text())
    assert c["schema"] == "exodia.gate4-four-state-owner-correction-lock/v1"
    assert set(c["target_states"]) == set(TARGETS)
    assert len(c["frozen_review_hashes"]) == 33
    assert c["protected_count"] == 29
    assert c["owner_final_production_approval"] is False
    assert c["release_enabled"] is False
    assert c["no_dashboard_or_contact_sheet_extraction"] is True
    assert c["review_board_sha256"] == (
        "f1b9e71ab0d2410f229918bdbef20e0f8bb1b9cf46b30354c742be5cb6b3be4d")
    frozen = [k for k,v in c["frozen_review_hashes"].items()
              if v["development_review_status"]=="OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT"]
    assert len(frozen)==29
    assert set(frozen).isdisjoint(TARGETS)
    assert len(c["correction_briefs"])==4
    assert all(c["correction_briefs"][s]["old_original_sha256"] for s in TARGETS)
    assert all(c["correction_briefs"][s]["old_review_sha256"] for s in TARGETS)


def test_real_29_original_and_review_files_remain_byte_identical_to_owner_review():
    result = verify_locked_29(ROOT)
    assert result["locked_29_verified"] == 29
    assert result["unapproved_replacements"] in (0,4)
    assert len(result["frozen_hashes"]) >= 29


def test_real_api_exposes_correct_review_status_but_zero_final_approvals():
    api = manifest(Settings().root)
    assert api["count"] == 33
    assert api["owner_development_accepted_count"] == 29
    assert api["owner_targeted_correction_count"] == 4
    assert api["production_release_enabled"] is False
    assert api["native_core_five_certified_count"] == 0
    assert api["owner_production_approved_count"] == 0
    assert api["artwork_available_count"] == 33
    assert all(api["states"][s]["owner_development_status"] in (
        "CORRECTION_REQUIRED", "CORRECTION_RENDERED_OWNER_REVIEW_PENDING") for s in TARGETS)
    assert sum(x["owner_development_status"]=="OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT"
               for x in api["states"].values())==29
    assert all(x["owner_approved"] is False for x in api["states"].values())


VALID = {
    "source_sha256": "a"*64, "source_dimensions":[1856,2304],
    "generator_model":"authorized_independent_image_generator",
    "generator_job_id":"unique-job-id-1001",
    "generation_input_manifest_sha256":"b"*64,
    "pose_evidence_description":("Independently composed full-body gesture and facial acting "
                                 "with naturally connected wrists and authentic anime Albedo design."),
    "derived_from_composite":False,
    "owner_approved":False,
    "production_release_enabled":False,
}


@pytest.mark.parametrize("patch,message", [
    ({"generator_model":"Runway nano-banana-2"},"runway_prohibited"),
    ({"generator_model":"rUnWaY"},"runway_prohibited"),
    ({"owner_approved":True},"fake_owner"),
    ({"production_release_enabled":True},"fake_owner"),
    ({"approved_by":"owner"},"fake_owner"),
    ({"derived_from_composite":True},"contact_sheet_or_composite"),
    ({"generator_job_id":""},"independent_generation_job"),
    ({"generation_input_manifest_sha256":None},"generation_request"),
    ({"pose_evidence_description":"raised hand"},"original_pose_evidence"),
])
def test_forbidden_model_fake_approval_or_ambiguous_pose_cannot_enter(patch,message):
    item = dict(VALID, **patch)
    with pytest.raises(ValueError,match=message):
        check_metadata("angered",item)


def test_out_of_scope_state_rejected_even_with_provenance():
    with pytest.raises(ValueError,match="unauthorized_replacement_state"):
        check_metadata("celebrating",VALID)


def test_no_artwork_or_metadata_is_pretended_when_zip_missing(tmp_path):
    with pytest.raises(ValueError,match="missing_or_oversized_correction_zip"):
        preflight(ROOT,tmp_path/"four_fake_sources.zip")


def test_real_native_resolution_geometry_must_be_genuine_file_bytes():
    with pytest.raises(ValueError,match="invalid_individual_source_size"):
        validate_original_png(b"fakeimage","neutral",[1536,1920])


def test_four_old_images_are_present_but_not_marked_as_corrected_or_production():
    lock = json.loads((ROOT/"assets/review/albedo_core5"/
                       "gate4_four_state_correction_lock.json").read_text())
    for state in TARGETS:
        item = lock["correction_briefs"][state]
        if item["status"]=="PENDING_NEW_STANDALONE_ARTWORK":
            assert item["new_original_sha256"] is None
            assert item["new_review_sha256"] is None
            assert lock["frozen_review_hashes"][state]["development_review_status"]=="CORRECTION_REQUIRED"
        else:
            assert item["status"]=="RENDERED_PENDING_OWNER"
            assert item["new_original_sha256"]
            assert item["new_review_sha256"]
        assert item["owner_final_visual_review"]=="PENDING"
