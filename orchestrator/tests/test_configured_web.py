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
    class Broken(Factory):
        async def launch_persistent_context(self,**kwargs):
            c=Context();c.pages[0].url="https://unapproved.test/";return c
    async def run():
        runner=ConfiguredWebRunner(tmp_path,browser_factory=Broken())
        with pytest.raises(WebAdapterError):
            await runner.run("test")
        assert runner.status=="error"
        await runner.close()
    asyncio.run(run())
