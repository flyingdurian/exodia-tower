"""Phase 6: operator-controlled four-provider EXODIA acceptance matrix.

The PR #13 probe remains the sole dispatcher. Default is read-only. Running
responses/cancellation across real signed-in browser profiles or Ollama
requires an explicit command on the owner's isolated Windows checkout.
Mocked CI cannot establish authenticated provider acceptance.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import provider_e2e_probe as probe

SCHEMA = "exodia.phase6.provider-acceptance-matrix/v1"
MODELS = probe.MODELS
CAPABILITIES = {
    "chatgpt": {"transport": "browser", "submission": True,
                "response_extraction": True, "local_cancellation": True},
    "gemini": {"transport": "browser", "submission": True,
               "response_extraction": True, "local_cancellation": True},
    "deepseek": {"transport": "browser", "submission": True,
                 "response_extraction": True, "local_cancellation": True},
    "ollama": {"transport": "local", "submission": True,
               "response_extraction": True, "local_cancellation": True},
}


def validate_models(models):
    selected = tuple(models)
    if not selected or len(selected) != len(set(selected)) or any(x not in MODELS for x in selected):
        raise ValueError("Select unique executable model names from chatgpt, gemini, deepseek, ollama")
    return selected


def safe_error_code(exc):
    """Never forward server error messages, local paths, account data or URLs."""
    if isinstance(exc, httpx.TimeoutException):
        return "localhost_timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return "localhost_http_" + str(code) if code in (401, 403, 404, 409, 422, 429, 500, 503) else "localhost_http_error"
    if isinstance(exc, httpx.HTTPError):
        return "localhost_connection_error"
    return "probe_contract_error"


async def verify_durable_record(client, task_id, expected_final):
    """Read events + paginated history by exact task ID without exporting row content."""
    if not isinstance(task_id, str) or not 1 <= len(task_id) <= 128:
        return {"persisted": False, "events_present": False,
                "terminal_state_match": False, "history_restart_tested": False}
    ident = quote(task_id, safe="")
    response = await client.get("/api/command/tasks/" + ident + "/events", headers=probe.CLIENT_HEADER)
    response.raise_for_status()
    timeline = response.json().get("events") or []
    events_present = (isinstance(timeline, list) and len(timeline) > 0 and
                      all(isinstance(x, dict) and x.get("task_id") == task_id for x in timeline))
    last = timeline[-1].get("to_state") if events_present else None
    found = False
    for offset in range(0, 1000, 200):
        page = await client.get("/api/command/tasks/history",
                                headers=probe.CLIENT_HEADER, params={"limit": 200, "offset": offset})
        page.raise_for_status()
        tasks = page.json().get("tasks") or []
        if not isinstance(tasks, list):
            break
        if any(isinstance(t, dict) and t.get("id") == task_id and
               t.get("state") == expected_final for t in tasks):
            found = True
            break
        if len(tasks) < 200:
            break
    return {"persisted": found, "events_present": events_present,
            "terminal_state_match": bool(events_present and last == expected_final),
            # Reading durable DB records does not prove they survive a later app restart.
            "history_restart_tested": False}


async def inspect_model(client, model, *, timeout=120, cancel_delay=1):
    """Two separate operator-authorized tasks; no blind retry on failure."""
    results = {}
    for mode in ("respond", "cancel"):
        try:
            evidence = await probe.run_probe(
                client, model, mode, timeout_s=timeout, cancel_delay_s=cancel_delay)
            record = await verify_durable_record(client, evidence.get("task_id"),
                                                 evidence.get("final_state"))
            results[mode] = {**evidence, "durable_history": record}
        except (httpx.HTTPError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            results[mode] = {"result": "inconclusive_or_failed",
                             "error_code": safe_error_code(exc),
                             "evidence_scope": "operator_localhost_api_only"}
            # A failed submission is not retried automatically, because the
            # remote consumer site might have already received the prompt.
    response = results["respond"]
    cancel = results["cancel"]
    observed = (
        response.get("result") == "local_delivery_observed" and
        response.get("durable_history", {}).get("persisted") is True and
        response.get("durable_history", {}).get("terminal_state_match") is True and
        cancel.get("result") == "local_cancellation_observed" and
        cancel.get("durable_history", {}).get("persisted") is True and
        cancel.get("durable_history", {}).get("terminal_state_match") is True
    )
    return {
        "provider": model,
        "implemented_transport_contract": CAPABILITIES[model],
        "response_trial": response,
        "cancellation_trial": cancel,
        "local_acceptance_checks_pass": observed,
        "authenticated_session_verified_by_tool": False,
        "real_provider_approval": "requires_owner_authenticated_session_evidence",
        "status": "local_traces_observed_pending_auth_evidence" if observed else "inconclusive_or_failed",
    }


async def build_matrix(client, models=MODELS, *, dispatch=False, timeout=120,
                       cancel_delay=1):
    selected = validate_models(models)
    if dispatch and (not isinstance(timeout, (int, float)) or not 1 <= timeout <= 900 or
                     not isinstance(cancel_delay, (int, float)) or
                     not 0 <= cancel_delay < timeout):
        raise ValueError("Unsafe probe timing")
    # No POST is possible unless the caller has separately granted consent.
    status = await probe.get_catalog(client)
    report = {
        "schema": SCHEMA, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "operator_localhost_existing_pr13_runner",
        "read_only": not dispatch, "build_sha": status["build_sha"],
        "build_channel": status["build_channel"],
        "official_api_options": status["official_api_options"],
        "providers": {},
        "real_authenticated_acceptance": "not_established_by_this_report",
        "claim": "ChatGPT, Gemini and DeepSeek Chronos support automatic submissions, extraction and local cancellation; live signed-in results require independent acceptance evidence",
    }
    for model in selected:
        if dispatch:
            report["providers"][model] = await inspect_model(
                client, model, timeout=timeout, cancel_delay=cancel_delay)
        else:
            report["providers"][model] = {
                "provider": model,
                "implemented_transport_contract": CAPABILITIES[model],
                "local_runtime_status": status["provider_status"][model],
                "status": "not_tested_in_read_only_mode",
                "authenticated_session_verified_by_tool": False,
            }
    return report


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:8767")
    p.add_argument("--models", choices=MODELS, nargs="+", default=list(MODELS))
    p.add_argument("--mode", choices=("status", "verify"), default="status")
    p.add_argument("--confirm-real-dispatch", action="store_true")
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--cancel-delay", type=float, default=1)
    p.add_argument("--evidence", type=Path)
    return p.parse_args(argv)


async def main_async(args):
    selected = validate_models(args.models)
    url = probe.loopback_url(args.base_url)
    if args.mode == "verify" and not args.confirm_real_dispatch:
        raise ValueError("--confirm-real-dispatch is required before creating real tasks")
    if args.mode == "verify" and args.evidence is None:
        raise ValueError("--evidence is required for durable local acceptance results")
    if args.evidence is not None and args.evidence.exists():
        raise ValueError("Existing evidence may not be overwritten")
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15, connect=3)) as client:
        report = await build_matrix(
            client, selected, dispatch=args.mode == "verify",
            timeout=args.timeout, cancel_delay=args.cancel_delay)
    safe_text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    print(safe_text)
    if args.evidence is not None:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        with args.evidence.open("x", encoding="utf-8") as dest:
            dest.write(safe_text + "\n")
    return 2 if args.mode == "verify" and not all(
        x.get("local_acceptance_checks_pass") for x in report["providers"].values()
    ) else 0


def main(argv=None):
    try:
        return asyncio.run(main_async(parse_args(argv)))
    except (ValueError, httpx.HTTPError, RuntimeError) as exc:
        # Error details can contain sensitive local filenames. A fixed reason
        # code is sufficient for CLI failures.
        print("EXODIA Phase 6 matrix unavailable (" + safe_error_code(exc) + ")", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
