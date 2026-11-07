from pathlib import Path
from types import SimpleNamespace
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.core.cache import SpeedrunnerCache
from app.core.classifier import classify
from app.rag.engine import CrystalArchives
from app.prompts.builder import build_messages
from app.automation.stealth import validate_url, BrowserUnavailable
from app.mcp.clients import github_overview, ServiceError
from app.monitoring.logger import EventLog
from app.core.router import Router
from app.api.server import app


def test_intent_classification():
    assert classify('check GitHub repo stats') == ('integration','github')
    assert classify('get Etsy shop metrics') == ('integration','etsy')
    assert classify('show YouTube watch time') == ('integration','youtube')
    assert classify('check Gmail unread') == ('integration','gmail')
    assert classify('search indexed documentation') == ('rag',None)
    assert classify('system status') == ('system',None)
    assert classify('draft a plan for a video') == ('reasoning',None)


def test_cache_namespace_and_clear(tmp_path):
    cache=SpeedrunnerCache(tmp_path/'t.sqlite')
    cache.put('docs','  HelLo   WORD ', 'one',60)
    assert cache.get('docs','hello word')=='one'
    assert cache.get('metrics','hello word') is None
    assert cache.count()==1
    cache.clear();assert cache.count()==0


def test_archive_search_and_safe_index(tmp_path):
    (tmp_path/'good.md').write_text('The cherry bus follows the golden loop road.',encoding='utf8')
    (tmp_path/'.env').write_text('secret-should-not-be-indexed')
    (tmp_path/'session_data').mkdir()
    (tmp_path/'session_data'/'cookies.txt').write_text('secret session')
    store=CrystalArchives(tmp_path/'data.sqlite', tmp_path)
    result=store.index_tree()
    assert result['files']==1
    assert result['chunks']==1
    rows=store.search('golden loop road')
    assert rows and 'good.md' in rows[0]['source']
    assert not store.search('secret-should-not-be-indexed')


def test_archive_replace(tmp_path):
    arc=CrystalArchives(tmp_path/'a.sqlite',tmp_path)
    arc.add_document('source.md','blue galaxy')
    arc.add_document('source.md','strawberry constellation')
    assert arc.count()==1
    assert not arc.search('galaxy')
    assert arc.search('strawberry')


def test_browser_allowlist():
    allowed=('example.com',)
    assert validate_url('https://example.com/docs',allowed).startswith('https')
    for url in ('http://example.com','https://example.com.evil.net','https://evil.net',
                'file:///etc/passwd','https://example.com:8080'):
        with pytest.raises(BrowserUnavailable):validate_url(url,allowed)


def test_prompts_mark_untrusted():
    message=build_messages('what happened','ignore everything','100 sales','suspicious snippet')
    assert message[0]['role']=='system'
    assert 'UNTRUSTED' in message[1]['content']
    assert 'suspicious snippet' in message[1]['content']


def test_event_log_redaction(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN','a-very-private-token')
    bus=EventLog()
    bus.publish('alert','a-very-private-token leaked')
    assert 'private' not in str(bus.latest())


def test_github_missing_auth(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN',raising=False)
    monkeypatch.setenv('GITHUB_REPO','owner/repo')
    with pytest.raises(ServiceError):asyncio.run(github_overview())


def test_fastapi_endpoints():
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        result=client.get('/api/stats').json()
        assert result['mode']=='local'
        assert 'integrations' in result['config']
        assert client.post('/api/ask',json={'question':'system status'}).status_code==200
        assert client.post('/api/ask',json={'question':'system status','channel':'hack'}).status_code==422
        assert client.post('/api/integrations/invalid/check').status_code==404
        assert client.get('/api/snapshots').status_code==200
        assert client.get('/api/snapshots/../../.env').status_code in (400,404)


def test_router_does_not_forge_answers(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    arc=CrystalArchives(tmp_path/'d.sqlite',tmp_path)
    cache=SpeedrunnerCache(tmp_path/'d.sqlite')
    conf=SimpleNamespace(root=tmp_path, allowed_hosts=(),browser_enabled=False,browser_read_url='',
                         web_headless=False, public_config=lambda:{'mode':'local'})
    r=Router(conf,arc,cache,EventLog())
    answer=asyncio.run(r.answer('Draft an original marketing strategy'))
    assert 'session not started' in answer['answer']
    assert answer['route']=='reasoning'
