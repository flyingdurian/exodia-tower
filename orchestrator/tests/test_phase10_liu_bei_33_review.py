"""Phase 10: 33-state Liu Bei review engineering; no art approval or provider calls."""
from __future__ import annotations

import asyncio
import json
import shutil

import httpx
import pytest

from app.api import server
from app.fleet.liu_bei_33_review import (
    validate_library, phase10_projection, SCHEMA
)
from app.operations.inbox import Inbox
from tools.liu_bei_native_identity_gate import ROOT, PILOT_MANIFEST


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "frontend/companions/source_masters").mkdir(parents=True)
    (root / "frontend/companions/production/kiko").mkdir(parents=True)
    (root / "app/companions").mkdir(parents=True)
    pilot = tmp_path / "assets/review/liu_bei_pilot"
    pilot.mkdir(parents=True)
    shutil.copyfile(ROOT / "frontend/companions/source_masters/router.png",
                    root / "frontend/companions/source_masters/router.png")
    shutil.copyfile(ROOT / "frontend/companions/production/kiko/portrait_registry.json",
                    root / "frontend/companions/production/kiko/portrait_registry.json")
    shutil.copyfile(ROOT / "app/companions/roster.json",
                    root / "app/companions/roster.json")
    shutil.copyfile(PILOT_MANIFEST, pilot / "pilot_manifest.json")
    shutil.copyfile(ROOT.parent / "assets/review/liu_bei_pilot/phase10_33_state_registry.json",
                    pilot / "phase10_33_state_registry.json")
    return root


def test_exact_33_keys_and_20_13_categories_match_untouched_albedo_vocabulary(isolated):
    manifest, keys = validate_library(isolated)
    actual = list(manifest["states"])
    assert len(keys) == len(actual) == 33
    assert len(set(keys)) == 33
    assert sum(x["category"] == "expression" for x in actual) == 20
    assert sum(x["category"] == "action" for x in actual) == 13
    assert set(("neutral", "confident", "angered", "working", "pointing")).issubset(keys)
    assert all(x["source_sha256"] is None for x in actual)
    assert all(x["owner_approval_reference"] is None for x in actual)
    assert all(x["asset_url"] is None for x in actual)


def test_review_returns_all_33_as_text_only_without_release(isolated):
    for state in ("neutral", "happy", "monitoring", "thinking_deeper", "awaiting_command"):
        r = phase10_projection(isolated, preview_state=state)
        assert r["schema"] == SCHEMA
        assert r["selected_state"] == state
        assert r["review_preview"] is True
        assert r["display"]["asset_url"] is None
        assert r["source_count"] == r["approved_native_state_count"] == 0
        assert r["production_release_enabled"] is False
        assert len(r["states"]) == 33
        assert all(s["owner_approved"] is False and
                   s["source_verified"] is False and
                   s["asset_url"] is None for s in r["states"])


def test_live_task_maps_into_legacy_five_without_promoting_unapproved_art(isolated):
    for task_state, expected in [
        ("draft", "neutral"), ("running", "working"), ("answered", "confident"),
        ("failed", "neutral"), ("cancelled", "neutral"),
    ]:
        task = {
            "id": "task-safe-99", "agent_id": "liu_bei", "state": task_state,
            "prompt": "SECRET_PROMPT_DO_NOT_LEAK",
            "answer": "SECRET_ANSWER_DO_NOT_LEAK",
            "private_instructions": "SECRET_PRIVATE_DO_NOT_LEAK",
        }
        result = phase10_projection(isolated, task=task)
        assert result["selected_state"] == expected
        assert result["task_id"] == "task-safe-99"
        for private in ("SECRET_PROMPT_DO_NOT_LEAK",
                        "SECRET_ANSWER_DO_NOT_LEAK",
                        "SECRET_PRIVATE_DO_NOT_LEAK"):
            assert private not in json.dumps(result)


def test_review_does_not_allow_cross_agent_preview_or_unknown_state(isolated):
    with pytest.raises(ValueError, match="not owned"):
        phase10_projection(isolated, task={"agent_id": "kiko", "state": "running"},
                           preview_state="celebrating")
    with pytest.raises(ValueError, match="Unsupported canonical"):
        phase10_projection(isolated, preview_state="../albedo.png")


def test_forged_sha_approvals_or_canonical_drift_fails_closed(isolated):
    path = isolated.parent / "assets/review/liu_bei_pilot/phase10_33_state_registry.json"
    canonical = json.loads(path.read_text("utf-8"))
    for field, value in [
        ("source_sha256", "b" * 64),
        ("owner_approval_reference", "fake-owner-approved"),
        ("asset_url", "/assets/unreviewed.png"),
        ("art_status", "released"),
    ]:
        mutated = json.loads(json.dumps(canonical))
        mutated["states"][3][field] = value
        path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ValueError):
            validate_library(isolated)
    path.write_text(json.dumps(canonical), encoding="utf-8")
    reference = isolated / "frontend/companions/production/kiko/portrait_registry.json"
    albedo = json.loads(reference.read_text("utf-8"))
    albedo["release"]["enabled"] = True
    reference.write_text(json.dumps(albedo), encoding="utf-8")
    with pytest.raises(ValueError, match="Canonical reference"):
        validate_library(isolated)


def test_33_state_endpoint_guards_local_client_and_task_ownership(monkeypatch, isolated, tmp_path):
    async def run():
        monkeypatch.setattr(server, "inbox", Inbox(tmp_path / "phase10.sqlite"))
        monkeypatch.setattr(
            server, "phase10_projection",
            lambda root, **kw: phase10_projection(isolated, **kw)
        )
        monkeypatch.setattr(
            server, "validate_liu_bei_33",
            lambda root: validate_library(isolated)
        )
        theirs = server.inbox.create("kiko", "ollama", "OTHER_PRIVATE_PROMPT")
        ours = server.inbox.create("liu_bei", "ollama", "LIU_BEI_PRIVATE_PROMPT")
        server.inbox.update(ours["id"], "state", "running")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            url = "/api/fleet/liu_bei/33-review"
            h = {"X-Exodia-Client": "exodia-dashboard"}
            assert (await client.get(url)).status_code == 403
            assert (await client.get(url, headers=h,
                params={"task_id": theirs["id"], "preview_state": "happy"})).status_code == 409
            assert (await client.get(url, headers=h,
                params={"preview_state": "nonexistent"})).status_code == 422
            response = await client.get(url, headers=h,
                params={"task_id": ours["id"]})
            assert response.status_code == 200, response.text
            assert response.json()["selected_state"] == "working"
            assert response.json()["planned_states"] == 33
            assert response.json()["display"]["asset_url"] is None
            assert "PRIVATE_PROMPT" not in response.text
    asyncio.run(run())
