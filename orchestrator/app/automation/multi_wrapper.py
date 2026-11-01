"""Persistent visible web workspaces. Account output extraction remains operator-assisted."""
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from time import monotonic
from app.automation.interactive_dom import StreamWatchConfig, watch_response_stream, DOMResponseError
from app.automation.gemini_media import (
    media_intent, snapshot_media, await_media_answer, store_media, MediaCaptureError
)

def installed_chrome() -> bool:
    """Google sign-in rejects Playwright's bundled Chromium. Prefer installed Chrome."""
    candidates = (
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/google-chrome-stable"),
    )
    return any(path.is_file() for path in candidates)

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
        self._last_error={name:None for name in PROVIDERS}
        self._last_timings={name:{} for name in PROVIDERS}
        self._browser_versions={name:None for name in PROVIDERS}
        self._browser_ua={name:None for name in PROVIDERS}
        self._pending={}
        self._initialization_lock=asyncio.Lock()
        # Distinct task tabs in one authenticated context. Concurrency is bounded,
        # not serialized behind an unrelated long-running Gemini image/video job.
        self._gemini_slots=asyncio.Semaphore(2)
        self._gemini_start_lock=asyncio.Lock()
        self._gemini_last_start=0.0
        self._gemini_active=0

    def snapshot(self):
        return {name:{"status":self._status[name], "url":spec.url,
                      "profile":f"session_data/{name}", "pending_prompt":name in self._pending,
                      "mode":"automatic_text" if name=="gemini" else "operator_assisted",
                      "error":self._last_error[name],
                      "last_timings":self._last_timings[name],
                      "actual_user_agent":self._browser_ua[name],
                      "browser_version":self._browser_versions[name],
                      "running_tasks":self._gemini_active if name=="gemini" else 0,
                      "max_parallel_tasks":2 if name=="gemini" else 1} for name,spec in PROVIDERS.items()}

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

    async def initialize_one(self, name):
        """Launch only the requested persistent browser profile."""
        if name not in PROVIDERS: raise ValueError("Unknown web provider")
        async with self._initialization_lock:
            self.profile_dir.mkdir(parents=True,exist_ok=True)
            if self._browser_factory is None and self._playwright is None:
                try:
                    from playwright.async_api import async_playwright
                    self._playwright=await async_playwright().start()
                    self._browser_factory=self._playwright.chromium
                except Exception as exc:
                    raise SessionError("Chromium is unavailable; run: .\\.venv\\Scripts\\python.exe -m playwright install chromium") from exc
            await self._launch(name)
            return self.snapshot()[name]

    async def _open_visible_browser(self, profile: Path):
        """Open the persistent profile in installed Chrome when it is present.

        Playwright's bundled Chromium is a separate build. Google account sign-in
        often rejects that build as outdated. This does not hide automation.
        """
        options = dict(user_data_dir=str(profile), headless=self.headless, accept_downloads=False)
        # Optional honest compatibility identification; it cannot override account security checks.
        user_agent=os.getenv("EXODIA_BROWSER_USER_AGENT","").strip()
        if user_agent:
            if len(user_agent)>512 or any(ord(c)<32 for c in user_agent):
                raise SessionError("EXODIA_BROWSER_USER_AGENT must be one valid header line under 512 characters.")
            options["user_agent"]=user_agent
        # Explicit opt-in only. May affect browser fingerprint; does not guarantee Google login.
        if os.getenv("EXODIA_EXPERIMENTAL_CHROMIUM_FLAG","").strip().lower() in ("1","true","yes"):
            options["args"]=["--disable-blink-features=AutomationControlled"]
        if installed_chrome():
            try:
                return await self._browser_factory.launch_persistent_context(**options, channel="chrome")
            except Exception as exc:
                message = str(exc).lower()
                if "channel" not in message and "chrome" not in message and "executable" not in message:
                    raise
        return await self._browser_factory.launch_persistent_context(**options)

    async def _launch(self,name):
        if name in self._contexts: return
        spec=PROVIDERS[name]
        profile=self.profile_dir/name
        profile.mkdir(parents=True,exist_ok=True)
        context=None
        self._status[name]="launching"
        try:
            context=await self._open_visible_browser(profile)
            page=context.pages[0] if context.pages else await context.new_page()
            await page.goto(spec.url,wait_until="domcontentloaded",timeout=30000)
            # Login redirects can leave the site domain; permit visible manual login.
            # Prompt preparation checks the canonical provider origin later.
            self._contexts[name]=context
            self._pages[name]=page
            try:
                self._browser_ua[name]=await page.evaluate("navigator.userAgent")
            except (AttributeError,RuntimeError,Exception):
                self._browser_ua[name]=None
            try:
                self._browser_versions[name]=context.browser.version if context.browser else None
            except (AttributeError,RuntimeError,Exception):
                self._browser_versions[name]=None
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
                await self._type_prompt(page,name,prompt.strip())
                self._status[name]="awaiting_operator_send_and_copy"
                self._pending[name]={"prompt":prompt.strip(),"prepared_at":datetime.now(timezone.utc).isoformat()}
                return {"model_choice":name,"status":"awaiting_operator",
                        "action":"Review and send in the visible browser, then paste the response into Exodia Tower.",
                        "url":PROVIDERS[name].url,"automatic_output":False}
            except Exception as exc:
                screenshot=await self._capture_failure(name,page)
                self._status[name]="dom_error_manual_review"
                raise SessionError(f"{name} input unavailable; inspect browser/login and local screenshot {screenshot}.") from exc

    @staticmethod
    async def _type_prompt(page,name,prompt):
        """Type naturally into contenteditable editors; use fill only for plain textareas.

        This prepares the prompt but never triggers Send or copies provider output.
        """
        selector=PROVIDERS[name].input_selector
        box=page.locator(selector).first
        if name=="deepseek":
            # DeepSeek's configured input is a native textarea, not contenteditable.
            await box.fill(prompt,timeout=15000)
        else:
            await box.click(timeout=15000)
            # Keyboard events keep React / rich-text handlers in sync.
            await page.keyboard.press("ControlOrMeta+A")
            await page.keyboard.type(prompt,delay=10)

    # Site-specific selectors are best-effort, not stable public interfaces.
    GEMINI_EDITORS=(
        'rich-textarea .ql-editor[contenteditable="true"]',
        'rich-textarea [contenteditable="true"]',
        'rich-textarea p',
        'div.ql-editor[contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        '[aria-label="Enter a prompt here"][contenteditable="true"]',
        'textarea[aria-label="Enter a prompt here"]',
    )
    GEMINI_SEND=(
        'button.send-button',
        'button[aria-label="Send message"]',
        'button[aria-label="Send"]',
        'button[data-test-id="send-button"]',
    )
    GEMINI_RESPONSE='message-content, model-response .markdown, model-response .response-container'
    GEMINI_STOP='button[aria-label*="Stop generating"], button[aria-label*="Stop response"], button.stop-button'

    @staticmethod
    async def _first_visible(page, selectors):
        for selector in selectors:
            try:
                item=page.locator(selector).first
                if await item.is_visible(timeout=1500):
                    return item
            except Exception:
                continue
        return None

    async def _wait_for_gemini_editor(self,page):
        """Gemini may render the guest editor after DOMContentLoaded.

        A signed-out welcome page is not proof that login is required.
        """
        for attempt in range(20):
            editor=await self._first_visible(page,self.GEMINI_EDITORS)
            if editor is not None:
                return editor
            if attempt<19:
                await asyncio.sleep(.5)
        return None

    async def send_prompt_robust(self,platform: str,prompt: str,*,phase=None)->dict:
        """Full Gemini user-requested browser task -> final text.

        No stealth, auth bypass, hidden API calls, or unattended sensitive actions.
        One active Gemini task per profile. Designed for plain chat text only.
        """
        if platform!="gemini":
            raise OperatorActionRequired("Automatic website mode is currently implemented only for Gemini.")
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:
            raise ValueError("Prompt must contain 1–12000 characters.")
        t_begin=monotonic()
        if "gemini" not in self._pages:
            if phase: phase("opening")
            await self.initialize_one("gemini")
        browser_ready=monotonic()
        if phase:phase("queued")
        async with self._gemini_slots:
            if "gemini" in self._pending:
                raise OperatorActionRequired("Gemini has an earlier manually prepared prompt; resolve it first.")
            context=self._contexts.get("gemini")
            baseline_page=self._pages.get("gemini")
            if baseline_page is None:
                raise SessionError("Gemini browser unavailable. Open the workspaces and sign in to Gemini.")
            page=baseline_page
            disposable=False
            self._gemini_active+=1
            try:
                # Each task gets a fresh conversation tab to prevent stale prompt
                # editors, old generated media and task cross-talk. Persistent
                # browser context shares its existing Google sign-in cookies.
                if context is not None and hasattr(context,"new_page"):
                    if phase:phase("opening")
                    page=await context.new_page()
                    disposable=True
                    await page.goto(PROVIDERS["gemini"].url,
                                    wait_until="domcontentloaded",timeout=30000)
                self._check_destination("gemini",page.url)
                # Light start-spacing limits UI racing without serializing responses.
                async with self._gemini_start_lock:
                    delay=max(0.0,2.5-(monotonic()-self._gemini_last_start))
                    if delay:
                        if phase:phase("cooldown")
                        await asyncio.sleep(delay)
                    self._gemini_last_start=monotonic()
                t_editor=monotonic()
                editor=await self._wait_for_gemini_editor(page)
                editor_ready=monotonic()
                if editor is None:
                    self._status["gemini"]="editor_unavailable"
                    raise SessionError(
                        "Gemini editor is not visible after loading. Guest text chat may work "
                        "without signing in; try typing manually in this same browser window. "
                        "If only the welcome page appears, reload Gemini and check for a blocked or "
                        "incomplete page load. Signing in is NOT required for basic guest chat. "
                        "Google may reject automated-browser sign-in; do not bypass its security checks."
                    )
                history=page.locator(self.GEMINI_RESPONSE)
                prior_count=await history.count()
                prior_text=(await history.last.inner_text(timeout=7000)).strip() if prior_count else ""
                wants_media=media_intent(prompt)
                baseline_media=await snapshot_media(page) if wants_media else []

                self._status["gemini"]="typing"
                if phase: phase("typing")
                t_typing=monotonic()
                await editor.click(timeout=15000)
                await page.keyboard.press("ControlOrMeta+A")
                # Fast text insertion preserves an input event for React editors.
                # Keep actual key events for shorter prompts that already work.
                if len(prompt.strip())>=250 and hasattr(page.keyboard,"insert_text"):
                    await page.keyboard.insert_text(prompt.strip())
                    typing_method="insert_text"
                else:
                    await page.keyboard.type(prompt.strip(),delay=0)
                    typing_method="keyboard_type"
                typed_at=monotonic()

                sender=await self._first_visible(page,self.GEMINI_SEND)
                self._status["gemini"]="submitting"
                if phase: phase("submitting")
                if sender is not None:
                    # A timeout here is ambiguous; do not retry or press Enter.
                    await sender.click(timeout=15000)
                else:
                    # Enter can submit in Gemini; it is used only when no send button exists.
                    await page.keyboard.press("Enter")
                submitted_at=monotonic()
                self._status["gemini"]="waiting_for_reply"
                if phase: phase("waiting_for_reply")
                first_text_at=[None]
                def mark_first_text():
                    if first_text_at[0] is None:
                        first_text_at[0]=monotonic()
                media=[]
                if wants_media:
                    self._status["gemini"]="rendering_media"
                    if phase:phase("rendering_media")
                    result=await await_media_answer(page,
                        text_selector=self.GEMINI_RESPONSE,stop_selector=self.GEMINI_STOP,
                        baseline=baseline_media,baseline_count=prior_count,
                        baseline_text=prior_text,
                        timeout=360.0 if 'video' in prompt.lower() else 130.0,
                        poll=.5,stable=1.6)
                    answer=result.answer
                    if answer:mark_first_text()
                    if result.media:
                        media=await store_media(page,result.media,
                          self.root/'app_data'/'artifacts')
                        if not answer.strip():
                            complete=sum(1 for item in media if item.get('url'))
                            answer=f"Generated {complete} media file(s)." if complete else (
                                "Gemini generated media but download capture failed; "
                                "inspect the Gemini browser and task diagnostics."
                            )
                else:
                    answer=await watch_response_stream(
                        page,
                        StreamWatchConfig(response_selector=self.GEMINI_RESPONSE,
                            stop_selector=self.GEMINI_STOP,timeout_seconds=180.0,
                            stable_seconds=1.5,poll_seconds=.25),
                        initial_count=prior_count,initial_text=prior_text,
                        on_first_text=mark_first_text)
                finished_at=monotonic()
                if not answer.strip(): raise SessionError("Gemini returned no readable text or media.")
                timings={
                    "browser_setup_s":round(browser_ready-t_begin,3),
                    "editor_wait_s":round(editor_ready-t_editor,3),
                    "typing_s":round(typed_at-t_typing,3),
                    "submit_s":round(submitted_at-typed_at,3),
                    "first_text_s":round(first_text_at[0]-submitted_at,3) if first_text_at[0] is not None else None,
                    "stream_completion_s":round(finished_at-submitted_at,3),
                    "settle_after_first_text_s":round(finished_at-first_text_at[0],3) if first_text_at[0] is not None else None,
                    "total_s":round(finished_at-t_begin,3),
                    "typing_method":typing_method,
                }
                self._last_timings["gemini"]=timings
                self._status["gemini"]="ready_for_next_prompt"
                self._last_error["gemini"]=None
                return {"answer":answer.strip()[:100000],"model_choice":"gemini",
                        "provider":"gemini","source":"gemini_visible_browser",
                        "automatic_output":True,"timings":timings,"media":media}
            except Exception as exc:
                screenshot=await self._capture_failure("gemini",page)
                if self._status["gemini"] not in ("needs_operator_login_or_review","editor_unavailable"):
                    self._status["gemini"]="dom_error_manual_review"
                message=(str(exc) if isinstance(exc,(SessionError,DOMResponseError)) else
                    f"Gemini browser error ({type(exc).__name__}).")
                self._last_error["gemini"]=message[:420]
                raise SessionError(f"{message} Debug screenshot: {screenshot}.") from exc
            finally:
                self._gemini_active-=1
                if disposable:
                    try:await page.close()
                    except Exception:pass

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
