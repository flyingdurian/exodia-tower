"""Phase 12 production preflight: non-mutating local health and release gates.

This is NOT a production-release command. Art identity approvals and actual
authenticated provider sessions cannot be established from CI or local files.
No browser, network, publishing, image import, database mutation or secret read.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = "exodia.phase12.production-preflight/v1"
ROSTER = ("kiko", "liu_bei", "memory", "archives", "inventory",
          "vault", "ninja", "cache", "strategy", "nova")
STATE_CATEGORIES = {"expression": 20, "action": 13}

def _json_policy(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Unsafe or missing local release policy")
    obj = json.loads(path.read_text("utf-8"))
    if not isinstance(obj, (dict, list)):
        raise ValueError("Invalid release policy structure")
    return obj


def _editorial_integrity(root: Path):
    """SQLite opens read-only; no migration or checkpoint is performed."""
    path = root / "app_data/editorial.sqlite"
    if path.is_symlink():
        raise ValueError("Linked editorial DB rejected")
    if not path.is_file():
        return "not_initialized"
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=3)
    try:
        check = conn.execute("PRAGMA quick_check(1)").fetchone()
        if not check or check[0] != "ok":
            raise ValueError("Editorial SQLite integrity gate failed")
        # Only the bounded outcome is released. No filenames, rows or SQL.
        return "integrity_ok"
    finally:
        conn.close()


def inspect_production_readiness(root: Path, *, host: str,
                                 history_health: dict) -> dict:
    root = Path(root).resolve()
    if not isinstance(history_health, dict) or (
        history_health.get("schema") != "exodia.command-history-health/v1"
    ):
        raise ValueError("Local command history health contract changed")
    if not isinstance(host, str):
        raise ValueError("Invalid local bind host")
    local_host = host.strip().lower() in {"localhost", "127.0.0.1", "::1"}
    backend = _json_policy(root / "app/companions/roster.json")
    frontend = _json_policy(root / "frontend/companions/roster.json")
    if (not isinstance(backend, list) or not isinstance(frontend, list)
            or tuple(row.get("id") for row in backend if isinstance(row, dict)) != ROSTER
            or tuple(row.get("id") for row in frontend if isinstance(row, dict)) != ROSTER
            or len(backend) != 10 or len(frontend) != 10
            or any(not isinstance(row, dict) for row in backend + frontend)
            or any((left["name"], left["id"]) != (right["name"], right["id"])
                   for left, right in zip(backend, frontend))):
        raise ValueError("Ten-companion roster identity drift")
    albedo = _json_policy(
        root / "frontend/companions/production/kiko/portrait_registry.json"
    )
    states = albedo.get("states")
    if (albedo.get("schema") != "exodia.portrait-state-registry/v1"
            or albedo.get("character_id") != "kiko"
            or albedo.get("release", {}).get("enabled") is not False
            or not isinstance(states, dict)
            or len(states) != 33
            or any(not isinstance(s, dict) for s in states.values())
            or any(sum(x["category"] == kind for x in states.values()) != count
                   for kind, count in STATE_CATEGORIES.items())):
        raise ValueError("Albedo portrait release or 33-state policy drift")

    pilot = _json_policy(root.parent / "assets/review/liu_bei_pilot/pilot_manifest.json")
    if (pilot.get("character_id") != "liu_bei"
            or pilot.get("production_release_enabled") is not False
            or pilot.get("native_production_certified") is not False
            or set(pilot.get("states", {})) !=
            {"neutral", "confident", "angered", "working", "pointing"}):
        raise ValueError("Liu Bei native release policy drift")
    variants = _json_policy(root.parent / "assets/review/liu_bei_pilot/variant_registry.json")
    if (variants.get("character_id") != "liu_bei"
            or variants.get("production_release_enabled") is not False
            or variants.get("automatic_registration_enabled") is not False):
        raise ValueError("Liu Bei variant policy drift")

    tasks_wal = history_health.get("journal_mode") == "wal"
    tasks_healthy = history_health.get("status") == "ok" and tasks_wal
    editorial = _editorial_integrity(root)
    data_ready = tasks_healthy and editorial == "integrity_ok"
    # Neither CI nor this inspection can establish authenticated providers or
    # exact native-source human review. Their status stays explicitly pending.
    checks = {
        "loopback_bind_configured": local_host,
        "ten_companion_roster_consistent": True,
        "albedo_33_state_art_release_locked": True,
        "liu_bei_pilot_and_variant_release_locked": True,
        "sqlite_task_integrity_and_wal": tasks_healthy,
        "sqlite_editorial_integrity": editorial,
        "authenticated_provider_acceptance": "not_established",
        "native_portrait_owner_release": "not_authorized",
    }
    return {
        "schema": SCHEMA,
        "read_only": True,
        "status": "development_gates_only",
        "local_operational_health": (
            "healthy" if data_ready and local_host else "action_required"
        ),
        "checks": checks,
        "production_release_enabled": False,
        "external_publishing_enabled": False,
        "art_registration_performed": False,
        "provider_dispatch_performed": False,
        "production_release_ready": False,
    }
