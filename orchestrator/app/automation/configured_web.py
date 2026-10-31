"""Configurable persistent Playwright adapter for sites that allow browser automation.

No built-in ChatGPT/Gemini/DeepSeek scraping: operator supplies site-specific
configuration in ignored session_data/custom_web.json. Never bypass access checks.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.automation.interactive_dom import DOMResponseError, StreamWatchConfig, watch_response_stream


class WebAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class SiteProfile:
    url: str
    input_selector: str
    submit_selector: str
    response_selector: str
    stop_selector: str | None
    input_mode: str
    headless: bool

    @classmethod
    def from_json(cls, source):
        if source.get("operator_authorized") is not True:
            raise WebAdapterError("Set operator_authorized=true only for a site you may automate.")
        url=source.get("url","")
        parsed=urlparse(url)
        if parsed.scheme=="http":
            if parsed.hostname not in ("127.0.0.1","localhost") or parsed.port != 8765:
                raise WebAdapterError("Nonlocal HTTP is not supported.")
        elif parsed.scheme!="https":
            raise WebAdapterError("Provide an HTTPS site, or the local Exodia demo URL.")
        if parsed.username or parsed.password or not parsed.hostname:
            raise WebAdapterError("Invalid browser site URL.")
        for key in ("input_selector","submit_selector","response_selector"):
            if not isinstance(source.get(key),str) or not source[key].strip():
                raise WebAdapterError(f"Missing {key} in site profile.")
        mode=source.get("input_mode","contenteditable")
        if mode not in ("contenteditable","textarea"):
            raise WebAdapterError("input_mode must be contenteditable or textarea.")
        return cls(url=url,input_selector=source["input_selector"],
                   submit_selector=source["submit_selector"],response_selector=source["response_selector"],
                   stop_selector=source.get("stop_selector") or None,
                   input_mode=mode,headless=bool(source.get("headless",False)))


class ConfiguredWebRunner:
    def __init__(self, root, *, browser_factory=None):
        self.root=Path(root).resolve()
        self.config_path=self.root/"session_data"/"custom_web.json"
        self.profile_dir=self.root/"session_data"/"custom_web_profile"
        self.debug_dir=self.root/"debug_snapshots"
        self._browser_factory=browser_factory
        self._playwright=None
        self._context=None
        self._page=None
        self._lock=asyncio.Lock()
        self.status="not_configured"
        self.last_error=None

    def profile(self):
        if not self.config_path.exists():
            raise WebAdapterError("Custom site not configured. Copy examples/custom_web.example.json to session_data/custom_web.json.")
        try:
            data=json.loads(self.config_path.read_text(encoding="utf-8"))
        except (ValueError,OSError) as exc:
            raise WebAdapterError("Custom site configuration isn't valid JSON.") from exc
        return SiteProfile.from_json(data)

    def snapshot(self):
        try:
            spec=self.profile()
            return {"configured":True,"status":self.status,"site":urlparse(spec.url).hostname,
                    "mode":"configured_browser","last_error":self.last_error}
        except WebAdapterError as exc:
            return {"configured":False,"status":"not_configured","last_error":str(exc)}

    def _assert_page(self, page, profile):
        expected=urlparse(profile.url)
        current=urlparse(page.url)
        if (expected.scheme,expected.hostname,expected.port)!=(current.scheme,current.hostname,current.port):
            raise WebAdapterError("Browser navigated outside configured site. Review login manually.")

    async def _page_for(self, profile):
        if self._page is not None:
            self._assert_page(self._page,profile)
            return self._page
        if self._browser_factory is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright=await async_playwright().start()
                self._browser_factory=self._playwright.chromium
            except Exception as exc:
                raise WebAdapterError("Playwright not available; install browser dependencies.") from exc
        self.profile_dir.mkdir(parents=True,exist_ok=True)
        self._context=await self._browser_factory.launch_persistent_context(
            user_data_dir=str(self.profile_dir),headless=profile.headless,
            accept_downloads=False)
        self._page=self._context.pages[0] if self._context.pages else await self._context.new_page()
        await self._page.goto(profile.url,wait_until="domcontentloaded",timeout=30000)
        self._assert_page(self._page,profile)
        return self._page

    async def _screenshot(self, page):
        self.debug_dir.mkdir(parents=True,exist_ok=True)
        from datetime import datetime, timezone
        filename="authorized-web-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")+".png"
        try:
            await page.screenshot(path=str(self.debug_dir/filename),full_page=False,timeout=5000)
            return filename
        except Exception:
            return "unavailable"

    async def run(self,prompt,*,phase=None):
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:
            raise WebAdapterError("Prompt must have 1-12000 characters.")
        profile=self.profile()
        async with self._lock:
            page=None
            try:
                self.status="opening"
                if phase: phase("opening")
                page=await self._page_for(profile)
                self._assert_page(page,profile)
                responses=page.locator(profile.response_selector)
                before=await responses.count()
                old=(await responses.last.inner_text()).strip() if before else ""
                self.status="typing"
                if phase: phase("typing")
                target=page.locator(profile.input_selector).first
                await target.click(timeout=15000)
                if profile.input_mode=="textarea":
                    await target.fill(prompt.strip(),timeout=15000)
                else:
                    await page.keyboard.press("ControlOrMeta+A")
                    await page.keyboard.type(prompt.strip(),delay=10)
                self.status="submitting"
                if phase: phase("submitting")
                await page.locator(profile.submit_selector).first.click(timeout=15000)
                self.status="waiting_for_reply"
                if phase: phase("waiting_for_reply")
                final=await watch_response_stream(
                    page,StreamWatchConfig(response_selector=profile.response_selector,
                        stop_selector=profile.stop_selector,timeout_seconds=180,stable_seconds=1.5,
                        poll_seconds=.3),initial_count=before,initial_text=old)
                self.status="ready"
                self.last_error=None
                return {"answer":final,"provider":"custom_web","source":"configured_browser",
                        "url":profile.url,"mode":"automatic"}
            except (Exception,DOMResponseError) as exc:
                self.status="error"
                shot=await self._screenshot(page) if page else "unavailable"
                self.last_error=f"{type(exc).__name__}; screenshot: {shot}"
                if isinstance(exc,WebAdapterError):
                    raise
                raise WebAdapterError(f"Configured web task failed: {type(exc).__name__}. Diagnostic screenshot: {shot}.") from exc

    async def close(self):
        if self._context is not None:
            try: await self._context.close()
            finally:self._context=None;self._page=None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright=None
            self._browser_factory=None
