"""Browser automation handoff tests with simulated DOM, no external accounts."""
import asyncio
import json
import pytest
from app.automation.configured_web import ConfiguredWebRunner, SiteProfile, WebAdapterError

class Input:
    def __init__(self,page):self.page=page;self.first=self
    async def click(self,timeout=15000):self.page.did_click=True
    async def fill(self,prompt,timeout=15000):self.page.sent=prompt
class Result:
    def __init__(self,page):self.page=page
    @property
    def last(self):return self
    async def count(self):return len(self.page.results)
    async def inner_text(self,timeout=5000):
        return self.page.results[-1] if self.page.results else ""
class Button:
    def __init__(self,page):self.page=page;self.first=self
    async def click(self,timeout=15000):
        self.page.submitted=True
        self.page.results.append("Model answer")
class Stop:
    async def is_visible(self):return False
class Keyboard:
    def __init__(self,page):self.page=page
    async def press(self,key):self.page.selected=(key=="ControlOrMeta+A")
    async def type(self,text,delay=10):self.page.sent=text
class Page:
    def __init__(self):
        self.url="http://127.0.0.1:8765/automation-demo"
        self.results=["Earlier unrelated answer"]
        self.did_click=False;self.selected=False;self.submitted=False;self.sent=""
        self.keyboard=Keyboard(self)
    def locator(self,selector):
        if selector=="#prompt":return Input(self)
        if selector=="#send":return Button(self)
        if selector==".reply":return Result(self)
        if selector=="#stop":return Stop()
        raise AssertionError(selector)
    async def goto(self,url,**kwargs):self.url=url
    async def screenshot(self,**kwargs):pass
class Context:
    def __init__(self):self.pages=[Page()]
    async def close(self):pass
class Factory:
    def __init__(self):self.launches=[]
    async def launch_persistent_context(self,**kwargs):
        self.launches.append(kwargs);return Context()

def configured(tmp_path):
    path=tmp_path/"session_data";path.mkdir()
    (path/"custom_web.json").write_text(json.dumps({
        "operator_authorized":True,"url":"http://127.0.0.1:8765/automation-demo",
        "input_selector":"#prompt","submit_selector":"#send",
        "response_selector":".reply","stop_selector":"#stop",
        "input_mode":"contenteditable","headless":False}))
    return path

def test_local_config_requires_authorization():
    with pytest.raises(WebAdapterError):
        SiteProfile.from_json({"url":"http://127.0.0.1:8765/automation-demo"})
    with pytest.raises(WebAdapterError):
        SiteProfile.from_json({"operator_authorized":True,"url":"http://127.0.0.1:9000/"})

def test_full_automated_cycle_works_with_mock_page(tmp_path):
    configured(tmp_path)
    async def run():
        factory=Factory()
        runner=ConfiguredWebRunner(tmp_path,browser_factory=factory)
        phases=[]
        result=await runner.run("Compose a headline",phase=phases.append)
        assert result["answer"]=="Model answer"
        assert result["source"]=="configured_browser"
        assert phases==["opening","typing","submitting","waiting_for_reply"]
        page=runner._page
        assert page.sent=="Compose a headline"
        assert page.submitted and page.selected
        assert factory.launches[0]["headless"] is False
        await runner.close()
    asyncio.run(run())

def test_screenshot_on_failure(tmp_path):
    configured(tmp_path)
    class RedirectedPage(Page):
        async def goto(self,url,**kwargs):
            self.url="https://unapproved.test/"
    class Broken(Factory):
        async def launch_persistent_context(self,**kwargs):
            c=Context();c.pages=[RedirectedPage()];return c
    async def run():
        runner=ConfiguredWebRunner(tmp_path,browser_factory=Broken())
        with pytest.raises(WebAdapterError):
            await runner.run("test")
        assert runner.status=="error"
        await runner.close()
    asyncio.run(run())


def test_custom_web_task_automatically_delivers_to_companion(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app.api import server
    import time
    configured(tmp_path)
    # Real HTTP + persistence + UI state; browser result simulated in the test.
    monkeypatch.setattr(server.web_adapter,"snapshot",lambda:{
       "configured":True,"status":"ready","site":"127.0.0.1"})
    async def simulated_run(prompt,*,phase):
        for p in ["typing","submitting","waiting_for_reply"]:
            phase(p)
            await asyncio.sleep(.004)
        return {"answer":"Browser result, ready for Nova","provider":"custom_web",
                "source":"configured_browser"}
    monkeypatch.setattr(server.web_adapter,"run",simulated_run)
    headers={"x-exodia-client":"exodia-dashboard"}
    with TestClient(server.app) as client:
        response=client.post("/api/command/tasks",headers=headers,json={
            "prompt":"Review this plan","agent_id":"nova","model_choice":"custom_web"})
        assert response.status_code==201,response.text
        task_id=response.json()["id"]
        for _ in range(50):
            result=next(t for t in client.get("/api/command/tasks").json()["tasks"] if t["id"]==task_id)
            if result["state"]=="answered":break
            time.sleep(.02)
        assert result["state"]=="answered"
        assert result["provider"]=="custom_web"
        assert result["answer"]=="Browser result, ready for Nova"
        assert result["error"]==""
        assert client.get("/automation-demo").status_code==200


def test_custom_web_requires_configured_site(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api import server
    monkeypatch.setattr(server.web_adapter,"snapshot",lambda:{
        "configured":False,"last_error":"No configuration"})
    with TestClient(server.app) as client:
        resp=client.post("/api/command/tasks",
            headers={"x-exodia-client":"exodia-dashboard"},
            json={"prompt":"Try","agent_id":"kiko","model_choice":"custom_web"})
        assert resp.status_code==422
