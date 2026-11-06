"""Phase 8 local installation acceptance: no real provider calls or art commits."""
from __future__ import annotations

import asyncio
import json

import pytest

from tools import phase8_a0_local_acceptance as gate

SHA = "d" * 64


def reports(geometry=False):
    status = ("technical_and_annotated_geometry_ready_for_human_review"
              if geometry else "awaiting_image_bound_annotations")
    telemetry = {
        "schema": "exodia.phase6-phase7-local-readiness/v1",
        "build_sha": "f" * 40,
        "phase7": {
            "character_id": "liu_bei", "watcher_state": "running",
            "intake_status": status, "check_sequence": 5,
            "original_sha256": SHA, "telemetry_consistent": True,
            "technical_source_pass": True,
            "geometry_ready_for_owner_review": geometry,
            "owner_identity_approval": "pending",
            "five_state_staging_authorized": False,
            "production_release_enabled": False,
        }
    }
    local = {
        "schema": "exodia.liu_bei-a0-manual-intake/v1",
        "character_id": "liu_bei", "candidate_sha256": SHA,
        "technical_source_pass": True,
        "annotated_geometry_consistency_pass": geometry, "status": status,
        "owner_identity_approval": "pending",
        "production_release_enabled": False,
        "inbox": "C:/PRIVATE_USER/liu_bei_a0_inbox",
        "candidate": {"filename": "C:/PRIVATE_USER/secret.png"},
        "private_instructions": "DO_NOT_LEAK",
    }
    return telemetry, local


def test_installed_a0_technical_pass_is_not_visual_approval():
    report = gate.correlate_installed_a0(*reports())
    assert report["native_png_technical_pass"] is True
    assert report["formatted_native_png_sha256"] == SHA
    assert report["pixel_bound_geometry_pass"] is False
    assert report["formatted_native_source_owner_approval"] == "not_established_by_gate"
    assert report["production_release_enabled"] is False
    assert report["next_gate"] == "annotate_actual_pixels_and_stamp_sha_bound_patches"
    text = json.dumps(report)
    for secret in ("PRIVATE_USER", "secret.png", "DO_NOT_LEAK"):
        assert secret not in text


def test_geometry_evidence_only_unlocks_human_review_not_five_state_staging():
    report = gate.correlate_installed_a0(*reports(geometry=True))
    assert report["pixel_bound_geometry_pass"] is True
    assert report["next_gate"] == "human_exact_sha_visual_and_anatomy_review"
    assert report["five_state_staging_authorized"] is False
    assert report["native_source_production_release_authorized"] is False
    assert report["formatted_native_png_sha256"] == SHA
    assert report["a0_original_visual_approval_sha256"] != SHA


def test_watcher_sha_mismatch_cannot_report_native_installation_success():
    telemetry, local = reports(geometry=True)
    telemetry["phase7"]["original_sha256"] = "e" * 64
    result = gate.correlate_installed_a0(telemetry, local)
    assert result["watcher_and_local_byte_sha_agree"] is False
    assert result["formatted_native_png_sha256"] is None
    assert result["native_png_technical_pass"] is False
    assert result["pixel_bound_geometry_pass"] is False


@pytest.mark.parametrize("field,value", [
    ("telemetry_consistent", False), ("watcher_state", "error"),
    ("check_sequence", 0), ("technical_source_pass", False)
])
def test_missing_watch_proof_fails_closed(field, value):
    t, s = reports(geometry=True)
    t["phase7"][field] = value
    result = gate.correlate_installed_a0(t, s)
    assert result["native_png_technical_pass"] is False
    assert result["pixel_bound_geometry_pass"] is False


def test_source_missing_and_forged_approval_are_not_passed():
    t, s = reports(geometry=True)
    s["candidate_sha256"] = None
    result = gate.correlate_installed_a0(t, s)
    assert result["installed_candidate_seen"] is False
    assert result["formatted_native_png_sha256"] is None
    t, s = reports()
    t["phase7"]["production_release_enabled"] = True
    with pytest.raises(ValueError, match="release gate"):
        gate.correlate_installed_a0(t, s)
    t, s = reports()
    s["owner_identity_approval"] = "approved"
    with pytest.raises(ValueError, match="release gate"):
        gate.correlate_installed_a0(t, s)


def test_actual_inspection_invokes_live_get_monitor_and_local_byte_scan(monkeypatch, tmp_path):
    root = tmp_path / "orchestrator"
    (root / "app/companions").mkdir(parents=True)
    (root / "app/companions/roster.json").write_text("[]", encoding="utf-8")
    telemetry, local = reports(True)
    called = []
    async def monitor_collect(client):
        called.append(("api", str(client.base_url)))
        return telemetry
    def scan(local_root):
        called.append(("bytes", str(local_root)))
        return local
    monkeypatch.setattr(gate, "_validate_registry", lambda root: called.append(("registry", str(root))))
    monkeypatch.setattr(gate.monitor, "collect", monitor_collect)
    monkeypatch.setattr(gate, "scan_dropin", scan)
    result = asyncio.run(gate.inspect(root, "http://127.0.0.1:8767"))
    assert result["pixel_bound_geometry_pass"] is True
    assert [x[0] for x in called] == ["registry", "api", "bytes"]
    with pytest.raises(ValueError):
        asyncio.run(gate.inspect(root, "https://external.example.com"))


def test_cli_redaction_and_exit_statuses(monkeypatch, capsys):
    async def geometry(*args):
        return gate.correlate_installed_a0(*reports(geometry=True))
    async def no_geometry(*args):
        return gate.correlate_installed_a0(*reports(geometry=False))
    monkeypatch.setattr(gate, "inspect", geometry)
    assert gate.main([]) == 0
    assert json.loads(capsys.readouterr().out)["pixel_bound_geometry_pass"] is True
    monkeypatch.setattr(gate, "inspect", no_geometry)
    assert gate.main([]) == 1
    assert json.loads(capsys.readouterr().out)["native_png_technical_pass"] is True
    async def failure(*args):
        raise RuntimeError("PRIVATE_HOME_PATH secret password")
    monkeypatch.setattr(gate, "inspect", failure)
    assert gate.main([]) == 2
    assert "PRIVATE_HOME_PATH" not in capsys.readouterr().err
