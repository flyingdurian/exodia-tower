"""Phase 6/7 local-only monitor contracts. These tests never dispatch a provider."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from tools import phase6_phase7_local_monitor as monitor


def fixtures(*, ready=False):
    status = ("technical_and_annotated_geometry_ready_for_human_review"
              if ready else "awaiting_image_bound_annotations")
    sha = "a" * 64
    watcher = {
        "schema": "exodia.phase5.liu_bei-a0-watch-telemetry/v1",
        "watcher_state": "running", "intake_status": status,
        "check_sequence": 4, "last_checked_utc": "2026-11-05T00:01:00Z",
        "last_transition_utc": "2026-11-05T00:01:00Z",
        "original_sha256": sha, "technical_source_pass": True,
        "image_bound_annotation_consistency": ready,
        "geometry_ready_for_owner_review": ready,
        "five_state_staging_authorized": False,
        "owner_identity_approval": "pending",
        "production_release_enabled": False,
        "native_production_certified": False,
    }
    preflight = {
        "schema": "exodia.phase5.liu_bei-a0-preflight/v1",
        "character_id": "liu_bei", "intake_status": status,
        "original_sha256": sha, "technical_source_pass": True,
        "image_bound_annotation_consistency": ready,
        "production_release_enabled": False, "native_production_certified": False,
        "owner_identity_approval": "pending",
        "independent_original_authorship_verified": False,
    }
    runtime = {
        "schema": "exodia.phase7.liu_bei-five-state-review/v1",
        "character_id": "liu_bei", "production_release_enabled": False,
        "owner_identity_approval": "pending",
        "independent_original_authorship_verified": False,
        "display": {"mode": "review_only_fallback", "asset_url": None},
        "states": [{"key": name, "asset_url": None,
                    "art_status": "awaiting_exact_sha_owner_approval"}
                   for name in monitor.EXPECTED],
    }
    health = {
        "schema": "exodia.command-history-health/v1", "status": "ok",
        "journal_mode": "wal", "total_tasks": 3, "total_events": 7,
        "retry_attempts": 1, "error_events": 0,
    }
    catalog = {
        "build_sha": "b" * 40, "provider_status": {
            name: {"mode": "local" if name == "ollama" else "browser",
                   "observed_state": "ready_for_next_prompt"}
            for name in monitor.probe.MODELS}
    }
    return watcher, preflight, runtime, health, catalog


def test_geometry_preflight_is_not_approval_or_five_state_release():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    result = monitor.correlate(watcher, preflight, runtime, health, catalog)
    assert result["phase7"]["geometry_ready_for_owner_review"] is True
    assert result["phase7"]["next_gate"] == "exact_sha_human_visual_review"
    assert result["phase7"]["original_sha256"] == "a" * 64
    assert result["phase7"]["five_state_staging_authorized"] is False
    assert result["phase7"]["production_release_enabled"] is False
    assert result["phase7"]["owner_identity_approval"] == "pending"
    assert result["phase6"]["authenticated_acceptance"] == "not_established_by_status"
    assert result["phase6"]["sqlite"]["total_tasks"] == 3


def test_mismatched_or_stale_watch_snapshot_fail_closed_without_sha():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    watcher["intake_status"] = "awaiting_image_bound_annotations"
    result = monitor.correlate(watcher, preflight, runtime, health, catalog)
    assert result["phase7"]["telemetry_consistent"] is False
    assert result["phase7"]["geometry_ready_for_owner_review"] is False
    assert result["phase7"]["original_sha256"] is None
    watcher["watcher_state"] = "error"
    assert monitor.correlate(watcher, preflight, runtime, health, catalog)[
        "phase7"]["five_state_staging_authorized"] is False


def test_no_native_master_requires_annotation_and_review():
    values = fixtures()
    result = monitor.correlate(*values)
    assert result["phase7"]["technical_source_pass"] is True
    assert result["phase7"]["geometry_ready_for_owner_review"] is False
    assert result["phase7"]["next_gate"] == "native_png_and_image_bound_landmark_preflight"


def test_any_review_state_image_or_policy_unlock_is_rejected():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    runtime["states"][2]["asset_url"] = "/some-unapproved-art.png"
    with pytest.raises(ValueError):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    runtime["states"][2]["asset_url"] = None
    watcher["five_state_staging_authorized"] = True
    with pytest.raises(ValueError):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    watcher["five_state_staging_authorized"] = False
    runtime["character_id"] = "router"
    with pytest.raises(ValueError):
        monitor.correlate(watcher, preflight, runtime, health, catalog)


def test_unapproved_runtime_display_cannot_bypass_per_state_asset_gate():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    runtime["display"]["asset_url"] = "/unapproved-portrait.png"
    with pytest.raises(ValueError, match="artwork-free"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    runtime["display"]["asset_url"] = None
    runtime["display"]["mode"] = "production"
    with pytest.raises(ValueError, match="artwork-free"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)


def test_unsafe_native_release_and_authorship_claims_fail_closed():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    preflight["native_production_certified"] = True
    with pytest.raises(ValueError, match="artwork lock"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    preflight["native_production_certified"] = False
    runtime["independent_original_authorship_verified"] = True
    with pytest.raises(ValueError, match="artwork lock"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    runtime["independent_original_authorship_verified"] = False
    watcher["owner_identity_approval"] = "approved"
    with pytest.raises(ValueError, match="artwork lock"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)


def test_malformed_review_states_raise_redacted_contract_error():
    watcher, preflight, runtime, health, catalog = fixtures(ready=True)
    runtime["states"][0] = "NOT_A_STATE_WITH_PRIVATE_DATA"
    with pytest.raises(ValueError, match="Five-state review contract changed"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)
    runtime["states"] = []
    with pytest.raises(ValueError, match="Five-state review contract changed"):
        monitor.correlate(watcher, preflight, runtime, health, catalog)


def test_full_monitor_collect_is_get_only_and_redacted(monkeypatch):
    async def run():
        watcher, preflight, runtime, health, catalog = fixtures(ready=True)
        routes = {
            "/api/fleet/liu_bei-a0/watch-status": watcher,
            "/api/fleet/liu_bei-a0/preflight": preflight,
            "/api/fleet/liu_bei/pilot-runtime": runtime,
            "/api/command/history-health": health,
        }
        async def fake_catalog(client):
            return catalog
        monkeypatch.setattr(monitor.probe, "get_catalog", fake_catalog)
        seen = []
        def handler(req):
            seen.append((req.method, req.url.path, req.headers.get("x-exodia-client")))
            return httpx.Response(200, json=routes.get(req.url.path, {}))
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://127.0.0.1:8767"
        ) as client:
            report = await monitor.collect(client)
        assert len(seen) == 4
        assert all(method == "GET" and header == "exodia-dashboard"
                   for method, _path, header in seen)
        assert report["phase7"]["geometry_ready_for_owner_review"] is True
        serialized = json.dumps(report)
        assert "private_instructions" not in serialized
        assert "password" not in serialized
        assert "api_key" not in serialized
    asyncio.run(run())


def test_monitor_rejects_external_host_and_invalid_cadence():
    with pytest.raises(ValueError):
        monitor.probe.loopback_url("https://chatgpt.com")
    assert monitor.parse_args([]).watch is False
    assert monitor.parse_args(["--watch", "--interval", "2"]).watch is True
    async def run():
        args = monitor.parse_args(["--interval", ".1"])
        with pytest.raises(ValueError):
            await monitor.main_async(args)
    asyncio.run(run())
