"""Riven Phase 7 review-only runtime tests: source locks and task-owned states."""
from __future__ import annotations

import json
import shutil

import httpx
import pytest

from app.api import server
from app.fleet.riven_runtime import (
    STATES, PILOT_STATES, desired_state, runtime_projection, SCHEMA
)
from app.operations.inbox import Inbox
from tools.riven_native_identity_gate import ROOT, PILOT_MANIFEST


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "frontend/companions/source_masters").mkdir(parents=True)
    (root / "app/companions").mkdir(parents=True)
    pilot = tmp_path / "assets/review/riven_pilot"
    pilot.mkdir(parents=True)
    shutil.copyfile(ROOT / "frontend/companions/source_masters/router.png",
                    root / "frontend/companions/source_masters/router.png")
    shutil.copyfile(ROOT / "app/companions/roster.json",
                    root / "app/companions/roster.json")
    shutil.copyfile(PILOT_MANIFEST, pilot / "pilot_manifest.json")
    return root


def test_five_states_and_task_routing_never_infer_anger_from_generic_failure():
    assert tuple(STATES) == PILOT_STATES == (
        "neutral", "confident", "angered", "working", "pointing")
    task = {"id":"riven-one", "agent_id":"router", "state":"failed", "metrics":{}}
    assert desired_state(task)[0] == "neutral"
    assert desired_state({**task, "metrics":{"route_blocked":True}})[0] == "angered"
    assert desired_state({**task, "state":"answered"})[0] == "confident"
    assert desired_state({**task, "state":"running"})[0] == "working"
    assert desired_state({**task, "state":"running",
                          "metrics":{"route_gesture":"pointing"}})[0] == "pointing"
    assert desired_state(manual_preview="pointing")[0] == "pointing"
    with pytest.raises(ValueError):
        desired_state(manual_preview="unknown")
    with pytest.raises(ValueError):
        desired_state({"agent_id":"kiko", "state":"running"})


def test_no_native_image_must_return_only_a_truthful_typographic_fallback(isolated):
    preview = runtime_projection(isolated)
    assert preview["schema"] == SCHEMA
    assert preview["character_id"] == "router"
    assert preview["selected_state"] == "neutral"
    assert preview["display"]["mode"] == "review_only_fallback"
    assert preview["display"]["asset_url"] is None
    assert preview["production_release_enabled"] is False
    assert preview["owner_identity_approval"] == "pending"
    assert preview["native_a0_intake"]["technical_source_pass"] is False
    assert len(preview["states"]) == 5
    assert [s["key"] for s in preview["states"]] == list(PILOT_STATES)
    assert all(s["asset_url"] is None for s in preview["states"])
    assert not any("img" in json.dumps(s).lower() for s in preview["states"])
    assert preview["display"]["status"].startswith("Five native Riven states")


def test_source_hash_drift_and_forged_approval_fail_closed(isolated):
    pilot = isolated.parent / "assets/review/riven_pilot/pilot_manifest.json"
    manifest = json.loads(pilot.read_text(encoding="utf-8"))
    manifest["states"]["working"]["owner_approval_reference"] = "owner-fake-approval"
    pilot.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        runtime_projection(isolated, manual_preview="working")
    manifest["states"]["working"]["owner_approval_reference"] = None
    manifest["production_release_enabled"] = True
    pilot.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        runtime_projection(isolated)


def test_task_bound_projection_does_not_expose_private_prompt_or_response(isolated):
    original = {"id":"riven-123", "agent_id":"router", "provider":"gemini",
                "state":"answered", "metrics":{"total_s":1.23},
                "prompt":"TOP_PRIVATE_PROMPT_EXAMPLE",
                "answer":"TOP_PRIVATE_ANSWER_EXAMPLE",
                "private_instructions":"TOP_PRIVATE_INSTRUCTIONS"}
    result = runtime_projection(isolated, task=original)
    assert result["selected_state"] == "confident"
    assert result["task_id"] == "riven-123"
    for secret in ("TOP_PRIVATE_PROMPT_EXAMPLE", "TOP_PRIVATE_ANSWER_EXAMPLE",
                   "TOP_PRIVATE_INSTRUCTIONS", str(isolated)):
        assert secret not in json.dumps(result)
    manual = runtime_projection(isolated, task=original, manual_preview="pointing")
    assert manual["selected_state"] == "pointing"
    assert manual["review_preview"] is True
    assert manual["display"]["asset_url"] is None


def test_api_is_local_guarded_and_rejects_cross_agent_task(monkeypatch, tmp_path, isolated):
    import asyncio
    async def run():
        monkeypatch.setattr(server, "inbox", Inbox(tmp_path/"commands.sqlite"))
        monkeypatch.setattr(server, "runtime_projection",
                            lambda root, **kw: runtime_projection(isolated, **kw))
        theirs = server.inbox.create("kiko","ollama","Albedo-only task")
        riven = server.inbox.create("router","ollama","Riven route task")
        server.inbox.update(riven["id"],"state","running")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url="http://testserver") as client:
            url = "/api/fleet/riven/pilot-runtime"
            assert (await client.get(url)).status_code == 403
            h = {"x-exodia-client":"exodia-dashboard"}
            assert (await client.get(url, headers=h, params={
                "task_id":theirs["id"]})).status_code == 409
            assert (await client.get(url, headers=h, params={
                "preview_state":"invalid"})).status_code == 422
            response = await client.get(url, headers=h, params={
                "task_id":riven["id"]})
            assert response.status_code == 200, response.text
            assert response.json()["selected_state"] == "working"
            assert response.json()["display"]["asset_url"] is None
            preview = await client.get(url, headers=h, params={
                "task_id":riven["id"],"preview_state":"angered"})
            assert preview.status_code == 200
            assert preview.json()["selected_state"] == "angered"
            assert preview.json()["review_preview"] is True
            assert "Riven route task" not in preview.text
            assert "Albedo-only task" not in preview.text
    asyncio.run(run())


def test_new_review_ui_must_not_use_poster_or_claim_native_source():
    from pathlib import Path
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    html = (frontend/"albedo_command.html").read_text(encoding="utf-8")
    js = (frontend/"riven_pilot_boot.mjs").read_text(encoding="utf-8")
    assert 'id="rivenPilotPane"' in html
    assert 'data-riven-preview="pointing"' in html
    assert "NATIVE RIVEN ART PENDING" in html
    assert 'asset_url' not in html.split('id="rivenPilotPane"')[1].split('</section>')[0]
    assert "production_release_enabled" in js
    assert "asset_url!==null" in js
    assert "exodia:command-task" in js
    assert "data-riven-preview" in js
    assert "source_masters/router.png" not in js
