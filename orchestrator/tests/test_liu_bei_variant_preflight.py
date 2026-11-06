"""Offline-only Phase 7 Liu Bei four-variant preflight; test art is synthetic."""
from __future__ import annotations

import asyncio
import json
import shutil

import httpx
import pytest
from PIL import Image, ImageDraw

from app.api import server
from app.fleet.liu_bei_variant_preflight import (
    VARIANTS, SCHEMA, A0_APPROVED_VISUAL_ORIGINAL_SHA, liu_bei_variant_preflight
)
from tools.liu_bei_manual_dropin import POINTS, stamp_patches, template_for
from tools.liu_bei_native_identity_gate import ROOT, PILOT_MANIFEST, LOCKED, sha256


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "frontend/companions/source_masters").mkdir(parents=True)
    (root / "app/companions").mkdir(parents=True)
    pilot = tmp_path / "assets/review/liu_bei_pilot"
    pilot.mkdir(parents=True)
    shutil.copyfile(ROOT / "frontend/companions/source_masters/router.png",
                    root / "frontend/companions/source_masters/router.png")
    shutil.copyfile(ROOT / "app/companions/roster.json",
                    root / "app/companions/roster.json")
    shutil.copyfile(PILOT_MANIFEST, pilot / "pilot_manifest.json")
    shutil.copyfile(ROOT.parent / "assets/review/liu_bei_pilot/variant_registry.json",
                    pilot / "variant_registry.json")
    return root


def synthetic_state(path):
    image = Image.new("RGB", LOCKED)
    draw = ImageDraw.Draw(image)
    for y in range(0, LOCKED[1], 64):
        for x in range(0, LOCKED[0], 64):
            draw.rectangle((x, y, x + 63, y + 63),
                           fill=((x * 3 + y) % 256, (y * 7 + x) % 256,
                                 ((x + y) // 7) % 256))
    image.save(path)


def test_four_placeholders_are_not_registered_art(isolated):
    report = liu_bei_variant_preflight(isolated)
    assert report["schema"] == SCHEMA
    assert report["character_id"] == "liu_bei"
    assert tuple(item["key"] for item in report["states"]) == tuple(VARIANTS)
    assert report["approved_a0_original_visual_sha256"] == A0_APPROVED_VISUAL_ORIGINAL_SHA
    assert report["formatted_a0_native_sha256"] is None
    assert report["a0_native_technical_pass"] is False
    assert report["automatic_registration_enabled"] is False
    assert report["production_release_enabled"] is False
    assert report["five_state_staging_authorized"] is False
    assert all(s["asset_url"] is None and s["owner_state_approval"] == "pending" and
               s["status"] == "awaiting_independent_state_source" for s in report["states"])
    assert not (isolated / "app_data/liu_bei_variant_inbox").exists()


def test_candidate_format_passes_without_owner_source_or_geometry_approval(isolated):
    inbox = isolated / "app_data/liu_bei_variant_inbox"
    inbox.mkdir(parents=True)
    candidate = inbox / "confident.png"
    synthetic_state(candidate)
    report = liu_bei_variant_preflight(isolated)
    accepted = report["states"][0]
    assert accepted["status"] == "awaiting_image_bound_annotations"
    assert accepted["technical_source_pass"] is True
    assert accepted["candidate_sha256"] == sha256(candidate)
    assert accepted["geometry_ready_for_owner_review"] is False
    assert accepted["source_authenticity_verified"] is False
    assert accepted["owner_state_approval"] == "pending"
    assert accepted["asset_url"] is None
    assert report["states"][1]["candidate_sha256"] is None


def test_image_bound_geometry_remains_human_review_not_release(isolated):
    inbox = isolated / "app_data/liu_bei_variant_inbox"
    inbox.mkdir(parents=True)
    candidate = inbox / "working.png"
    synthetic_state(candidate)
    sidecar = candidate.with_suffix(".landmarks.json")
    annotations = template_for(candidate)
    assert all(annotations["landmarks"][key] is None for key in POINTS)
    annotations["landmarks"] = {
        "left_iris_center": [610, 634], "right_iris_center": [902, 634],
        "left_shoulder_joint": [505, 980], "right_shoulder_joint": [1035, 980],
        "head_left": [461, 620], "head_right": [1075.4, 620],
    }
    sidecar.write_text(json.dumps(annotations), encoding="utf-8")
    stamp_patches(candidate, sidecar)
    review = liu_bei_variant_preflight(isolated)
    item = review["states"][2]
    assert item["status"] == "technical_geometry_ready_for_human_review"
    assert item["image_bound_annotation_consistency"] is True
    assert item["geometry_ready_for_owner_review"] is True
    assert item["owner_state_approval"] == "pending"
    assert item["production_release_enabled"] is False
    assert item["asset_url"] is None
    candidate.with_suffix(".landmarks.json").write_text(
        '{"schema": "invalid"}', encoding="utf-8"
    )
    changed = liu_bei_variant_preflight(isolated)["states"][2]
    assert changed["status"] == "rejected_annotations"
    assert changed["geometry_ready_for_owner_review"] is False


def test_registry_forged_approval_and_source_are_rejected(isolated):
    registry = isolated.parent / "assets/review/liu_bei_pilot/variant_registry.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["states"]["angered"]["owner_approval_reference"] = "fabricated"
    registry.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="registry mutation"):
        liu_bei_variant_preflight(isolated)
    data["states"]["angered"]["owner_approval_reference"] = None
    data["production_release_enabled"] = True
    registry.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="registry contract changed"):
        liu_bei_variant_preflight(isolated)


def test_unknown_variant_name_and_symlink_folder_fail_closed(isolated, tmp_path):
    inbox = isolated / "app_data/liu_bei_variant_inbox"
    inbox.mkdir(parents=True)
    (inbox / "mira.png").write_bytes(b"not an authorized companion source")
    with pytest.raises(ValueError, match="Unexpected"):
        liu_bei_variant_preflight(isolated)
    (inbox / "mira.png").unlink()
    inbox.rmdir()
    outside = tmp_path / "private_folder"
    outside.mkdir()
    try:
        inbox.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Filesystem does not support safe symlink test")
    with pytest.raises(ValueError, match="Unsafe variant intake"):
        liu_bei_variant_preflight(isolated)


def test_local_api_is_read_only_and_redacts_original_artwork(monkeypatch, isolated):
    async def run():
        monkeypatch.setattr(
            server, "liu_bei_variant_preflight",
            lambda root: liu_bei_variant_preflight(isolated)
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            path = "/api/fleet/liu_bei/variant-preflight"
            assert (await client.get(path)).status_code == 403
            response = await client.get(
                path, headers={"X-Exodia-Client": "exodia-dashboard"}
            )
            assert response.status_code == 200
            assert len(response.json()["states"]) == 4
            assert "source_masters/router.png" not in response.text
            assert "production_release_enabled" in response.text
            assert not (isolated / "app_data/liu_bei_variant_inbox").exists()
    asyncio.run(run())
