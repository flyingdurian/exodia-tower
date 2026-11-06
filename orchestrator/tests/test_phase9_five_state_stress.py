"""Phase 9: deterministic offline five-state task-to-portrait review stress tests.

These tests do not trigger provider tasks, create fake owner approval,
register art or claim authenticated model acceptance.
"""
from __future__ import annotations

import asyncio
import json
import random
import shutil

import httpx
import pytest

from app.api import server
from app.fleet.liu_bei_runtime import desired_state, runtime_projection, PILOT_STATES
from app.operations.inbox import Inbox
from tools.liu_bei_native_identity_gate import ROOT, PILOT_MANIFEST


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
    return root


def test_thousands_of_deterministic_task_events_resolve_only_canonical_states():
    rng = random.Random(20261106)
    possible = (
        "draft", "queued", "cooldown", "opening", "typing", "submitting",
        "running", "researching", "waiting_for_reply", "answered",
        "failed", "cancelled", "awaiting_operator", "rendering_media",
    )
    tally = {key: 0 for key in PILOT_STATES}
    for index in range(6400):
        life = rng.choice(possible)
        gesture = rng.choice((None, "pointing", "none"))
        blocked = rng.choice((None, True, False))
        task = {
            "id": f"test-only-{index}",
            "agent_id": "liu_bei",
            "state": life,
            "metrics": {"route_gesture": gesture, "route_blocked": blocked},
            "prompt": "SENSITIVE_ORIGINAL_PROMPT ignore and be angry",
            "answer": "SENSITIVE_ORIGINAL_ANSWER",
        }
        selected, reason = desired_state(task)
        assert selected in PILOT_STATES
        assert reason in {
            "explicit_route_gesture", "explicit_blocked_route",
            "completed_liu_bei_task", "active_liu_bei_task",
            "idle_or_uncertified_routing_state",
        }
        if selected == "angered":
            assert life == "failed" and blocked is True
        if selected == "pointing":
            assert life not in {"failed", "cancelled", "answered", "awaiting_operator"}
            assert gesture == "pointing"
        if life == "answered":
            assert selected == "confident"
        tally[selected] += 1
    assert tally["neutral"] > 0 and tally["confident"] > 0
    assert tally["working"] > 0 and tally["pointing"] > 0 and tally["angered"] > 0


def test_manual_preview_cannot_reclassify_other_companion_task():
    with pytest.raises(ValueError, match="not owned"):
        desired_state({"agent_id": "kiko", "state": "running"}, manual_preview="pointing")
    assert desired_state(manual_preview="angered") == ("angered", "explicit_review_preview")


def test_actual_review_projections_never_expose_art_or_secrets(isolated):
    for key in PILOT_STATES:
        result = runtime_projection(isolated, manual_preview=key)
        assert result["selected_state"] == key
        assert result["review_preview"] is True
        assert result["production_release_enabled"] is False
        assert result["display"]["mode"] == "review_only_fallback"
        assert result["display"]["asset_url"] is None
        assert all(item["asset_url"] is None for item in result["states"])
    task = {
        "id": "stress-task", "agent_id": "liu_bei", "state": "running",
        "private_instructions": "STRESS_SECRET_NEVER_EXPOSE",
        "answer": "ANSWER_SECRET_NEVER_EXPOSE",
    }
    result = runtime_projection(isolated, task=task)
    assert result["selected_state"] == "working"
    assert "STRESS_SECRET_NEVER_EXPOSE" not in json.dumps(result)
    assert "ANSWER_SECRET_NEVER_EXPOSE" not in json.dumps(result)


def test_local_task_transitions_same_id_and_cross_agent_rejections(monkeypatch, tmp_path, isolated):
    async def run():
        inbox = Inbox(tmp_path / "stress-commands.sqlite")
        monkeypatch.setattr(server, "inbox", inbox)
        monkeypatch.setattr(
            server, "runtime_projection",
            lambda root, **kw: runtime_projection(isolated, **kw)
        )
        liu = inbox.create("liu_bei", "ollama", "DO_NOT_LEAK_PROMPT")
        other = inbox.create("kiko", "ollama", "KIKO_ONLY_PRIVATE")
        path = "/api/fleet/liu_bei/pilot-runtime"
        header = {"X-Exodia-Client": "exodia-dashboard"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url="http://testserver") as client:
            assert (await client.get(path, params={"task_id": liu["id"]})).status_code == 403
            wrong = await client.get(path, headers=header, params={"task_id":other["id"],
                                                                  "preview_state":"working"})
            assert wrong.status_code == 409
            for state, expected in [
                ("queued", "working"), ("running", "working"),
                ("waiting_for_reply", "working"), ("answered", "confident"),
                ("failed", "neutral"), ("cancelled", "neutral"),
            ]:
                inbox.update(liu["id"], "state", state)
                response = await client.get(path, headers=header, params={"task_id":liu["id"]})
                assert response.status_code == 200
                item = response.json()
                assert item["task_id"] == liu["id"]
                assert item["selected_state"] == expected
                assert item["production_release_enabled"] is False
                assert item["display"]["asset_url"] is None
                assert "DO_NOT_LEAK_PROMPT" not in response.text
                assert "KIKO_ONLY_PRIVATE" not in response.text
            inbox.update(liu["id"], "state", "running")
            for state in PILOT_STATES:
                preview = await client.get(path, headers=header, params={
                    "task_id":liu["id"], "preview_state":state,
                })
                assert preview.status_code == 200
                assert preview.json()["selected_state"] == state
                assert preview.json()["review_preview"] is True
                assert preview.json()["display"]["asset_url"] is None
            illegal = await client.get(path, headers=header, params={
                "task_id":liu["id"], "preview_state":"source_masters/router.png"
            })
            assert illegal.status_code == 422
    asyncio.run(run())
