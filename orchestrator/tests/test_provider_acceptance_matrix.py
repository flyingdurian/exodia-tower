"""Phase 6 operator-run matrix contracts: no real provider calls in CI."""
import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "provider_acceptance_matrix", ROOT / "tools/provider_acceptance_matrix.py")
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


def mock_catalog():
    options = [{"value": name, "available": name in matrix.MODELS,
                "status": "automatic_browser" if name in matrix.MODELS[:-1] else
                          "automatic_local" if name == "ollama" else "not_configured"}
               for name in matrix.probe.SEVEN]
    return {"default": "chatgpt", "options": options}


def local_client():
    calls = []
    def handler(request):
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path == "/api/command/model-options":
            return httpx.Response(200, json=mock_catalog())
        if request.method == "GET" and request.url.path == "/api/command/providers":
            return httpx.Response(200, json={"ollama": {"connected": True}})
        if request.method == "GET" and request.url.path == "/api/web/sessions":
            return httpx.Response(200, json={"models": {
                name: {"status": "ready_for_next_prompt"} for name in matrix.MODELS[:-1]}})
        if request.method == "GET" and request.url.path == "/api/build-info":
            return httpx.Response(200, json={"channel": "development", "commit_sha": "a"*40})
        if request.method == "GET" and request.url.path.endswith("/events"):
            key = request.url.path.split("/")[-2]
            return httpx.Response(200, json={"task_id": key, "events": [
                {"task_id": key, "to_state": "answered"}]})
        if request.method == "GET" and request.url.path == "/api/command/tasks/history":
            return httpx.Response(200, json={"tasks": [{
                "id": "mock-chatgpt-1", "state": "answered"}], "total": 1})
        return httpx.Response(404)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler),
                              base_url="http://127.0.0.1:8767"), calls


def test_default_matrix_is_read_only_but_chatgpt_matches_gemini_capabilities():
    assert matrix.MODELS == ("chatgpt", "gemini", "deepseek", "ollama")
    assert matrix.CAPABILITIES["chatgpt"] == matrix.CAPABILITIES["gemini"]
    assert matrix.CAPABILITIES["chatgpt"]["response_extraction"]
    async def run():
        client, calls = local_client()
        async with client:
            data = await matrix.build_matrix(client)
        assert data["read_only"] is True
        assert list(data["providers"]) == list(matrix.MODELS)
        assert all(item["status"] == "not_tested_in_read_only_mode"
                   for item in data["providers"].values())
        assert all(item["authenticated_session_verified_by_tool"] is False
                   for item in data["providers"].values())
        assert all(m == "GET" for m, _ in calls)
        assert len(data["official_api_options"]) == 3
        assert all(x["configured"] is False for x in data["official_api_options"].values())
    asyncio.run(run())


def test_explicit_verify_requires_evidence_and_confirmation_before_network(monkeypatch):
    async def run():
        args = matrix.parse_args(["--mode", "verify", "--models", "chatgpt"])
        with pytest.raises(ValueError, match="confirm-real-dispatch"):
            await matrix.main_async(args)
        args = matrix.parse_args(["--mode", "verify", "--models", "chatgpt",
                                  "--confirm-real-dispatch"])
        with pytest.raises(ValueError, match="evidence"):
            await matrix.main_async(args)
        with pytest.raises(ValueError):
            matrix.validate_models(["chatgpt", "chatgpt"])
        with pytest.raises(ValueError):
            matrix.probe.loopback_url("https://gemini.google.com/")
    asyncio.run(run())


def test_separate_response_and_cancel_trials_produce_no_fabricated_auth_claim(monkeypatch):
    called = []
    async def fake_run_probe(client, model, mode, **kwargs):
        called.append((model, mode))
        return {"task_id": f"test-{model}-{mode}", "final_state":
                "answered" if mode == "respond" else "cancelled",
                "result": "local_delivery_observed" if mode == "respond" else
                          "local_cancellation_observed",
                "answer_received": mode == "respond",
                "remote_cancel_confirmed": False,
                "evidence_scope": "real_local_task_api_no_provider_auth_inference"}
    async def fake_history(client, task_id, expected_final):
        return {"persisted": True, "events_present": True,
                "terminal_state_match": True, "history_restart_tested": False}
    monkeypatch.setattr(matrix.probe, "run_probe", fake_run_probe)
    monkeypatch.setattr(matrix, "verify_durable_record", fake_history)
    async def run():
        client, traffic = local_client()
        async with client:
            data = await matrix.build_matrix(client, models=matrix.MODELS,
                                             dispatch=True, timeout=2, cancel_delay=.1)
        assert called == [(name, stage) for name in matrix.MODELS
                         for stage in ("respond", "cancel")]
        for name, result in data["providers"].items():
            assert result["local_acceptance_checks_pass"] is True
            assert result["authenticated_session_verified_by_tool"] is False
            assert result["real_provider_approval"].startswith("requires_owner")
            assert result["response_trial"]["durable_history"]["history_restart_tested"] is False
        assert "authenticated_session_verified_by_tool\": true" not in json.dumps(data).lower()
        assert data["real_authenticated_acceptance"] == "not_established_by_this_report"
        assert all(method == "GET" for method, _ in traffic)
    asyncio.run(run())


def test_real_local_evidence_lookup_uses_exact_task_id_not_most_recent():
    async def run():
        client, calls = local_client()
        async with client:
            result = await matrix.verify_durable_record(client, "mock-chatgpt-1", "answered")
            missing = await matrix.verify_durable_record(client, "other-id", "answered")
        assert result == {"persisted": True, "events_present": True,
                          "terminal_state_match": True, "history_restart_tested": False}
        assert missing["persisted"] is False
        assert all(method == "GET" for method, _ in calls)
    asyncio.run(run())


def test_provider_timeout_or_http_error_is_sanitized_without_auto_retry(monkeypatch):
    attempts = []
    async def fail_once(client, model, mode, **kwargs):
        attempts.append((model, mode))
        raise httpx.ConnectError("DO_NOT_PRINT_LOCAL_PROFILE_AND_SECRET")
    monkeypatch.setattr(matrix.probe, "run_probe", fail_once)
    async def run():
        client, calls = local_client()
        async with client:
            result = await matrix.inspect_model(client, "chatgpt")
        assert len(attempts) == 2  # two distinct modes, not retries of one mode
        assert result["local_acceptance_checks_pass"] is False
        assert result["response_trial"]["error_code"] == "localhost_connection_error"
        assert "DO_NOT_PRINT_LOCAL_PROFILE_AND_SECRET" not in json.dumps(result)
    asyncio.run(run())
