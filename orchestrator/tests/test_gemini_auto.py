"""Signed-in Gemini browser automation: synthetic DOM tests, no real Google account."""
import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.automation.multi_wrapper import MultiWebSessionManager, SessionError, PROVIDERS

class Editor:
    def __init__(self,page): self.page=page;self.first=self
    async def is_visible(self,timeout=1500): return True
    async def click(self,timeout=15000): self.page.focused=True

class Sender:
    def __init__(self,page): self.page=page;self.first=self
    async def is_visible(self,timeout=1500):return True
    async def click(self,timeout=15000):
        assert self.page.focused and self.page.typed
        self.page.sent+=1
        self.page.responses.append("Streaming Gemini result [1].")

class History:
    def __init__(self,page): self.page=page;self.last=self
    async def count(self):return len(self.page.responses)
    async def inner_text(self,timeout=7000):return self.page.responses[-1]

class Stop:
    def __init__(self,page):self.page=page
    async def is_visible(self):return False

class Keyboard:
    def __init__(self,page):self.page=page;self.pressed=[]
    async def type(self,content,delay=4):self.page.typed=content
    async def insert_text(self,content):self.page.typed=content;self.page.used_insert_text=True
    async def press(self,key):self.pressed.append(key)

class FakePage:
    def __init__(self):
        self.url='https://gemini.google.com/app'
        self.keyboard=Keyboard(self);self.responses=['Old answer should not be reused']
        self.typed='';self.sent=0;self.focused=False
        self.shots=[]
    async def goto(self,url,**kwargs):self.url=url
    def locator(self,selector):
        if selector==MultiWebSessionManager.GEMINI_RESPONSE:return History(self)
        if selector==MultiWebSessionManager.GEMINI_STOP:return Stop(self)
        if selector in MultiWebSessionManager.GEMINI_EDITORS:return Editor(self)
        if selector in MultiWebSessionManager.GEMINI_SEND:return Sender(self)
        raise AssertionError('unexpected selector: '+selector)
    async def screenshot(self,**kwargs):
        path=Path(kwargs['path']);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'diagnostic')
        self.shots.append(str(path))

class Context:
    def __init__(self):self.pages=[FakePage()];self.closed=False
    async def close(self):self.closed=True

class Factory:
    def __init__(self):self.contexts=[];self.arguments=[]
    async def launch_persistent_context(self,**kwargs):
        self.arguments.append(kwargs);context=Context();self.contexts.append(context);return context

def test_gemini_automatic_types_submits_waits_and_returns_new_reply(tmp_path):
    async def run():
        factory=Factory();manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        states=[]
        output=await manager.send_prompt_robust("gemini","Summarize this article",phase=states.append)
        assert output['answer']=="Streaming Gemini result [1]."
        assert output['automatic_output'] is True
        assert output['source']=="gemini_visible_browser"
        metrics=output['timings']
        assert metrics['total_s']>=metrics['first_text_s']
        assert metrics['typing_method']=='keyboard_type'
        assert states==["opening","queued","typing","submitting","waiting_for_reply"]
        page=factory.contexts[0].pages[0]
        assert page.typed=="Summarize this article"
        assert page.sent==1
        assert page.keyboard.pressed==["ControlOrMeta+A"]
        assert len(factory.arguments)==1 and factory.arguments[0]['headless'] is False
        assert str(factory.arguments[0]['user_data_dir']).endswith("session_data/gemini")
        assert manager.snapshot()['gemini']['status']=='ready_for_next_prompt'
        assert manager.snapshot()['chatgpt']['status']=='not_started'
        await manager.close()
    asyncio.run(run())

def test_gemini_failed_login_stores_private_screenshot(tmp_path):
    async def run():
        factory=Factory();manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        await manager.initialize_one("gemini")
        page=factory.contexts[0].pages[0]
        page.url='https://accounts.google.com/signin'
        with pytest.raises(SessionError,match='screenshot'):
            await manager.send_prompt_robust("gemini","Hello")
        assert page.shots
        assert manager.snapshot()['gemini']['status']=='needs_operator_login_or_review'
        await manager.close()
    asyncio.run(run())

def test_task_dispatch_automatically_delivers_real_gemini_label(monkeypatch):
    import time
    from app.api import server
    events=[]
    async def fake(prompt,platform=None,phase=None):
        raise AssertionError("wrong signature")
    async def answer(platform,prompt,*,phase=None):
        assert platform=='gemini'
        for part in ('typing','submitting','waiting_for_reply'):
            phase(part)
            await asyncio.sleep(.003)
        return {'answer':'Gemini synthetic answer','source':'gemini_visible_browser','automatic_output':True,'timings':{'total_s':3.2,'first_text_s':0.4,'typing_s':0.05,'stream_completion_s':2.7},'media':[{'kind':'image','url':'/artifacts/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png','bytes':1200}]}
    monkeypatch.setattr(server.router.sessions,'send_prompt_robust',answer)
    headers={'X-Exodia-Client':'exodia-dashboard'}
    with TestClient(server.app) as client:
        resp=client.post('/api/command/tasks',headers=headers,json={
           'agent_id':'nova','model_choice':'gemini','prompt':'Draft a title'})
        assert resp.status_code==201,resp.text
        task=resp.json()
        assert task['state']=='opening'
        for _ in range(80):
            row=next(x for x in client.get('/api/command/tasks').json()['tasks'] if x['id']==task['id'])
            if row['state']=='answered':break
            time.sleep(.02)
        assert row['state']=='answered',row
        assert row['answer']=='Gemini synthetic answer'
        assert row['media'][0]['kind']=='image'
        assert row['artifact']=='/artifacts/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png'
        assert row['metrics']['total_s']==3.2
        assert row['metrics']['first_text_s']==0.4
        assert row['provider']=='gemini'
        assert row['error']==''
        assert client.get('/api/command/tasks').json()['automatic_extraction']['gemini'] is True

def test_guest_gemini_editor_is_accepted_without_login(tmp_path):
    async def run():
        factory=Factory()
        manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        output=await manager.send_prompt_robust("gemini","Guest mode prompt")
        assert output["answer"]=="Streaming Gemini result [1]."
        assert manager.snapshot()["gemini"]["status"]=="ready_for_next_prompt"
        await manager.close()
    asyncio.run(run())


def test_guest_welcome_without_editor_reports_editor_unavailable(tmp_path,monkeypatch):
    async def run():
        factory=Factory()
        manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        await manager.initialize_one("gemini")
        page=factory.contexts[0].pages[0]
        async def not_visible(page):
            return None
        monkeypatch.setattr(manager,"_wait_for_gemini_editor",not_visible)
        with pytest.raises(SessionError,match="Guest text chat may work"):
            await manager.send_prompt_robust("gemini","Hello")
        assert manager.snapshot()["gemini"]["status"]=="editor_unavailable"
        assert page.shots
        assert manager.snapshot()["gemini"]["error"] is not None
        await manager.close()
    asyncio.run(run())

def test_large_prompt_uses_faster_input_event_instead_of_character_events(tmp_path):
    async def run():
        f=Factory();manager=MultiWebSessionManager(tmp_path,browser_factory=f)
        prompt='Research summary with details: ' + ('important evidence ' * 30)
        output=await manager.send_prompt_robust('gemini',prompt)
        p=f.contexts[0].pages[0]
        assert p.used_insert_text is True
        assert p.typed==prompt.strip()
        assert p.sent==1
        assert output['timings']['typing_method']=='insert_text'
        await manager.close()
    asyncio.run(run())

def test_actual_gemini_wrapper_handles_image_first_without_markdown(tmp_path):
    """The actual send_prompt_robust entrypoint must not require text output."""
    import base64
    class ImagePage(FakePage):
        def __init__(self):
            super().__init__();self.results=['Old answer'];self.media_reads=0
        async def evaluate(self,script,arg=None):
            if arg is not None:
                return {'base64':base64.b64encode(b'\x89PNG\r\n\x1a\nIMAGE').decode('ascii'),
                        'type':'image/png'}
            self.media_reads+=1
            return [{'kind':'image','src':'blob:gemini-image-123','width':512,'height':512}] if self.sent else []
    class ImageFactory(Factory):
        async def launch_persistent_context(self,**kwargs):
            self.arguments.append(kwargs)
            context=Context();context.pages=[ImagePage()]
            self.contexts.append(context)
            return context
    async def run():
        factory=ImageFactory()
        manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        result=await manager.send_prompt_robust('gemini','Generate an image of a red bicycle')
        assert result['answer']
        assert result['media'][0]['kind']=='image'
        assert result['media'][0]['url'].startswith('/artifacts/')
        assert (tmp_path/'app_data'/'artifacts').exists()
        assert result['timings']['total_s']>=1.5
        await manager.close()
    asyncio.run(run())

def test_two_simultaneous_gemini_jobs_use_separate_tabs_and_close(tmp_path):
    class DisposablePage(FakePage):
        def __init__(self):
            super().__init__()
            self.closed=False
        async def close(self):self.closed=True
    class TabContext(Context):
        def __init__(self):
            super().__init__()
            self.jobs=[]
        async def new_page(self):
            page=DisposablePage()
            self.jobs.append(page)
            return page
    class TabFactory(Factory):
        async def launch_persistent_context(self,**kwargs):
            self.arguments.append(kwargs)
            context=TabContext()
            self.contexts.append(context)
            return context
    async def run():
        factory=TabFactory()
        manager=MultiWebSessionManager(tmp_path,browser_factory=factory)
        outputs=await asyncio.gather(
            manager.send_prompt_robust('gemini','Question A'),
            manager.send_prompt_robust('gemini','Question B'),
        )
        ctx=factory.contexts[0]
        assert len(ctx.jobs)==2
        assert [page.typed for page in ctx.jobs]==['Question A','Question B']
        assert all(page.sent==1 and page.closed for page in ctx.jobs)
        assert all(result['answer']=='Streaming Gemini result [1].' for result in outputs)
        assert manager.snapshot()['gemini']['running_tasks']==0
        assert ctx.closed is False
        await manager.close()
    asyncio.run(run())
