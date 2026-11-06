"""Read-only Phase 6/7 localhost monitor. Never submits provider tasks or approves art.

Run inside orchestrator:
  python tools/phase6_phase7_local_monitor.py
  python tools/phase6_phase7_local_monitor.py --watch
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import provider_e2e_probe as probe

HEADERS = probe.CLIENT_HEADER
SCHEMA = "exodia.phase6-phase7-local-readiness/v1"
EXPECTED = ("neutral", "confident", "angered", "working", "pointing")


async def get_json(client: httpx.AsyncClient, path: str):
    response = await client.get(path, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Invalid local telemetry")
    return data


def correlate(watcher: dict, preflight: dict, runtime: dict, history: dict, catalog: dict):
    """Build only an allowlisted redacted report from the four local services."""
    if watcher.get("schema") != "exodia.phase5.liu_bei-a0-watch-telemetry/v1":
        raise ValueError("Local watcher telemetry contract not installed")
    if preflight.get("character_id") != "liu_bei" or runtime.get("character_id") != "liu_bei":
        raise ValueError("Companion identity mismatch")
    if history.get("schema") != "exodia.command-history-health/v1":
        raise ValueError("Local SQLite health contract changed")
    states = runtime.get("states") or []
    if not isinstance(states, list) or tuple(x.get("key") for x in states) != EXPECTED:
        raise ValueError("Five-state review contract changed")
    if (any(x.get("asset_url") is not None for x in states)
            or runtime.get("production_release_enabled") is not False
            or preflight.get("production_release_enabled") is not False
            or watcher.get("five_state_staging_authorized") is not False):
        raise ValueError("Native artwork lock changed; inspect manually")
    consistent = (
        watcher.get("watcher_state") == "running"
        and watcher.get("intake_status") == preflight.get("intake_status")
        and watcher.get("original_sha256") == preflight.get("original_sha256")
        and watcher.get("technical_source_pass") is preflight.get("technical_source_pass")
        and watcher.get("image_bound_annotation_consistency")
            is preflight.get("image_bound_annotation_consistency")
    )
    geometry = bool(
        consistent
        and watcher.get("geometry_ready_for_owner_review") is True
        and preflight.get("technical_source_pass") is True
        and preflight.get("image_bound_annotation_consistency") is True
        and preflight.get("intake_status") ==
            "technical_and_annotated_geometry_ready_for_human_review")
    return {
        "schema": SCHEMA,
        "read_only": True,
        "build_sha": catalog.get("build_sha", "unknown"),
        "phase6": {
            "provider_status": {name: {
                "mode": catalog["provider_status"].get(name, {}).get("mode", "unavailable"),
                "observed_state": catalog["provider_status"].get(name, {}).get("observed_state", "not_observed")}
                for name in probe.MODELS},
            "authenticated_acceptance": "not_established_by_status",
            "sqlite": {"status": history.get("status"), "journal_mode": history.get("journal_mode"),
                       "total_tasks": history.get("total_tasks"),
                       "total_events": history.get("total_events"),
                       "retry_attempts": history.get("retry_attempts"),
                       "error_events": history.get("error_events")}
        },
        "phase7": {
            "character_id": "liu_bei",
            "watcher_state": watcher.get("watcher_state"),
            "intake_status": watcher.get("intake_status"),
            "check_sequence": watcher.get("check_sequence"),
            "last_checked_utc": watcher.get("last_checked_utc"),
            "last_transition_utc": watcher.get("last_transition_utc"),
            "original_sha256": watcher.get("original_sha256") if consistent else None,
            "telemetry_consistent": consistent,
            "technical_source_pass": bool(consistent and preflight.get("technical_source_pass") is True),
            "geometry_ready_for_owner_review": geometry,
            "owner_identity_approval": "pending",
            "next_gate": "exact_sha_human_visual_review" if geometry else
                         "native_png_and_image_bound_landmark_preflight",
            "five_state_staging_authorized": False,
            "production_release_enabled": False,
        },
    }


async def collect(client: httpx.AsyncClient):
    # GET only. Does not write to SQLite, submit providers or register source art.
    catalog = await probe.get_catalog(client)
    paths = (
        "/api/fleet/liu_bei-a0/watch-status",
        "/api/fleet/liu_bei-a0/preflight",
        "/api/fleet/liu_bei/pilot-runtime",
        "/api/command/history-health",
    )
    data = await asyncio.gather(*(get_json(client, p) for p in paths))
    return correlate(*data, catalog)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8767")
    parser.add_argument("--watch", action="store_true",
                        help="Keep checking on this foreground terminal; Ctrl+C stops it")
    parser.add_argument("--interval", type=float, default=1.5)
    return parser.parse_args(argv)


async def main_async(args):
    url = probe.loopback_url(args.base_url)
    if not .5 <= args.interval <= 30:
        raise ValueError("Poll interval must be 0.5–30 seconds")
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(12, connect=3)) as client:
        last = None
        while True:
            status = await collect(client)
            public = json.dumps(status, sort_keys=True, indent=2, allow_nan=False)
            if public != last:
                print(public, flush=True)
                last = public
            if not args.watch:
                return 0
            await asyncio.sleep(args.interval)


def main(argv=None):
    try:
        return asyncio.run(main_async(parse_args(argv)))
    except KeyboardInterrupt:
        return 0
    except (ValueError, httpx.HTTPError, RuntimeError, TypeError, KeyError):
        print("EXODIA local monitor unavailable (local_api_or_contract_error)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
