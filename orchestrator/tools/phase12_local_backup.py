"""Phase 12 operator-confirmed private SQLite recovery snapshots.

This CLI is never invoked by startup or HTTP. A snapshot contains private task
prompts, answers, social drafts and local databases; it is NOT encrypted.
Only an explicit local confirmation writes to an ignored local app_data folder.
Snapshots are consistent PER DATABASE using SQLite's online backup API; the
three files are NOT a cross-database transaction. No restore is automated.

From orchestrator:
  python tools/phase12_local_backup.py --confirm-private-local-backup
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import ROOT

FILES = (
    "companion_tasks.sqlite",
    "editorial.sqlite",
    "exodia_tower.sqlite",
)
SCHEMA = "exodia.phase12.private-sqlite-backup/v1"


def backup_local(root: Path, *, confirmed: bool = False) -> dict:
    """No user-supplied arbitrary destination and no destructive overwrite."""
    if confirmed is not True:
        raise ValueError("Explicit private local snapshot confirmation required")
    root = Path(root).resolve()
    app_data = root / "app_data"
    backup_dir = app_data / "phase12_private_backups"
    if (app_data.is_symlink() or backup_dir.is_symlink()
            or not app_data.is_dir()
            or not app_data.resolve().is_relative_to(root)):
        raise ValueError("Unsafe or absent local app_data")
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    if (backup_dir.is_symlink() or not backup_dir.resolve().is_relative_to(root)
            or not backup_dir.is_dir()):
        raise ValueError("Unsafe local snapshot directory")
    try:
        backup_dir.chmod(0o700)
    except OSError:
        pass  # Windows filesystem permissions must be checked by the operator.

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    completed = []
    missing = []
    for name in FILES:
        source = app_data / name
        if source.is_symlink():
            raise ValueError("Linked source database rejected")
        if not source.exists():
            missing.append(name)
            continue
        if not source.is_file():
            raise ValueError("Invalid source database")
        destination = backup_dir / (
            name.removesuffix(".sqlite") + "-" + timestamp + "-" +
            uuid4().hex + ".sqlite"
        )
        fd = None
        try:
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            fd = None
            with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True,
                                 timeout=10) as original:
                if original.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                    raise ValueError("Source SQLite integrity check failed")
                with sqlite3.connect(destination, timeout=10) as target:
                    original.backup(target, pages=64)
                    if target.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                        raise ValueError("Snapshot SQLite integrity check failed")
            try:
                destination.chmod(0o600)
            except OSError:
                pass  # NTFS ACL inspection is an operator responsibility.
            completed.append(name)
        except Exception:
            if fd is not None:
                os.close(fd)
            destination.unlink(missing_ok=True)
            raise
    return {
        "schema": SCHEMA,
        "operator_explicitly_confirmed": True,
        "snapshot_status": "completed" if completed else "no_databases_found",
        "databases_snapshotted": completed,
        "databases_absent": missing,
        "snapshots_private_unencrypted": True,
        "cross_database_atomic_snapshot": False,
        "production_release_enabled": False,
        "network_upload_performed": False,
        "restore_performed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-private-local-backup", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        report = backup_local(
            args.root, confirmed=args.confirm_private_local_backup
        )
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, sqlite3.Error):
        # Do not emit local paths, user secrets or SQLite exception text.
        print("EXODIA private snapshot unavailable (local_backup_gate_failed)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
