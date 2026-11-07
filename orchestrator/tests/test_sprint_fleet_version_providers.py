"""Owner Sprint 2026-11-04: identity, art state, build info, transport safeguards."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.api import server
from app.automation.provider_catalog import CHOICES, ADVANCED, selection
from app.build_info import build_info
from app.operations.inbox import Inbox

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / 'orchestrator'
EXPECTED_IDS = ('kiko', 'liu_bei', 'memory', 'archives', 'inventory',
                'vault', 'ninja', 'cache', 'strategy', 'nova')
EXPRESSIONS = set('neutral happy joyful excited gentle smiling_closed laughing amused confident serious focused thinking curious surprised concerned worried sad disappointed angered blushing'.split())
ACTIONS = set('idle working monitoring pointing explaining celebrating defeat stretching sleeping waking_up tantrum thinking_deeper awaiting_command'.split())
LABELS = (
    'ChatGPT (chronos)', 'Gemini (chronos)', 'DeepSeek (chronos)',
    'Ollama (automatic local)', 'ChatGPT (api)', 'Gemini (api)', 'DeepSeek (api)'
)
HEADERS = {'x-exodia-client': 'exodia-dashboard'}

def test_fleet_reconciled_ten_ids_twenty_expressions_thirteen_actions():
    for path in (APP_ROOT/'app/companions/roster.json', APP_ROOT/'frontend/companions/roster.json'):
        roster = json.loads(path.read_text())
        assert tuple(a['id'] for a in roster) == EXPECTED_IDS
        assert tuple(a['name'] for a in roster) == ('Albedo', 'Liu Bei', 'Mira', 'Lyra', 'Pip', 'Aurelia', 'Nyx', 'Mochi', 'Orion', 'Nova')
    registry = json.loads((APP_ROOT/'frontend/companions/production/kiko/portrait_registry.json').read_text())
    assert registry['character_id'] == 'kiko'
    assert len(registry['states']) == 33
    assert {key for key, value in registry['states'].items() if value['category'] == 'expression'} == EXPRESSIONS
    assert {key for key, value in registry['states'].items() if value['category'] == 'action'} == ACTIONS
    assert all(value['status'] == 'pending_production_art' for value in registry['states'].values())
    assert registry['release']['enabled'] is False
    standard = (ROOT/'docs/EXODIA_FLEET_33_STATE_ART_STANDARD.md').read_text()
    expressions_text = standard.split('### 20 expressions', 1)[1].split('### 13 actions', 1)[0]
    actions_text = standard.split('### 13 actions', 1)[1].split('## 5.', 1)[0]
    parsed_expressions = re.findall(r'^\| `([a-z_]+)` \|', expressions_text, re.MULTILINE)
    parsed_actions = re.findall(r'^\| `([a-z_]+)` \|', actions_text, re.MULTILINE)
    assert len(parsed_expressions) == 20 and set(parsed_expressions) == EXPRESSIONS
    assert len(parsed_actions) == 13 and set(parsed_actions) == ACTIONS
    assert '≥72 unique Idle frames' in standard
    assert '±2 px shoulders' in standard

def test_version_api_is_single_source_and_commit_is_reproducible(monkeypatch):
    sha = 'a'*40
    monkeypatch.setenv('EXODIA_BUILD_SHA',sha)
    monkeypatch.setenv('EXODIA_BUILD_CHANNEL','development')
    with TestClient(server.app) as client:
        v = client.get('/api/build-info').json()
        assert v['version'] == server.app.version
        assert v['short_sha'] == sha[:12]
        assert v['verified_commit'] is True and v['channel']=='development'
        assert v['label']=='EXODIA v0.3.0-dev · '+sha[:12]
        for url in ('/', '/test-workbench','/operations-legacy'):
            page=client.get(url)
            assert page.status_code==200 and 'buildBadge' in page.text

def test_build_sha_fallback_does_not_invent_commit(monkeypatch):
    monkeypatch.setenv('EXODIA_BUILD_SHA','not-a-sha')
    b=build_info()
    assert b['short_sha']=='unknown' and b['commit_sha'] is None
    assert b['verified_commit'] is False

def test_seven_choices_exactly_ordered_and_modes():
    assert len(CHOICES)==7
    assert tuple(c.label for c in CHOICES)==LABELS
    assert tuple(c.value for c in CHOICES)==('chatgpt','gemini','deepseek','ollama',
        'chatgpt:api','gemini:api','deepseek:api')
    assert tuple(c.transport for c in CHOICES)==('browser',)*3+('local',)+('api',)*3
    assert all(not x.available for x in CHOICES[4:])
    assert selection('chatgpt').provider_id=='chatgpt'
    assert selection('ollama').transport=='local'
    assert selection('deepseek').status=='automatic_browser'
    assert set(ADVANCED)=={'custom_web','web_slot_2','web_slot_3'}
    for c in CHOICES[4:]:
        with pytest.raises(ValueError, match='not configured'):
            selection(c.value)
    with pytest.raises(ValueError, match='transport mismatch'):
        selection('chatgpt','api')

def test_public_model_catalog_and_model_task_error_are_truthful(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'inbox',Inbox(tmp_path/'tasks.sqlite'))
    with TestClient(server.app) as client:
        d=client.get('/api/command/model-options').json()
        assert d['default']=='chatgpt'
        assert [a['label'] for a in d['options']]==list(LABELS)
        assert len(d['advanced'])==3
        for api_value in ('chatgpt:api','gemini:api','deepseek:api'):
            payload={'model_choice':api_value,'agent_id':'kiko','prompt':'Check model setup','transport':'api'}
            r=client.post('/api/command/tasks',json=payload,headers=HEADERS)
            assert r.status_code==422 and 'not configured' in r.text
            a=client.post('/api/ask',json={'model_choice':api_value,'transport':'api','question':'Research the roadmap'})
            assert a.status_code==422 and 'not configured' in a.text
        assert client.get('/api/command/tasks').json()['tasks']==[]
        assert client.post('/api/command/tasks',json={'model_choice':'chatgpt','transport':'api','agent_id':'kiko','prompt':'Should fail'},headers=HEADERS).status_code==422
        assert client.post('/api/ask',json={'model_choice':'chatgpt','channel':'api','question':'Should not use browser'}).status_code==409

def test_legacy_ids_and_deepseek_starts_automatically(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'inbox',Inbox(tmp_path/'tasks.sqlite'))
    async def fake_send(platform, prompt, *, phase=None):
        assert platform=='deepseek' and prompt=='Prepare a campaign plan'
        if phase:
            for stage in ('typing','submitting','waiting_for_reply'): phase(stage)
        return {'answer':'DeepSeek prepared a campaign plan with three concrete steps.','automatic_output':True,'timings':{'total_s':1.2},'media':[]}
    monkeypatch.setattr(server.router.sessions,'send_prompt_robust',fake_send)
    with TestClient(server.app) as client:
        for provider in ('gemini','chatgpt','deepseek','ollama'):
            assert selection(provider).provider_id==provider
        p={'model_choice':'deepseek','agent_id':'nova','prompt':'Prepare a campaign plan','transport':'browser'}
        t=client.post('/api/command/tasks',json=p,headers=HEADERS)
        assert t.status_code==201
        assert t.json()['provider']=='deepseek' and t.json()['state']=='opening'
        import time
        latest=None
        for _ in range(40):
            latest=client.get('/api/command/tasks').json()['tasks'][0]
            if latest['state']=='answered': break
            time.sleep(.02)
        assert latest['state']=='answered'
        assert latest['answer'].startswith('DeepSeek prepared')
        assert client.get('/api/command/tasks').json()['automatic_extraction']['deepseek'] is True

def test_ask_ollama_routes_to_local_backend_without_browser(monkeypatch):
    async def mock_generate(prompt,*,companion):
        assert companion=='kiko' and prompt=='Generate a test sentence'
        return {'answer':'From local Ollama','provider':'ollama','model':'local-test','tokens':3}
    async def prohibited(*args,**kwargs):
        raise AssertionError('Browser router must not execute for local Ollama')
    monkeypatch.setattr(server.local_model,'generate',mock_generate)
    monkeypatch.setattr(server.router,'answer',prohibited)
    with TestClient(server.app) as client:
        r=client.post('/api/ask',json={'question':'Generate a test sentence','model_choice':'ollama','transport':'local'})
        assert r.status_code==200
        assert r.json()['route']=='local' and r.json()['answer']=='From local Ollama'
        assert r.json()['data']['transport']=='local'
