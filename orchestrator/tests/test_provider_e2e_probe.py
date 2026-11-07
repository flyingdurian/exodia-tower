"""Offline contract tests for the *operator-run* probe, never real-provider proof."""
import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('provider_e2e_probe',ROOT/'tools'/'provider_e2e_probe.py')
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_probe_allows_only_explicit_local_loopback_and_dispatch_gate():
    assert probe.loopback_url('http://127.0.0.1:8767') == 'http://127.0.0.1:8767'
    for bad in ('https://chatgpt.com', 'http://192.168.1.5:8767',
                'http://127.0.0.1:8767/api/command/tasks', 'http://localho.st:8767',
                'http://user:pass@localhost:8767', 'http://localhost'):
        with pytest.raises(ValueError):probe.loopback_url(bad)
    assert probe.parse_args([]).mode == 'status'
    assert probe.parse_args(['--mode', 'respond', '--model','chatgpt']).confirm_real_dispatch is False


def test_status_is_observation_only_and_api_configuration_is_individual():
    catalog={'default':'chatgpt','options':[
        {'value':p,'available':p in probe.MODELS,'status':'automatic_browser' if p in probe.MODELS else 'not_configured'}
        for p in probe.SEVEN]}
    status=probe.public_status(catalog,{'ollama':{'status':'offline'}},
       {'models':{'chatgpt':{'status':'needs_operator_login_or_review'},
                  'gemini':{'status':'ready_for_next_prompt'}}},
        {'channel':'development','commit_sha':'a'*40})
    assert status['provider_status']['chatgpt']['authenticated_e2e']=='not_verified_by_status'
    assert status['provider_status']['gemini']['observed_state']=='ready_for_next_prompt'
    assert status['provider_status']['ollama']['observed_state']=='offline'
    assert len(status['official_api_options'])==3
    assert not any(x['configured'] for x in status['official_api_options'].values())
    with pytest.raises(ValueError):probe.public_status({'default':'ollama','options':[]},{},{},{})


def test_existing_evidence_is_rejected_before_any_local_api_call(tmp_path, monkeypatch):
    evidence = tmp_path / 'accepted.json'
    evidence.write_text('DO_NOT_OVERWRITE_EXISTING_RESULT', encoding='utf-8')
    def fail_if_network_attempted(*args, **kwargs):
        raise AssertionError('Existing evidence must prevent even opening the client')
    monkeypatch.setattr(probe.httpx, 'AsyncClient', fail_if_network_attempted)
    args = probe.parse_args(['--mode', 'respond', '--model', 'chatgpt',
                             '--confirm-real-dispatch', '--evidence', str(evidence)])
    with pytest.raises(ValueError, match='Existing evidence'):
        asyncio.run(probe.main_async(args))
    assert evidence.read_text('utf-8') == 'DO_NOT_OVERWRITE_EXISTING_RESULT'


def test_real_dispatch_requires_consent_before_local_api_call(monkeypatch):
    def fail_if_network_attempted(*args, **kwargs):
        raise AssertionError('Missing consent must prevent all client traffic')
    monkeypatch.setattr(probe.httpx, 'AsyncClient', fail_if_network_attempted)
    args = probe.parse_args(['--mode', 'cancel', '--model', 'gemini'])
    with pytest.raises(ValueError, match='confirm-real-dispatch'):
        asyncio.run(probe.main_async(args))


def test_probe_error_codes_never_echo_path_credentials_or_http_body():
    secret = 'PRIVATE_BROWSER_PROFILE_AND_KEY'
    assert secret not in probe.safe_error_code(ValueError(secret))
    assert probe.safe_error_code(OSError(secret)) == 'local_evidence_io_error'
    assert probe.safe_error_code(httpx.ConnectError(secret)) == 'localhost_connection_error'
    request = httpx.Request('GET', 'http://localhost:8767/api/build-info')
    response = httpx.Response(503, request=request)
    error = httpx.HTTPStatusError(secret, request=request, response=response)
    assert probe.safe_error_code(error) == 'localhost_http_error'


def mock_client(mode='respond'):
    state={'task':None,'seen':0,'calls':[]}
    def handler(request):
        path=request.url.path;state['calls'].append((request.method,path))
        if request.method=='POST' and path=='/api/command/tasks':
            assert request.headers['X-Exodia-Client']=='exodia-dashboard'
            body=json.loads(request.content)
            assert body['custom_instructions']=='' and body['prompt']==probe.SAFE_PROMPT
            state['task']={'id':'faux-task-uuid','provider':body['model_choice'],
                           'state':'opening','answer':'','metrics':{}}
            return httpx.Response(201,json=state['task'])
        if request.method=='POST' and path.endswith('/cancel'):
            assert request.headers['X-Exodia-Client']=='exodia-dashboard'
            state['task']['state']='cancelled';return httpx.Response(200,json=state['task'])
        if request.method=='GET' and path=='/api/command/tasks':
            state['seen']+=1
            if mode=='respond' and state['seen']>=1:
                state['task']['state']='answered';state['task']['answer']='Real response text NOT to log'
            return httpx.Response(200,json={'tasks':[state['task']]})
        return httpx.Response(404)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler),base_url='http://127.0.0.1:8767'),state


def test_mock_task_response_probe_tracks_persistence_without_disclosing_response():
    async def scenario():
        client,db=mock_client()
        async with client:
            result=await probe.run_probe(client,'gemini','respond',timeout_s=3,interval_s=.001)
        assert result['result']=='local_delivery_observed' and result['answer_received']
        assert result['observed_states']==['opening','answered']
        assert 'Real response text' not in json.dumps(result)
        assert db['calls'][0]==('POST','/api/command/tasks')
    asyncio.run(scenario())


def test_mock_cancel_probe_is_local_only_and_cannot_claim_remote_abort():
    async def scenario():
        client,db=mock_client('cancel')
        async with client:
            result=await probe.run_probe(client,'chatgpt','cancel',timeout_s=3,cancel_delay_s=0,interval_s=.001)
        assert result['result']=='local_cancellation_observed'
        assert result['cancelled_locally'] is True
        assert result['remote_cancel_confirmed'] is False
        assert result['persisted_cancelled'] is True
        assert any(x[1].endswith('/cancel') for x in db['calls'])
    asyncio.run(scenario())


def test_timeout_cancels_local_job_and_never_claims_provider_success():
    async def scenario():
        client,db=mock_client('cancel')
        async with client:
            result=await probe.run_probe(client,'ollama','respond',timeout_s=1,interval_s=.05)
        assert result['result']=='inconclusive_or_failed' and result['timeout_occurred']
        assert result['cancelled_locally'] and not result['answer_received']
        assert result['remote_cancel_confirmed'] is False
    asyncio.run(scenario())
