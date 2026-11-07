"""Tests run without signing into ChatGPT, Gemini or DeepSeek."""
import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.automation.multi_wrapper import MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS, type_composer_text
from app.core.zero_api import ZeroAPIModelRouter
from app.companions.rigs import load_all, validate_rig
from app.api.server import app

class Locator:
    def __init__(self,fail=False): self.first=self;self.fail=fail;self.messages=[];self.clicks=0
    async def fill(self,s,timeout=10000):
        if self.fail: raise RuntimeError('DOM changed')
        self.messages.append(s)
    async def click(self,timeout=15000):
        if self.fail: raise RuntimeError('DOM changed')
        self.clicks+=1

class Keyboard:
    def __init__(self):self.typed=[];self.pressed=[]
    async def type(self,text,delay=0):self.typed.append((text,delay))
    async def press(self,key):self.pressed.append(key)

class Page:
    def __init__(self): self.url='https://placeholder.invalid';self.inputs={};self.captures=[];self.keyboard=Keyboard()
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
        c=Context(kwargs['user_data_dir']);c.opts=dict(kwargs);self.contexts.append(c);return c

def test_three_isolated_sessions_and_manual_replies(tmp_path):
    async def go():
        f=Factory();m=MultiWebSessionManager(tmp_path,browser_factory=f)
        statuses=await m.initialize_all()
        assert len(f.contexts)==3 and len({c.path for c in f.contexts})==3
        assert all(v['status']=='needs_operator_login_or_review' for v in statuses.values())
        router=ZeroAPIModelRouter(m)
        r=await router.generate('Review this draft','gemini')
        assert r['status']=='awaiting_operator' and r['automatic_output'] is False
        gp=f.contexts[1].pages[0]
        assert gp.inputs[PROVIDERS['gemini'].input_selector].clicks==1
        # Deliberate latency optimization: rich-text typing dispatches input events without a fixed delay.
        assert gp.keyboard.typed==[('Review this draft',0)]
        assert gp.keyboard.pressed==['ControlOrMeta+A']
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
        assert client.get('/api/web/sessions').json()['automatic_extraction']['gemini'] is True
        assert len(client.get('/api/web/sessions').json()['models'])==3
        assert client.post('/api/web/sessions/chatgpt/prepare',json={'prompt':'test'}).status_code==403
        h={'X-Exodia-Client':'exodia-dashboard'}
        assert client.post('/api/web/sessions/chatgpt/prepare',headers=h,json={'prompt':'test'}).status_code==409
        assert client.get('/api/rigs').json()['rigs']['kiko']['production_ready'] is False
        assert client.get('/rig-lab').status_code==200

def test_native_textarea_uses_normal_fill(tmp_path):
    async def run():
        f=Factory();m=MultiWebSessionManager(tmp_path,browser_factory=f)
        await m.initialize_all()
        result=await m.prepare_prompt('deepseek','Plain text')
        p=m._pages['deepseek']
        assert p.inputs[PROVIDERS['deepseek'].input_selector].messages==['Plain text']
        assert p.keyboard.typed==[]
        assert result['status']=='awaiting_operator'
        await m.close()
    asyncio.run(run())

def test_chatgpt_contenteditable_receives_keyboard_events(tmp_path):
    async def run():
        f=Factory();m=MultiWebSessionManager(tmp_path,browser_factory=f)
        await m.initialize_all()
        await m.prepare_prompt('chatgpt','Explain this diagram')
        p=m._pages['chatgpt']
        assert p.keyboard.typed==[('Explain this diagram',0)]
        assert p.inputs[PROVIDERS['chatgpt'].input_selector].messages==[]
        await m.close()
    asyncio.run(run())

def test_custom_user_agent_is_passed_to_browser_without_disabling_security(tmp_path,monkeypatch):
    async def run():
        monkeypatch.setenv('EXODIA_BROWSER_USER_AGENT','ExodiaTowerBrowserTest/1.0')
        factory=Factory()
        m=MultiWebSessionManager(tmp_path,browser_factory=factory)
        await m.initialize_all()
        assert all(ctx.opts.get('user_agent')=='ExodiaTowerBrowserTest/1.0' for ctx in factory.contexts)
        assert all('args' not in ctx.opts for ctx in factory.contexts)
        await m.close()
    asyncio.run(run())

def test_optional_chromium_blink_flag_is_off_by_default_but_opt_in(tmp_path,monkeypatch):
    async def run():
        monkeypatch.delenv('EXODIA_EXPERIMENTAL_CHROMIUM_FLAG',raising=False)
        plain=Factory()
        manager=MultiWebSessionManager(tmp_path/'plain',browser_factory=plain)
        await manager.initialize_all()
        assert all('args' not in c.opts for c in plain.contexts)
        await manager.close()
        monkeypatch.setenv('EXODIA_EXPERIMENTAL_CHROMIUM_FLAG','true')
        opted=Factory()
        manager=MultiWebSessionManager(tmp_path/'opted',browser_factory=opted)
        await manager.initialize_all()
        assert all(c.opts.get('args')==['--disable-blink-features=AutomationControlled'] for c in opted.contexts)
        await manager.close()
    asyncio.run(run())


def test_browser_composer_multiline_never_sends_bare_enter():
    """Newlines use Shift+Enter; an ordinary Enter can submit a browser message."""
    async def run():
        p=Page()
        mode=await type_composer_text(p,'First line\nSecond line\nThird')
        assert mode=='shift_enter_lines'
        assert p.keyboard.typed==[('First line',0),('Second line',0),('Third',0)]
        assert p.keyboard.pressed==['Shift+Enter','Shift+Enter']
        assert 'Enter' not in p.keyboard.pressed
    asyncio.run(run())

def test_browser_composer_long_prompt_prefers_insert_text_when_available():
    """Long prompts should use the fast input-event path instead of slow per-character typing."""
    class InsertKeyboard(Keyboard):
        def __init__(self):
            super().__init__();self.inserted=[]
        async def insert_text(self,text):self.inserted.append(text)
    async def run():
        p=Page();p.keyboard=InsertKeyboard()
        prompt='Long operator request ' * 20
        mode=await type_composer_text(p,prompt)
        assert mode=='insert_text'
        assert p.keyboard.inserted==[prompt.strip()]
        assert p.keyboard.typed==[]
    asyncio.run(run())
