"""Phase 11: strict, art-free fleet readiness across the original ten agents."""
from __future__ import annotations

import asyncio
import json
import random
import shutil

import httpx
import pytest

from app.api import server
from app.fleet.fleet_readiness import (
    EXPECTED_IDS, SCHEMA, fleet_projection, lifecycle, validate_fleet_policy
)
from app.operations.inbox import Inbox
from tools.liu_bei_native_identity_gate import ROOT, PILOT_MANIFEST


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "app/companions").mkdir(parents=True)
    (root / "frontend/companions/production/kiko").mkdir(parents=True)
    fleet = tmp_path / "assets/review/fleet"
    fleet.mkdir(parents=True)
    pilot = tmp_path / "assets/review/liu_bei_pilot"
    pilot.mkdir(parents=True)
    for relative in (
        "app/companions/roster.json",
        "frontend/companions/roster.json",
        "frontend/companions/production/kiko/portrait_registry.json",
    ):
        shutil.copyfile(ROOT / relative, root / relative)
    shutil.copyfile(PILOT_MANIFEST, pilot / "pilot_manifest.json")
    shutil.copyfile(ROOT.parent / "assets/review/fleet/phase11_rollout_policy.json",
                    fleet / "phase11_rollout_policy.json")
    return root


def test_ten_stable_ids_unchanged_roster_and_330_art_free_contracts(isolated):
    roster, policy = validate_fleet_policy(isolated)
    assert tuple(entry["id"] for entry in roster) == EXPECTED_IDS
    assert len(roster) == len(policy) == 10
    output = fleet_projection(isolated)
    assert output["schema"] == SCHEMA
    assert output["fleet_count"] == 10
    assert output["planned_contract_slots"] == 330
    assert output["states_per_companion"] == 33
    assert output["native_33_production_released_count"] == 0
    assert output["production_release_enabled"] is False
    assert output["automatic_social_publishing"] is False
    assert output["remote_task_dispatch_performed"] is False
    assert all(x["review_asset_url"] is None for x in output["companions"])
    assert all(x["existing_portrait_workflow_unchanged"] is True
               for x in output["companions"])


def test_no_art_folders_or_source_masters_created_by_fleet_status(isolated):
    before = sorted(x.relative_to(isolated.parent).as_posix()
                    for x in isolated.parent.rglob("*") if x.is_file())
    for agent in EXPECTED_IDS:
        report = fleet_projection(isolated, selected_agent=agent)
        assert report["selected_agent"] == agent
        assert report["task_lifecycle"] == "idle"
        assert report["canonical_review_state"] == "neutral"
        assert report["production_release_enabled"] is False
    after = sorted(x.relative_to(isolated.parent).as_posix()
                   for x in isolated.parent.rglob("*") if x.is_file())
    assert before == after
    assert not (isolated / "app_data").exists()


def test_real_task_states_are_sanitized_and_never_infer_anger_or_approval(isolated):
    transitions = {
        "draft": ("idle", "neutral"), "running": ("active", "working"),
        "awaiting_operator": ("waiting", "awaiting_command"),
        "answered": ("completed", "confident"),
        "failed": ("interrupted", "concerned"),
        "cancelled": ("cancelled", "neutral"),
        "waiting_for_reply": ("waiting", "awaiting_command"),
    }
    for agent in EXPECTED_IDS:
        for state, expected in transitions.items():
            task = {
                "id": "safe-task-id-1", "agent_id": agent, "state": state,
                "prompt": "SECRET_PRIVATE_PROMPT", "answer": "SECRET_PRIVATE_ANSWER",
                "private_instructions": "SECRET_PRIVATE_INSTRUCTIONS",
            }
            result = fleet_projection(isolated, selected_agent=agent, task=task)
            assert (result["task_lifecycle"], result["canonical_review_state"]) == expected
            text = json.dumps(result)
            for phrase in ("SECRET_PRIVATE_PROMPT", "SECRET_PRIVATE_ANSWER",
                           "SECRET_PRIVATE_INSTRUCTIONS"):
                assert phrase not in text
            assert result["production_release_enabled"] is False


def test_5000_deterministic_events_always_resolve_to_allowed_review_states():
    rng = random.Random(20261106)
    values = (
        "queued", "cooldown", "opening", "typing", "submitting", "running",
        "researching", "rendering_media", "waiting_for_reply", "awaiting_operator",
        "answered", "failed", "cancelled", "draft", "unrecognized_state",
    )
    counts = {}
    for _ in range(5000):
        value = lifecycle({"state": rng.choice(values),
                           "prompt": "FAKE_PROMPT_NEVER_READ"})
        counts[value] = counts.get(value, 0) + 1
        assert value in {"idle", "active", "waiting", "completed",
                         "interrupted", "cancelled"}
    assert all(counts.get(x, 0) > 0
               for x in ("idle", "active", "waiting", "completed",
                         "interrupted", "cancelled"))


def test_fleet_policy_forged_approval_and_source_replacements_fail_closed(isolated):
    policy_path = isolated.parent / "assets/review/fleet/phase11_rollout_policy.json"
    original = json.loads(policy_path.read_text("utf-8"))
    for key, value in [
        ("automatic_remote_provider_dispatch", True),
        ("automatic_social_publishing", True),
        ("owner_release_authorized", True),
    ]:
        fake = json.loads(json.dumps(original))
        fake[key] = value
        policy_path.write_text(json.dumps(fake), encoding="utf-8")
        with pytest.raises(ValueError, match="policy"):
            validate_fleet_policy(isolated)
    fake = json.loads(json.dumps(original))
    fake["companions"][5]["source_master_replacement_authorized"] = True
    policy_path.write_text(json.dumps(fake), encoding="utf-8")
    with pytest.raises(ValueError, match="ownership"):
        validate_fleet_policy(isolated)


def test_legacy_albedo_and_liu_bei_approval_drift_fail_closed(isolated):
    albedo = isolated / "frontend/companions/production/kiko/portrait_registry.json"
    data = json.loads(albedo.read_text("utf-8"))
    data["release"]["enabled"] = True
    albedo.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Albedo"):
        validate_fleet_policy(isolated)
    data["release"]["enabled"] = False
    albedo.write_text(json.dumps(data), encoding="utf-8")
    pilot = isolated.parent / "assets/review/liu_bei_pilot/pilot_manifest.json"
    source = json.loads(pilot.read_text("utf-8"))
    source["states"]["confident"]["source_sha256"] = "f" * 64
    pilot.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="Unapproved Liu Bei"):
        validate_fleet_policy(isolated)


def test_fleet_ownership_cannot_be_bypassed_with_another_agent_task(isolated):
    with pytest.raises(ValueError, match="belongs to another"):
        fleet_projection(isolated, selected_agent="vault",
                         task={"id": "local-1", "agent_id": "ninja", "state": "running"})
    with pytest.raises(ValueError, match="Unknown EXODIA"):
        fleet_projection(isolated, selected_agent="unknown-agent")
    with pytest.raises(ValueError, match="Invalid local task"):
        fleet_projection(isolated, selected_agent="vault",
                         task={"id": "../private", "agent_id": "vault", "state": "running"})


def test_local_fleet_api_guarded_task_owner_and_privacy(monkeypatch, isolated, tmp_path):
    async def run():
        monkeypatch.setattr(server, "inbox", Inbox(tmp_path / "phase11.sqlite"))
        from app.fleet import fleet_readiness as fleet_service
        original_projection = fleet_service.fleet_projection
        monkeypatch.setattr(
            fleet_service, "fleet_projection",
            lambda root, **kw: original_projection(isolated, **kw)
        )
        a = server.inbox.create("vault", "ollama", "PRIVATE_VAULT_TEXT")
        b = server.inbox.create("ninja", "ollama", "PRIVATE_NINJA_TEXT")
        server.inbox.update(a["id"], "state", "running")
        h = {"X-Exodia-Client": "exodia-dashboard"}
        path = "/api/fleet/readiness"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            assert (await client.get(path)).status_code == 403
            assert (await client.get(path, headers=h,
                 params={"selected_agent": "fake"})).status_code == 422
            assert (await client.get(path, headers=h,
                 params={"selected_agent": "ninja", "task_id": a["id"]})).status_code == 409
            assert (await client.get(path, headers=h,
                 params={"selected_agent": "vault", "task_id": "not-existing"})).status_code == 404
            response = await client.get(path, headers=h,
                params={"selected_agent": "vault", "task_id": a["id"]})
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["fleet_count"] == 10
            assert body["planned_contract_slots"] == 330
            assert body["task_lifecycle"] == "active"
            assert body["native_33_production_released_count"] == 0
            assert "PRIVATE_VAULT_TEXT" not in response.text
            assert "PRIVATE_NINJA_TEXT" not in response.text
    asyncio.run(run())


def test_fleet_review_does_not_duplicate_legacy_chibi_controls():
    html = (ROOT / "frontend/albedo_command.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend/fleet_readiness_boot.mjs").read_text(encoding="utf-8")
    assert 'id="fleetReadinessPanel" class="fleet-review-controls"' in html
    assert html.count('class="chibi-test-controls"') == 1
    assert "fleet_readiness_boot.mjs" in html
    assert "/api/fleet/readiness" in script
    assert "remote_task_dispatch" not in script
