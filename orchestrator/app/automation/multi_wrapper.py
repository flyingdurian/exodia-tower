"""Persistent operator-assisted web workspaces, no evasion or output scraping."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

@dataclass(frozen=True)
class ProviderSpec:
    url: str
    input_selector: str
    submit_selector: str
    response_selector: str

PROVIDERS = {
    "chatgpt": ProviderSpec("https://chatgpt.com","div#prompt-textarea","button[data-testid='send-button']","div.markdown"),
    "gemini": ProviderSpec("https://gemini.google.com","rich-textarea p","button.send-button","message-content"),
    "deepseek": ProviderSpec("https://chat.deepseek.com","textarea#chat-input","div.chat-submit-button","div.ds-markdown"),
}

class SessionError(RuntimeError): pass
class OperatorActionRequired(SessionError): pass

class MultiWebSessionManager:
    """Three persistent, isolated Chromium profiles; manually supervised prompt transfer."""
    def __init__(self, root: Path, *, headless=False, browser_factory=None):
        self.root=Path(root).resolve()
        self.profile_dir=self.root/"session_data"
        self.debug_dir=self.root/"debug_snapshots"
        self.headless=headless
        self._browser_factory=browser_factory
        self._playwright=None
        self._contexts={}
        self._pages={}
        self._locks={name:asyncio.Lock() for name in PROVIDERS}
        self._status={name:"not_started" for name in PROVIDERS}
        self._pending={}
        self._initialization_lock=asyncio.Lock()

    def snapshot(self):
        return {name:{"status":self._status[name], "url":spec.url,
                      "profile":f"session_data/{name}", "pending_prompt":name in self._pending,
                      "mode":"operator_assisted"} for name,spec in PROVIDERS.items()}

    async def initialize_all(self):
        async with self._initialization_lock:
            self.profile_dir.mkdir(parents=True,exist_ok=True)
            if self._browser_factory is None and self._playwright is None:
                try:
                    from playwright.async_api import async_playwright
                    self._playwright=await async_playwright().start()
                    self._browser_factory=self._playwright.chromium
                except Exception as exc:
                    raise SessionError("Playwright Chromium unavailable. Run: playwright install chromium") from exc
            results=await asyncio.gather(*(self._launch(name) for name in PROVIDERS),return_exceptions=True)
            for name,result in zip(PROVIDERS,results):
                if isinstance(result,BaseException): self._status[name]="error"
            return self.snapshot()

    async def _launch(self,name):
        if name in self._contexts: return
        spec=PROVIDERS[name]
        profile=self.profile_dir/name
        profile.mkdir(parents=True,exist_ok=True)
        context=None
        self._status[name]="launching"
        try:
            context=await self._browser_factory.launch_persistent_context(
                user_data_dir=str(profile),headless=self.headless,accept_downloads=False)
            page=context.pages[0] if context.pages else await context.new_page()
            await page.goto(spec.url,wait_until="domcontentloaded",timeout=30000)
            # Login redirects can leave the site domain; permit visible manual login.
            # Prompt preparation checks the canonical provider origin later.
            self._contexts[name]=context
            self._pages[name]=page
            self._status[name]="needs_operator_login_or_review"
        except Exception as exc:
            self._status[name]="error"
            if context is not None:
                try: await context.close()
                except Exception: pass
            raise SessionError(f"{name} browser session could not start ({type(exc).__name__}).") from exc

    @staticmethod
    def _check_destination(name,url):
        parsed=urlparse(url)
        allowed=urlparse(PROVIDERS[name].url).hostname
        host=(parsed.hostname or "").lower()
        if parsed.scheme!="https" or not host or not (host==allowed or host.endswith("."+allowed)):
            raise SessionError(f"{name} redirected to an unapproved domain; manual review required.")

    async def prepare_prompt(self,name,prompt):
        if name not in PROVIDERS: raise ValueError("Choose chatgpt, gemini, or deepseek")
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:
            raise ValueError("Prompt must contain 1–12000 characters.")
        async with self._locks[name]:
            if name in self._pending:
                raise OperatorActionRequired(f"{name} already has a pending browser reply; record it first.")
            page=self._pages.get(name)
            if page is None:
                raise OperatorActionRequired(f"{name} session not started; start sessions and log in first.")
            try:
                self._check_destination(name,page.url)
                await page.locator(PROVIDERS[name].input_selector).first.fill(prompt.strip(),timeout=10000)
                self._status[name]="awaiting_operator_send_and_copy"
                self._pending[name]={"prompt":prompt.strip(),"prepared_at":datetime.now(timezone.utc).isoformat()}
                return {"model_choice":name,"status":"awaiting_operator",
                        "action":"Review and send in the visible browser, then paste the response into Exodia Tower.",
                        "url":PROVIDERS[name].url,"automatic_output":False}
            except Exception as exc:
                screenshot=await self._capture_failure(name,page)
                self._status[name]="dom_error_manual_review"
                raise SessionError(f"{name} input unavailable; inspect browser/login and local screenshot {screenshot}.") from exc

    async def _capture_failure(self,name,page):
        self.debug_dir.mkdir(parents=True,exist_ok=True)
        timestamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        filename=f"dom-error-{timestamp}-{name}.png"
        try:
            await page.screenshot(path=str(self.debug_dir/filename),full_page=False,timeout=5000)
            return filename
        except Exception: return "unavailable"

    def receive_operator_response(self,name,response):
        if name not in PROVIDERS: raise ValueError("Unknown model")
        if name not in self._pending:
            raise OperatorActionRequired("Prepare a prompt before recording a response.")
        if not isinstance(response,str) or not response.strip() or len(response)>100000:
            raise ValueError("Manual response must contain 1–100000 characters.")
        del self._pending[name]
        self._status[name]="ready_for_next_prompt"
        return {"model_choice":name,"status":"operator_supplied",
                "answer":response.strip(),"source":"manual_copy","verified":False}

    async def close(self):
        for name,context in list(self._contexts.items()):
            try: await context.close()
            finally: self._status[name]="closed"
        self._contexts.clear();self._pages.clear();self._pending.clear()
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright=None
            self._browser_factory=None
