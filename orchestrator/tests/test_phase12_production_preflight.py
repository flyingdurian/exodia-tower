"""Phase 12 operational health, release locks and private local backups.

No live provider dispatch, real artwork promotion, social posting or network I/O.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
from pathlib import Path

import httpx
import pytest

from app.api import server
from app.operations.inbox import Inbox
from app.operations.production_readiness import (
    SCHEMA, inspect_production_readiness
)
from app.social.workflow import EditorialStore
from tools import phase12_local_backup as backup
from tools.liu_bei_native_identity_gate import ROOT


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "app/companions").mkdir(parents=True)
    (root / "frontend/companions/production/kiko").mkdir(parents=True)
    pilot = tmp_path / "assets/review/liu_bei_pilot"
    pilot.mkdir(parents=True)
    for name in ("app/companions/roster.json",
                 "frontend/companions/roster.json",
                 "frontend/companions/production/kiko/portrait_registry.json"):
        shutil.copyfile(ROOT / name, root / name)
    for name in ("pilot_manifest.json", "variant_registry.json"):
        shutil.copyfile(ROOT.parent / "assets/review/liu_bei_pilot" / name,
                        pilot / name)
    inbox = Inbox(root / "app_data/companion_tasks.sqlite")
    social = EditorialStore(root / "app_data/editorial.sqlite")
    with sqlite3.connect(root / "app_data/exodia_tower.sqlite") as c:
        c.execute("CREATE TABLE private_state (name TEXT)")
        c.execute("INSERT INTO private_state VALUES ('PRIVATE_DO_NOT_PUBLISH')")
    return root, inbox, social


def test_health_is_factual_and_never_confuses_it_with_production_approval(isolated):
    root, inbox, _ = isolated
    health = inbox.history_health()
    report = inspect_production_readiness(root, host="127.0.0.1",
                                          history_health=health)
    assert report["schema"] == SCHEMA
    assert report["local_operational_health"] == "healthy"
    assert report["checks"]["ten_companion_roster_consistent"] is True
    assert report["checks"]["sqlite_task_integrity_and_wal"] is True
    assert report["checks"]["sqlite_editorial_integrity"] == "integrity_ok"
    assert report["checks"]["authenticated_provider_acceptance"] == "not_established"
    assert report["checks"]["native_portrait_owner_release"] == "not_authorized"
    assert report["production_release_ready"] is False
    assert report["provider_dispatch_performed"] is False
    assert report["external_publishing_enabled"] is False
    assert "PRIVATE_DO_NOT_PUBLISH" not in json.dumps(report)


def test_non_loopback_host_or_unhealthy_tasks_blocks_operational_health(isolated):
    root, inbox, _ = isolated
    health = inbox.history_health()
    report = inspect_production_readiness(root, host="0.0.0.0",
                                          history_health=health)
    assert report["local_operational_health"] == "action_required"
    assert report["checks"]["loopback_bind_configured"] is False
    health["journal_mode"] = "delete"
    report = inspect_production_readiness(root, host="127.0.0.1",
                                          history_health=health)
    assert report["checks"]["sqlite_task_integrity_and_wal"] is False
    assert report["local_operational_health"] == "action_required"


def test_mutated_release_ledger_and_companion_identity_fails_closed(isolated):
    root, inbox, _ = isolated
    targets = [
        (root / "frontend/companions/production/kiko/portrait_registry.json",
         "release", "enabled", True),
        (root.parent / "assets/review/liu_bei_pilot/pilot_manifest.json",
         None, "production_release_enabled", True),
        (root.parent / "assets/review/liu_bei_pilot/variant_registry.json",
         None, "automatic_registration_enabled", True),
    ]
    for filename, parent, field, value in targets:
        old = filename.read_text("utf-8")
        doc = json.loads(old)
        (doc[parent] if parent else doc)[field] = value
        filename.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ValueError):
            inspect_production_readiness(root, host="localhost",
                                         history_health=inbox.history_health())
        filename.write_text(old, encoding="utf-8")
    roster = root / "frontend/companions/roster.json"
    rows = json.loads(roster.read_text("utf-8"))
    rows[2]["id"] = "fabricated"
    roster.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="roster"):
        inspect_production_readiness(root, host="localhost",
                                     history_health=inbox.history_health())


def test_missing_editorial_db_cannot_be_reported_as_healthy(isolated):
    root, inbox, _ = isolated
    (root / "app_data/editorial.sqlite").unlink()
    report = inspect_production_readiness(
        root, host="127.0.0.1", history_health=inbox.history_health())
    assert report["checks"]["sqlite_editorial_integrity"] == "not_initialized"
    assert report["local_operational_health"] == "action_required"


def test_private_backup_requires_opt_in_and_has_no_overwrite_or_network(isolated):
    root, inbox, _ = isolated
    inbox.create("kiko", "ollama", "SECRET_PROMPT_BACKUP_ONLY")
    with pytest.raises(ValueError, match="confirmation"):
        backup.backup_local(root)
    report = backup.backup_local(root, confirmed=True)
    assert report["schema"] == backup.SCHEMA
    assert report["network_upload_performed"] is False
    assert report["snapshots_private_unencrypted"] is True
    assert report["cross_database_atomic_snapshot"] is False
    assert report["restore_performed"] is False
    assert report["production_release_enabled"] is False
    assert set(report["databases_snapshotted"]) == set(backup.FILES)
    assert "SECRET_PROMPT_BACKUP_ONLY" not in json.dumps(report)
    files = sorted((root / "app_data/phase12_private_backups").glob("*.sqlite"))
    assert len(files) == 3
    if os.name != "nt":
        assert all((f.stat().st_mode & 0o077) == 0 for f in files)
    tasks = next(f for f in files if f.name.startswith("companion_tasks-"))
    with sqlite3.connect(tasks) as c:
        assert c.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
        assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert c.execute("SELECT prompt FROM tasks").fetchone()[0] == "SECRET_PROMPT_BACKUP_ONLY"
    again = backup.backup_local(root, confirmed=True)
    assert len(list((root / "app_data/phase12_private_backups").glob("*.sqlite"))) == 6
    assert set(again["databases_snapshotted"]) == set(backup.FILES)


def test_private_backup_rejects_linked_databases_and_backup_directories(isolated, tmp_path):
    root, _, _ = isolated
    source = root / "app_data/editorial.sqlite"
    source.unlink()
    outside = tmp_path / "outside.sqlite"
    with sqlite3.connect(outside) as c:
        c.execute("CREATE TABLE forbidden (secret TEXT)")
    try:
        source.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links unavailable in this filesystem")
    with pytest.raises(ValueError, match="Linked source"):
        backup.backup_local(root, confirmed=True)
    source.unlink()
    target = root / "app_data/phase12_private_backups"
    target.mkdir(exist_ok=True)
    target.rmdir()
    outside_folder = tmp_path / "unsafe_backup_destination"
    outside_folder.mkdir()
    target.symlink_to(outside_folder, target_is_directory=True)
    with pytest.raises(ValueError, match="Unsafe"):
        backup.backup_local(root, confirmed=True)


def test_backup_cli_reports_errors_without_private_paths(monkeypatch, capsys, isolated):
    root, _, _ = isolated
    assert backup.main(["--root", str(root)]) == 2
    assert "phase12_private_backups" not in capsys.readouterr().err
    (root / "app_data/editorial.sqlite").write_bytes(b"PRIVATE_PATH_AND_SQLITE_ERROR")
    assert backup.main(["--root", str(root),
                        "--confirm-private-local-backup"]) == 2
    out = capsys.readouterr()
    assert "PRIVATE_PATH_AND_SQLITE_ERROR" not in out.err
    assert "private snapshot unavailable" in out.err.lower()


def test_http_readiness_is_guarded_redacted_and_get_only(monkeypatch, isolated):
    async def run():
        root, inbox, _ = isolated
        monkeypatch.setattr(server, "inbox", inbox)
        from dataclasses import replace
        monkeypatch.setattr(server, "settings", replace(server.settings, root=root))
        calls = []
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver"
        ) as client:
            url = "/api/operations/production-preflight"
            assert (await client.get(url)).status_code == 403
            response = await client.get(
                url, headers={"X-Exodia-Client": "exodia-dashboard"})
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["production_release_ready"] is False
            assert data["local_operational_health"] == "healthy"
            assert "PRIVATE_DO_NOT_PUBLISH" not in response.text
            assert (await client.post(
                url, headers={"X-Exodia-Client":"exodia-dashboard"}
            )).status_code == 405
    asyncio.run(run())
