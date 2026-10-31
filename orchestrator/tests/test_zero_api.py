"""Tests run without signing into ChatGPT, Gemini or DeepSeek."""
import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.automation.multi_wrapper import MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS
from app.core.zero_api import ZeroAPIModelRouter
from app.companions.rigs import load_all, validate_rig
from app.api.server import app

class Locator:
    def __init__(self,fail=False): self.first=self;self.fail=fail;self.messages=[]
    async def fill(self,s,timeout=10000):
        if self.fail: raise RuntimeError('DOM changed')
        self.messages.append(s)

class Page:
    def __init__(self): self.url='https://placeholder.invalid';self.inputs={};self.captures=[]
    async def goto(self,url,**kwargs): self.url=url
    def locator(self,sel):
        if sel not in self.inputs: self.inputs[sel]=Locator()
        return self.inputs[sel]
    async def screenshot(self,**kwargs):
        self.captures.append(kwargs['path']);Path(kwargs['path']).write_bytes(b'fake')

class Context:
    def __init__(self,path):self.pages=[Page()];self.path=path;self.closed=False
    async def close(self):self.closed=True

class Factory:
    def __init__(self):self.contexts=[]
    async def launch_persistent_context(self,**kwargs):
        c=Context(kwargs['user_data_dir']);self.contexts.append(c);return c

def test_three_isolated_sessions_and_manual_replies(tmp_path):
    async def go():
        f=Factory();m=MultiWebSessionManager(tmp_path,browser_factory=f)
        statuses=await m.initialize_all()
        assert len(f.contexts)==3 and len({c.path for c in f.contexts})==3
        assert all(v['status']=='needs_operator_login_or_review' for v in statuses.values())
        router=ZeroAPIModelRouter(m)
        r=await router.generate('Review this draft','gemini')
        assert r['status']=='awaiting_operator' and r['automatic_output'] is False
        assert f.contexts[1].pages[0].inputs[PROVIDERS['gemini'].input_selector].messages==['Review this draft']
        with pytest.raises(OperatorActionRequired):m.receive_operator_response('chatgpt','not pending')
        result=router.record_operator_response('gemini','Copied manually')
        assert result['source']=='manual_copy' and result['verified'] is False
        await m.close()
        assert all(c.closed for c in f.contexts)
    asyncio.run(go())

def test_dom_error_screenshot_no_retry(tmp_path):
    async def go():
        m=MultiWebSessionManager(tmp_path,browser_factory=Factory())
        await m.initialize_all()
        p=m._pages['chatgpt']
        p.inputs[PROVIDERS['chatgpt'].input_selector]=Locator(fail=True)
        with pytest.raises(SessionError,match='screenshot'):await m.prepare_prompt('chatgpt','Explain')
        assert m.snapshot()['chatgpt']['status']=='dom_error_manual_review'
        assert len(p.captures)==1 and Path(p.captures[0]).exists()
        await m.close()
    asyncio.run(go())

def test_unapproved_navigation_and_model(tmp_path):
    m=MultiWebSessionManager(tmp_path,browser_factory=Factory())
    with pytest.raises(ValueError):asyncio.run(m.prepare_prompt('invalid','Test'))
    with pytest.raises(SessionError):m._check_destination('gemini','https://gemini.google.com.evil.test')

def test_10_rig_manifests():
    from app.config import ROOT
    rigs=load_all(ROOT)
    assert len(rigs)==10
    for manifest in rigs.values():
        validate_rig(manifest)
        assert len(manifest['bones'])==22
        assert len(manifest['poses'])==24
        assert manifest['production_ready'] is False

def test_web_endpoints_require_operator():
    with TestClient(app) as client:
        assert client.get('/api/web/sessions').json()['automatic_extraction'] is False
        assert len(client.get('/api/web/sessions').json()['models'])==3
        assert client.post('/api/web/sessions/chatgpt/prepare',json={'prompt':'test'}).status_code==403
        h={'X-Exodia-Client':'exodia-dashboard'}
        assert client.post('/api/web/sessions/chatgpt/prepare',headers=h,json={'prompt':'test'}).status_code==409
        assert client.get('/api/rigs').json()['rigs']['kiko']['production_ready'] is False
        assert client.get('/rig-lab').status_code==200
