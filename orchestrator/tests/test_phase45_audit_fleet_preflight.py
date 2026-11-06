"""Phase 4 audit telemetry + Phase 5 Liu Bei preflight, without external actions."""
from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.api import server
from app.fleet.liu_bei_preflight import LIU_BEI_ID, PILOT_STATES, FROZEN_IDS, liu_bei_a0_preflight
from app.operations.inbox import Inbox
from tools.liu_bei_native_identity_gate import ROOT as ORCHESTRATOR_ROOT, PILOT_MANIFEST


@pytest.fixture
def liu_bei_sandbox(tmp_path):
    root=tmp_path/"orchestrator"
    (root/"frontend/companions/source_masters").mkdir(parents=True)
    (root/"app/companions").mkdir(parents=True)
    target=tmp_path/"assets/review/liu_bei_pilot"
    target.mkdir(parents=True)
    shutil.copyfile(ORCHESTRATOR_ROOT/"frontend/companions/source_masters/router.png",
                    root/"frontend/companions/source_masters/router.png")
    shutil.copyfile(ORCHESTRATOR_ROOT/"app/companions/roster.json",
                    root/"app/companions/roster.json")
    shutil.copyfile(PILOT_MANIFEST,target/"pilot_manifest.json")
    return root


def test_phase5_no_candidate_is_read_only_pending_and_all_other_companions_frozen(liu_bei_sandbox):
    root=liu_bei_sandbox
    manifest=root.parent/"assets/review/liu_bei_pilot/pilot_manifest.json"
    raw=manifest.read_bytes()
    preview=liu_bei_a0_preflight(root)
    assert preview["schema"]=="exodia.phase5.liu_bei-a0-preflight/v1"
    assert preview["character_id"]==LIU_BEI_ID=="liu_bei"
    assert preview["intake_status"]=="awaiting_manual_png"
    assert preview["canonical_canvas"]==[1536,1920]
    assert preview["original_sha256"] is None
    assert preview["independent_original_authorship_verified"] is False
    assert preview["owner_identity_approval"]=="pending"
    assert preview["five_state_pilot"].startswith("locked_")
    assert preview["production_release_enabled"] is False
    assert preview["native_production_certified"] is False
    assert set(preview["frozen_other_companion_ids"])==set(FROZEN_IDS)
    assert [x["state"] for x in preview["pilot_states"]]==list(PILOT_STATES)
    assert all(x["production_status"]=="locked" for x in preview["pilot_states"])
    assert "inbox" not in json.dumps(preview).lower()
    assert str(root) not in json.dumps(preview)
    assert manifest.read_bytes()==raw
    assert not (root/"app_data/liu_bei_a0_inbox").exists()


def test_phase5_rejects_non_native_art_and_does_not_approve_by_sha(liu_bei_sandbox):
    inbox=liu_bei_sandbox/"app_data/liu_bei_a0_inbox"
    inbox.mkdir(parents=True)
    Image.new("RGB",(1122,1402),"#223344").save(inbox/"liu_bei_A0_native.png")
    status=liu_bei_a0_preflight(liu_bei_sandbox)
    assert status["intake_status"]=="source_rejected"
    assert status["original_sha256"] is None
    assert status["technical_source_pass"] is False
    assert status["owner_identity_approval"]=="pending"
    assert status["production_release_enabled"] is False


@pytest.mark.parametrize("tamper",["release","state","roster"])
def test_phase5_fails_closed_on_art_or_roster_mutation(liu_bei_sandbox,tamper):
    root=liu_bei_sandbox
    manifest_path=root.parent/"assets/review/liu_bei_pilot/pilot_manifest.json"
    roster_path=root/"app/companions/roster.json"
    if tamper=="roster":
        roster=json.loads(roster_path.read_text("utf-8"))
        roster=[a for a in roster if a["id"]!="memory"]
        roster_path.write_text(json.dumps(roster),encoding="utf-8")
    else:
        manifest=json.loads(manifest_path.read_text("utf-8"))
        if tamper=="release":
            manifest["production_release_enabled"]=True
        else:
            manifest["states"]["neutral"]["source_file"]="fake_unapproved.png"
        manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(ValueError):
        liu_bei_a0_preflight(root)


def test_sqlite_error_codes_are_durable_but_never_store_raw_error_text(tmp_path):
    path=tmp_path/"command.sqlite"
    inbox=Inbox(path)
    task=inbox.create("kiko","ollama","UNSAFE_PROMPT_IN_SOURCE",
                      private_instructions="DO_NOT_LOG_SECRET_INSTRUCTION")
    inbox.update(task["id"],"state","running")
    inbox.update(task["id"],"error","RAW_PROVIDER_SECRET_PATH_AND_TOKEN")
    inbox.update(task["id"],"state","failed")
    timeline=inbox.events(task["id"])
    assert "error_recorded" in [e["event"] for e in timeline]
    assert next(e for e in timeline if e["event"]=="error_recorded")["reason_code"]=="task_error"
    assert "DO_NOT_LOG_SECRET_INSTRUCTION" not in json.dumps(timeline)
    assert "RAW_PROVIDER_SECRET_PATH_AND_TOKEN" not in json.dumps(timeline)
    assert "UNSAFE_PROMPT_IN_SOURCE" not in json.dumps(timeline)
    health=Inbox(path).history_health()
    assert health["schema"]=="exodia.command-history-health/v1"
    assert health["status"]=="ok"
    assert health["journal_mode"]=="wal"
    assert health["total_tasks"]==1 and health["failed_tasks"]==1
    assert health["error_events"]==1
    assert health["total_events"]>=3
    assert "DO_NOT_LOG_SECRET_INSTRUCTION" not in json.dumps(health)
    assert str(path) not in json.dumps(health)


def test_legacy_task_event_table_migrates_reason_code_without_rewriting_events(tmp_path):
    path=tmp_path/"legacy.sqlite"
    with sqlite3.connect(path) as c:
        c.execute("""CREATE TABLE task_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
            event TEXT NOT NULL, from_state TEXT, to_state TEXT,
            occurred_at TEXT NOT NULL)""")
        c.execute("""INSERT INTO task_events(task_id,event,from_state,to_state,occurred_at)
                     VALUES('legacy-task','legacy_snapshot',NULL,'failed','2025-01-01T00:00:00+00:00')""")
    inbox=Inbox(path)
    with sqlite3.connect(path) as c:
        names=[r[1] for r in c.execute("PRAGMA table_info(task_events)")]
        assert "reason_code" in names
        assert c.execute("SELECT COUNT(*) FROM task_events").fetchone()[0]==1
        assert c.execute("SELECT reason_code FROM task_events").fetchone()[0] is None
    task=inbox.create("kiko","ollama","new task")
    assert inbox.events(task["id"])[0]["reason_code"] is None


def test_history_health_and_phase5_endpoints_are_local_and_redacted(monkeypatch,tmp_path,liu_bei_sandbox):
    async def run():
        isolated=Inbox(tmp_path/"local.sqlite")
        isolated.create("kiko","ollama","ORIGINAL_PROMPT_PRIVATE",
                        private_instructions="NEVER_EXPOSE_PRIVATE_INSTRUCTION")
        monkeypatch.setattr(server,"inbox",isolated)
        monkeypatch.setattr(server,"liu_bei_a0_preflight",lambda unused:liu_bei_a0_preflight(liu_bei_sandbox))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url="http://testserver") as client:
            for url in ("/api/command/history-health","/api/fleet/liu_bei-a0/preflight"):
                blocked=await client.get(url)
                assert blocked.status_code==403
                resp=await client.get(url,headers={"x-exodia-client":"exodia-dashboard"})
                assert resp.status_code==200,resp.text
                assert "ORIGINAL_PROMPT_PRIVATE" not in resp.text
                assert "NEVER_EXPOSE_PRIVATE_INSTRUCTION" not in resp.text
                assert str(liu_bei_sandbox) not in resp.text
            assert (await client.get("/api/command/history-health",
                      headers={"x-exodia-client":"exodia-dashboard"})).json()["total_tasks"]==1
    asyncio.run(run())


def test_sqlite_boundary_returns_safe_503_and_does_not_reveal_exception(monkeypatch):
    async def run():
        def broken():
            raise sqlite3.OperationalError("RAW_SQL_PRIVATE_SECRET_123 local path /home/operator")
        monkeypatch.setattr(server.inbox,"history_health",broken)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url="http://testserver") as client:
            resp=await client.get("/api/command/history-health",
                                  headers={"x-exodia-client":"exodia-dashboard"})
        assert resp.status_code==503
        assert resp.json()["code"]=="sqlite_storage_unavailable"
        assert "RAW_SQL_PRIVATE_SECRET_123" not in resp.text
        assert "/home/operator" not in resp.text
        assert not any("RAW_SQL_PRIVATE_SECRET_123" in json.dumps(e)
                       for e in server.events.latest())
    asyncio.run(run())


def test_phase5_route_fails_safely_when_locked_manifest_is_invalid(monkeypatch):
    async def run():
        def corrupt(_):
            raise ValueError("SECRET_ART_PATH_DO_NOT_EXPOSE")
        monkeypatch.setattr(server,"liu_bei_a0_preflight",corrupt)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),
                                     base_url="http://testserver") as client:
            resp=await client.get("/api/fleet/liu_bei-a0/preflight",
                                  headers={"x-exodia-client":"exodia-dashboard"})
        assert resp.status_code==503
        assert "SECRET_ART_PATH_DO_NOT_EXPOSE" not in resp.text
        assert "SECRET_ART_PATH_DO_NOT_EXPOSE" not in json.dumps(server.events.latest())
    asyncio.run(run())
