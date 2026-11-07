"""Liu Bei identity migration: preserve SQLite history, art locks and API."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.operations.inbox import Inbox
from app.api import server
from tools.liu_bei_native_identity_gate import PILOT_MANIFEST, verify_reference, ROOT


def test_legacy_task_ids_migrate_once_without_changing_history(tmp_path):
    file = tmp_path / "command.sqlite"
    with sqlite3.connect(file) as c:
        c.execute("""CREATE TABLE tasks(
            id TEXT PRIMARY KEY, agent_id TEXT, provider TEXT, prompt TEXT,
            state TEXT, answer TEXT DEFAULT '', artifact TEXT,
            created_at TEXT, updated_at TEXT)""")
        c.execute("""INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)""",
            ("legacy-original-task", "router", "gemini", "Historic prompt",
             "answered", "Historic response", None,
             "2025-02-14T00:01:00+00:00", "2025-02-14T00:03:00+00:00"))
        c.execute("""INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)""",
            ("another-agent", "kiko", "ollama", "Original Albedo task",
             "answered", "Albedo answer", None,
             "2025-02-14T00:02:00+00:00", "2025-02-14T00:04:00+00:00"))
    inbox=Inbox(file)
    migrated=inbox.get("legacy-original-task")
    assert migrated["id"]=="legacy-original-task"
    assert migrated["agent_id"]=="liu_bei"
    assert migrated["prompt"]=="Historic prompt"
    assert migrated["answer"]=="Historic response"
    assert migrated["state"]=="answered"
    assert migrated["created_at"]=="2025-02-14T00:01:00+00:00"
    assert inbox.get("another-agent")["agent_id"]=="kiko"
    events=inbox.events("legacy-original-task")
    assert [e["event"] for e in events]==["legacy_snapshot","companion_id_migrated"]
    assert events[-1]["reason_code"]=="identity_renamed"
    assert events[-1]["to_state"]=="answered"
    assert len(Inbox(file).events("legacy-original-task"))==len(events)
    with sqlite3.connect(file) as c:
        assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]==2
        assert c.execute("SELECT COUNT(*) FROM tasks WHERE agent_id='router'").fetchone()[0]==0


def test_idempotent_migration_keeps_retry_lineage_and_no_remote_dispatch(tmp_path):
    file=tmp_path/"durable.sqlite"
    inbox=Inbox(file)
    with sqlite3.connect(file) as c:
        # Simulates an existing valid modern database written before the rename.
        c.execute("INSERT INTO tasks(id,agent_id,provider,prompt,state,created_at,updated_at) "
                  "VALUES(?,?,?,?,?,?,?)", ("failed-parent","router","chatgpt",
                                           "Old route request","failed",
                                           "2025-04-01T00:00:00+00:00",
                                           "2025-04-01T00:00:00+00:00"))
        c.execute("INSERT INTO tasks(id,agent_id,provider,prompt,state,created_at,updated_at,retry_of,retry_index) "
                  "VALUES(?,?,?,?,?,?,?,?,?)",("retry-child","router","chatgpt",
                                              "Old route request","answered",
                                              "2025-04-01T00:01:00+00:00",
                                              "2025-04-01T00:02:00+00:00",
                                              "failed-parent",1))
    reopened=Inbox(file)
    assert reopened.get("failed-parent")["agent_id"]=="liu_bei"
    assert reopened.get("retry-child")["agent_id"]=="liu_bei"
    assert reopened.get("retry-child")["retry_of"]=="failed-parent"
    assert reopened.get("retry-child")["retry_index"]==1
    assert reopened.get("retry-child")["state"]=="answered"
    assert len([e for e in reopened.events("retry-child") if e["event"]=="companion_id_migrated"])==1
    assert len([e for e in Inbox(file).events("retry-child") if e["event"]=="companion_id_migrated"])==1
    with pytest.raises(ValueError,match="Retired companion ID"):
        reopened.create("router","ollama","Should not create old owner")
    assert reopened.create("liu_bei","ollama","Native ID")["agent_id"]=="liu_bei"


def test_public_rosters_and_routes_use_new_identity(monkeypatch,tmp_path):
    monkeypatch.setattr(server,"inbox",Inbox(tmp_path/"tasks.sqlite"))
    with TestClient(server.app) as client:
        response=client.get("/api/companions")
        assert response.status_code==200
        ids=[x["id"] for x in response.json()["agents"]]
        assert "liu_bei" in ids and "router" not in ids
        liu=next(x for x in response.json()["agents"] if x["id"]=="liu_bei")
        assert liu["name"]=="Liu Bei"
        assert liu["portrait"] is None and liu["thumbnail"] is None
        assert client.post("/api/companions/router/react",json={"state":"idle"}).status_code==422
        assert client.post("/api/companions/liu_bei/react",json={"state":"idle"}).status_code==200
        h={"x-exodia-client":"exodia-dashboard"}
        assert client.get("/api/fleet/liu_bei-a0/watch-status",headers=h).status_code==200
        assert client.get("/api/fleet/liu_bei-a0/preflight",headers=h).status_code==200
        assert client.get("/api/fleet/liu_bei/pilot-runtime",headers=h).status_code==200
        assert client.get("/api/fleet/riven-a0/watch-status",headers=h).status_code==404
        assert client.get("/api/fleet/riven-a0/preflight",headers=h).status_code==404
        assert client.get("/api/fleet/riven/pilot-runtime",headers=h).status_code==404


def test_unchanged_poster_sha_preserves_reference_only_policy():
    data=json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    assert data["character_id"]=="liu_bei" and data["name"]=="Liu Bei"
    assert data["identity_reference"]["sha256"]==(
        "65562dfd75c83ac46cf6ec2dec05bff9d59812bd22287750bd48833f94bc584e")
    assert data["identity_reference"]["path"]=="frontend/companions/source_masters/router.png"
    assert verify_reference(data,ROOT)["status"]=="verified_composite_reference_only"
    assert data["native_production_certified"] is False
    assert data["production_release_enabled"] is False
    assert all(x["source_file"] is None for x in data["states"].values())
