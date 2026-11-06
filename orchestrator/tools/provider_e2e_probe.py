"""Explicit operator-run *real* local EXODIA transport acceptance probe.

Default mode is read-only. Never opens provider logins, reads cookies or stores
prompts/responses/secrets. This probes the actual current EXODIA task API; it is
not a mock provider implementation or an authenticated CI certification.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

import httpx

MODELS = ('chatgpt', 'gemini', 'deepseek', 'ollama')
SEVEN = ('chatgpt', 'gemini', 'deepseek', 'ollama', 'chatgpt:api', 'gemini:api', 'deepseek:api')
FINISHED = frozenset({'answered', 'failed', 'cancelled'})
NONTERMINAL = frozenset({'draft', 'queued', 'opening', 'cooldown', 'researching',
                         'typing', 'submitting', 'running', 'rendering_media',
                         'waiting_for_reply', 'awaiting_operator'})
SAFE_PROMPT = 'For a local software integration test, reply with one short sentence about reliable task completion.'
CLIENT_HEADER = {'X-Exodia-Client': 'exodia-dashboard'}


def loopback_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Only HTTP loopback EXODIA endpoints are allowed; never send test prompts to external URLs')
    if parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Use only the root localhost URL without credentials, paths or query strings')
    if parsed.port is None:
        raise ValueError('Specify the local EXODIA port explicitly')
    return f'{parsed.scheme}://{parsed.netloc}'


def public_status(catalog: dict, providers: dict, sessions: dict, build: dict) -> dict:
    options = catalog.get('options') or []
    values = tuple(option.get('value') for option in options)
    if values != SEVEN or catalog.get('default') != 'chatgpt':
        raise ValueError('Seven canonical model IDs or ChatGPT default have changed')
    api = {option['value']: {'configured': bool(option.get('available')),
                              'status': str(option.get('status') or 'unknown')}
           for option in options if option['value'].endswith(':api')}
    browser = sessions.get('models') or {}
    local = providers.get('ollama') or {}
    return {
        'build_sha': build.get('commit_sha') or 'unknown',
        'build_channel': build.get('channel') or 'unknown',
        'provider_status': {
            model: {'mode': 'local' if model == 'ollama' else 'browser',
                    'observed_state': (('local_service_connected' if local.get('connected') else 'local_service_offline')
                        if model == 'ollama' and 'connected' in local
                        else str((local if model == 'ollama' else browser.get(model) or {}).get('status', 'not_observed'))),
                    'authenticated_e2e': 'not_verified_by_status'}
            for model in MODELS},
        'official_api_options': api,
        'claim': 'Status is local telemetry only; not authenticated end-to-end acceptance'
    }


async def get_catalog(client: httpx.AsyncClient):
    urls = ('/api/command/model-options', '/api/command/providers',
            '/api/web/sessions', '/api/build-info')
    payloads = []
    for url in urls:
        response = await client.get(url)
        response.raise_for_status()
        payloads.append(response.json())
    return public_status(*payloads)


async def task_by_id(client: httpx.AsyncClient, task_id: str) -> dict:
    r = await client.get('/api/command/tasks')
    r.raise_for_status()
    for task in r.json().get('tasks', []):
        if task.get('id') == task_id:
            return task
    raise RuntimeError('Task ID disappeared from the persistent task inbox')


async def create_task(client: httpx.AsyncClient, model: str) -> dict:
    if model not in MODELS:
        raise ValueError('Only four executable canonical model choices may be probed')
    r = await client.post('/api/command/tasks', headers=CLIENT_HEADER, json={
        'agent_id': 'kiko', 'model_choice': model,
        'transport': 'local' if model == 'ollama' else 'browser',
        'web_research': False, 'prompt': SAFE_PROMPT,
        'custom_instructions': ''})
    r.raise_for_status()
    if r.status_code != 201 or not r.json().get('id'):
        raise RuntimeError('EXODIA did not return a new durable task ID')
    return r.json()


def capture_public_evidence(task: dict, states: list[str], elapsed_s: float) -> dict:
    metrics = task.get('metrics') or {}
    return {
        'task_id': task.get('id'), 'model': task.get('provider'),
        'final_state': task.get('state'), 'observed_states': states,
        'answer_received': task.get('state') == 'answered' and bool((task.get('answer') or '').strip()),
        'observed_elapsed_s': round(elapsed_s, 3),
        'reported_total_s': metrics.get('total_s') if isinstance(metrics.get('total_s'), (int, float)) else None,
        'reported_first_text_s': metrics.get('first_text_s') if isinstance(metrics.get('first_text_s'), (int, float)) else None,
        'remote_cancel_confirmed': False,
        'evidence_scope': 'real_local_task_api_no_provider_auth_inference',
    }


async def run_probe(client: httpx.AsyncClient, model: str, mode: str,
                    timeout_s: float = 90, cancel_delay_s: float = 1.0,
                    interval_s: float = .65) -> dict:
    if mode not in ('respond', 'cancel'):
        raise ValueError('Run mode must be respond or cancel')
    if timeout_s < 1 or timeout_s > 900 or interval_s <= 0 or interval_s > 10:
        raise ValueError('Timeout or poll cadence outside safe bounds')
    start = monotonic()
    initial = await create_task(client, model)
    task_id = initial['id']
    task = initial
    visited = []
    cancelled_locally = False
    reached_deadline = False
    while True:
        state = str(task.get('state') or 'unknown')
        if not visited or visited[-1] != state:
            visited.append(state)
        elapsed = monotonic() - start
        if mode == 'cancel' and not cancelled_locally and elapsed >= cancel_delay_s and state not in FINISHED:
            response = await client.post(f'/api/command/tasks/{task_id}/cancel', headers=CLIENT_HEADER)
            response.raise_for_status()
            task = response.json()
            cancelled_locally = task.get('state') == 'cancelled'
            continue
        if state in FINISHED:
            break
        if elapsed >= timeout_s:
            reached_deadline = True
            # Do not leave a persistent local job running silently after timeout.
            response = await client.post(f'/api/command/tasks/{task_id}/cancel', headers=CLIENT_HEADER)
            if response.status_code == 200:
                task = response.json()
                cancelled_locally = task.get('state') == 'cancelled'
            else:
                task = await task_by_id(client, task_id)
            if not visited or visited[-1] != task.get('state'):
                visited.append(str(task.get('state')))
            break
        await asyncio.sleep(interval_s)
        task = await task_by_id(client, task_id)
    evidence = capture_public_evidence(task, visited, monotonic()-start)
    evidence['mode'] = mode
    evidence['timeout_occurred'] = reached_deadline
    evidence['cancelled_locally'] = cancelled_locally
    evidence['manual_handoff_observed'] = 'awaiting_operator' in visited
    evidence['authenticated_provider_acceptance'] = 'requires_independent_session_evidence'
    evidence['result'] = ('local_delivery_observed' if (mode == 'respond' and evidence['answer_received'] and not reached_deadline and not evidence['manual_handoff_observed'])
                          else 'local_cancellation_observed' if (mode == 'cancel' and cancelled_locally and task.get('state') == 'cancelled' and not reached_deadline)
                          else 'inconclusive_or_failed')
    if mode == 'cancel' and evidence['result'] == 'local_cancellation_observed':
        # Catch late-result persistence while remaining explicit about remote side effects.
        await asyncio.sleep(min(1.0, interval_s))
        persisted = await task_by_id(client, task_id)
        evidence['persisted_cancelled'] = (persisted.get('state') == 'cancelled' and not persisted.get('answer'))
        if not evidence['persisted_cancelled']:
            evidence['result'] = 'inconclusive_or_failed'
    return evidence


async def main_async(args) -> int:
    url = loopback_url(args.base_url)
    async with httpx.AsyncClient(base_url=url, timeout=httpx.Timeout(15.0, connect=3.0)) as client:
        report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                  'source': 'operator_localhost_real_api_probe',
                  'read_only': args.mode == 'status',
                  'status': await get_catalog(client)}
        if args.mode != 'status':
            if not args.model:
                raise ValueError('Supply --model for a real request/cancellation probe')
            if not args.confirm_real_dispatch:
                raise ValueError('Explicit --confirm-real-dispatch required to create a live task')
            report['probe'] = await run_probe(client, args.model, args.mode,
                timeout_s=args.timeout, cancel_delay_s=args.cancel_delay)
    safe_json = json.dumps(report, indent=2, sort_keys=True)
    print(safe_json)
    if args.evidence:
        path = Path(args.evidence)
        if path.exists():
            raise ValueError('Refusing to overwrite existing evidence; choose a new output filename')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(safe_json + '\n', encoding='utf-8')
    return 2 if args.mode != 'status' and report['probe']['result'] not in ('local_delivery_observed', 'local_cancellation_observed') else 0


def parse_args(argv=None):
    p=argparse.ArgumentParser(description='EXODIA real localhost task acceptance; read-only by default')
    p.add_argument('--base-url', default='http://127.0.0.1:8767')
    p.add_argument('--mode', choices=('status','respond','cancel'), default='status')
    p.add_argument('--model', choices=MODELS)
    p.add_argument('--confirm-real-dispatch', action='store_true', help='Explicitly authorize live benign task submission')
    p.add_argument('--timeout', type=float, default=90)
    p.add_argument('--cancel-delay', type=float, default=1.0)
    p.add_argument('--evidence', help='Optional local REDACTED JSON evidence file; never overwritten')
    return p.parse_args(argv)


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main_async(parse_args())))
    except (ValueError, httpx.HTTPError, RuntimeError) as exc:
        print(f'EXODIA provider probe unavailable: {exc}', file=sys.stderr)
        sys.exit(2)
