"""Response observer tests against a simulated permitted web UI."""
import asyncio
import pytest
from app.automation.interactive_dom import StreamWatchConfig, watch_response_stream, DOMResponseError


class ResultLocator:
    def __init__(self,page):self.page=page
    async def count(self):return 1
    @property
    def last(self):return self
    async def inner_text(self,timeout=5000):
        return self.page.next_text()
    async def is_visible(self):return self.page.generating


class FakePage:
    def __init__(self,texts,generating=False):self.texts=list(texts);self.generating=generating
    def next_text(self):
        if len(self.texts)>1:return self.texts.pop(0)
        return self.texts[0] if self.texts else ""
    def locator(self,selector):return ResultLocator(self)


def test_watcher_waits_for_new_stable_answer():
    async def run():
        page=FakePage(["old","new part","new completed","new completed","new completed"])
        r=await watch_response_stream(page,StreamWatchConfig('.answer',timeout_seconds=0.5,stable_seconds=.008,poll_seconds=.005),initial_count=1,initial_text="old")
        assert r=="new completed"
    asyncio.run(run())


def test_watcher_rejects_old_unchanged_output():
    async def run():
        page=FakePage(["old"])
        with pytest.raises(DOMResponseError):
            await watch_response_stream(page,StreamWatchConfig('.answer',timeout_seconds=.04,stable_seconds=.008,poll_seconds=.005),initial_count=1,initial_text="old")
    asyncio.run(run())


def test_watcher_requires_valid_configuration():
    async def run():
        with pytest.raises(ValueError):
            await watch_response_stream(FakePage([]),StreamWatchConfig('',timeout_seconds=1))
    asyncio.run(run())


def test_first_visible_callback_only_fires_for_new_text():
    async def run():
        page=FakePage(['old answer','old answer','fresh answer','fresh answer','fresh answer'])
        calls=[]
        result=await watch_response_stream(
            page,StreamWatchConfig('.answer',timeout_seconds=.4,stable_seconds=.01,poll_seconds=.005),
            initial_count=1,initial_text='old answer',on_first_text=lambda:calls.append('new'))
        assert result=='fresh answer'
        assert calls==['new']
    asyncio.run(run())
