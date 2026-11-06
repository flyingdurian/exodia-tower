"""Phase 8: verify installed Liu Bei A0 against live watcher and local bytes.

Read-only. Requires the actual Windows checkout and its EXODIA localhost API.
A successful *technical* gate is not original authorship, landmark identity,
owner approval of the formatted source, or authorization to release artwork.

Usage (inside orchestrator):
  python tools/phase8_a0_local_acceptance.py
  python tools/phase8_a0_local_acceptance.py --base-url http://127.0.0.1:8767

Never POST, copy a PNG, modify a registry, or write an acceptance receipt.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import phase6_phase7_local_monitor as monitor
from tools.liu_bei_manual_dropin import scan_dropin
from tools.liu_bei_native_identity_gate import ROOT, LOCKED
from app.fleet.liu_bei_variant_preflight import (
    A0_APPROVED_VISUAL_ORIGINAL_SHA, _validate_registry,
)

SCHEMA = "exodia.phase8.liu-bei-installed-a0-acceptance/v1"
SHA = re.compile(r"^[a-f0-9]{64}$")


def correlate_installed_a0(telemetry: dict, local: dict):
    """Compare watcher API telemetry with the current checkout's actual bytes.

    Return only an explicit allowlist. No original file path, prompt, answer,
    browser session, credentials, diagnostics or raw anatomy coordinates.
    """
    if telemetry.get("schema") != monitor.SCHEMA:
        raise ValueError("Unknown local-monitor schema")
    phase = telemetry.get("phase7")
    if not isinstance(phase, dict) or local.get("schema") != "exodia.liu_bei-a0-manual-intake/v1":
        raise ValueError("A0 intake schema mismatch")
    if local.get("character_id") != "liu_bei" or phase.get("character_id") != "liu_bei":
        raise ValueError("A0 companion identity mismatch")
    if (phase.get("production_release_enabled") is not False
            or phase.get("five_state_staging_authorized") is not False
            or phase.get("owner_identity_approval") != "pending"
            or local.get("production_release_enabled") is not False
            or local.get("owner_identity_approval") != "pending"):
        raise ValueError("Liu Bei release gate or owner approval changed")

    candidate_hash = local.get("candidate_sha256")
    observed_hash = phase.get("original_sha256")
    source_exists = isinstance(candidate_hash, str) and SHA.fullmatch(candidate_hash) is not None
    source_lock = (
        source_exists
        and observed_hash == candidate_hash
        and phase.get("telemetry_consistent") is True
        and phase.get("watcher_state") == "running"
        and isinstance(phase.get("check_sequence"), int)
        and phase["check_sequence"] > 0
    )
    technical = (
        source_lock
        and local.get("technical_source_pass") is True
        and phase.get("technical_source_pass") is True
    )
    geometry = (
        technical
        and local.get("annotated_geometry_consistency_pass") is True
        and phase.get("geometry_ready_for_owner_review") is True
        and local.get("status") ==
            "technical_and_annotated_geometry_ready_for_human_review"
        and phase.get("intake_status") == local.get("status")
    )
    return {
        "schema": SCHEMA,
        "build_sha": telemetry.get("build_sha", "unknown"),
        "character_id": "liu_bei",
        "read_only": True,
        "a0_original_visual_approval_sha256": A0_APPROVED_VISUAL_ORIGINAL_SHA,
        # The installed native PNG's hash is separate from the original visual
        # master's hash, particularly when the native file was reformatted.
        "formatted_native_png_sha256": candidate_hash if source_lock else None,
        "native_canvas": list(LOCKED),
        "installed_candidate_seen": bool(source_exists),
        "watcher_and_local_byte_sha_agree": bool(source_lock),
        "native_png_technical_pass": bool(technical),
        "pixel_bound_geometry_pass": bool(geometry),
        "human_anatomy_identity_review": "pending",
        "formatted_native_source_owner_approval": "not_established_by_gate",
        "native_source_production_release_authorized": False,
        "five_state_staging_authorized": False,
        "production_release_enabled": False,
        "next_gate": (
            "human_exact_sha_visual_and_anatomy_review" if geometry
            else "annotate_actual_pixels_and_stamp_sha_bound_patches" if technical
            else "install_stable_native_png_and_confirm_watcher"
        ),
    }


async def inspect(root: Path, base_url: str):
    root = Path(root).resolve()
    if root != ROOT.resolve():
        # --root is for explicitly isolated checkouts and tests only; still
        # require the full frozen local policy to be present in that checkout.
        if not (root / "app/companions/roster.json").is_file():
            raise ValueError("Invalid isolated checkout root")
    _validate_registry(root)
    url = monitor.probe.loopback_url(base_url)
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(12, connect=3)) as client:
        telemetry = await monitor.collect(client)
    # The watcher and scanner independently inspect the original candidate;
    # never trust an API-only claim that installed bytes match local bytes.
    local = await asyncio.to_thread(scan_dropin, root)
    return correlate_installed_a0(telemetry, local)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--base-url", default="http://127.0.0.1:8767")
    return parser.parse_args(argv)


def main(argv=None):
    try:
        args = parse_args(argv)
        report = asyncio.run(inspect(args.root, args.base_url))
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0 if report["pixel_bound_geometry_pass"] else 1 if report["native_png_technical_pass"] else 2
    except (ValueError, FileNotFoundError, OSError, KeyError, TypeError,
            json.JSONDecodeError, httpx.HTTPError, RuntimeError):
        # File paths and raw error bodies can reveal the operator's local machine.
        print("EXODIA Phase 8 A0 validation unavailable (local_evidence_or_policy_error)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
