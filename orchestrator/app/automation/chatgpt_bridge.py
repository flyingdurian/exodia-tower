"""Task-bound, user-initiated ChatGPT browser submission.

This component DOES NOT inspect, scrape, store, or programmatically extract
ChatGPT outputs. It prepares/sends a prompt through the authenticated visible
ChatGPT UI, keeps the task tab open for user review, and accepts a separately
user-supplied answer through Exodia's existing task endpoint.

No authentication automation, hidden website API, session-token handling,
CAPTCHA interaction, stealth patching, or response watcher.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Any

from app.automation.multi_wrapper import (
    MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS,
)

EDITOR_SELECTORS=(
    '#prompt-textarea[contenteditable="true"]',
    'div#prompt-textarea',
    '[data-testid="composer-input"][contenteditable="true"]',
    '[role="textbox"][contenteditable="true"]',
    'textarea#prompt-textarea',
)
SEND_SELECTORS=(
    'button[data-testid="send-button"]',
    'button[data-testid="composer-send-button"]',
    'button[aria-label="Send message"]',
    'button[aria-label="Send prompt"]',
)

@dataclass
class BrowserJob:
    task_id:str
    page:Any
    created_at:float
    owns_tab:bool

class ChatGPTSubmissionBridge:
    """Maximum two pending task tabs, serialized starts, manual result delivery."""

    def __init__(self,sessions:MultiWebSessionManager,*,max_tabs:int=2,start_spacing:float=1.0):
        if max_tabs<1 or start_spacing<0:raise ValueError('Invalid ChatGPT limits')
        self.sessions=sessions
        self.max_tabs=max_tabs
        self.start_spacing=start_spacing
        self.tasks:dict[str,BrowserJob]={}
        self.start_lock=asyncio.Lock()
        self.last_start=0.0
        self.last_error=None

    def snapshot(self):
        return {'mode':'automatic_submit_manual_result',
                'automatic_output_extraction':False,
                'pending_tasks':list(self.tasks),
                'pending_count':len(self.tasks),
                'max_pending_tabs':self.max_tabs,
                'last_error':self.last_error}

    async def _visible(self,page,selectors,timeout:float=10.0):
        deadline=monotonic()+timeout
        while monotonic()<deadline:
            for selector in selectors:
                try:
                    candidate=page.locator(selector).first
                    if await candidate.is_visible(timeout=650):
                        return candidate
                except Exception:
                    pass
            await asyncio.sleep(.15)
        return None

    async def submit(self,task_id:str,prompt:str,*,phase=None):
        if not task_id or len(task_id)>128:
            raise ValueError('Invalid task ID')
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:
            raise ValueError('Prompt must contain 1-12000 characters')
        if task_id in self.tasks:
            raise OperatorActionRequired('ChatGPT task already submitted; open its browser tab')
        if 'chatgpt' not in self.sessions._contexts:
            if phase:phase('opening')
            await self.sessions.initialize_one('chatgpt')
        context=self.sessions._contexts.get('chatgpt')
        if context is None:
            raise SessionError('ChatGPT browser context is unavailable')
        async with self.start_lock:
            if len(self.tasks)>=self.max_tabs:
                raise OperatorActionRequired(
                    f'ChatGPT has {len(self.tasks)} pending review tab(s). '
                    'Record or cancel one before starting another.')
            if task_id in self.tasks:
                raise OperatorActionRequired('ChatGPT task already submitted')
            if phase:phase('queued')
            delay=max(0.0,self.start_spacing-(monotonic()-self.last_start))
            if delay:
                if phase:phase('cooldown')
                await asyncio.sleep(delay)
            self.last_start=monotonic()
            page=None
            owns_tab=False
            try:
                if phase:phase('opening')
                if hasattr(context,'new_page'):
                    page=await context.new_page()
                    owns_tab=True
                else:
                    # A compatibility path for older injected test browsers.
                    page=self.sessions._pages.get('chatgpt')
                if page is None:raise SessionError('No ChatGPT browser tab available')
                await page.goto(PROVIDERS['chatgpt'].url,
                                wait_until='domcontentloaded',timeout=30000)
                self.sessions._check_destination('chatgpt',page.url)
                editor=await self._visible(page,EDITOR_SELECTORS,timeout=12.0)
                if editor is None:
                    raise OperatorActionRequired(
                        'ChatGPT composer not found. Complete any sign-in or '
                        'on-screen browser review manually, then create a new task.')
                if phase:phase('typing')
                await editor.click(timeout=8000)
                await page.keyboard.press('ControlOrMeta+A')
                if hasattr(page.keyboard,'insert_text'):
                    await page.keyboard.insert_text(prompt.strip())
                    typing='insert_text'
                else:
                    await page.keyboard.type(prompt.strip(),delay=0)
                    typing='keyboard_type'
                send=await self._visible(page,SEND_SELECTORS,timeout=5.0)
                if send is None:
                    raise OperatorActionRequired(
                        'ChatGPT Send button missing. The prompt remains visible '
                        'for manual review; no automatic retry was attempted.')
                try:
                    if hasattr(send,'is_enabled') and not await send.is_enabled():
                        raise OperatorActionRequired('ChatGPT Send button is disabled')
                except OperatorActionRequired:
                    raise
                except Exception:
                    pass
                if phase:phase('submitting')
                # Do not retry an ambiguous click; duplicates are worse than
                # a visible task requiring operator review.
                await send.click(timeout=12000)
                self.tasks[task_id]=BrowserJob(task_id,page,monotonic(),owns_tab)
                self.sessions._status['chatgpt']='awaiting_operator'
                self.last_error=None
                if phase:phase('awaiting_operator')
                return {'task_id':task_id,
                        'status':'awaiting_operator',
                        'submission':'send_clicked_unverified',
                        'typing_method':typing,
                        'automatic_output':False,
                        'action':'Review the result in the ChatGPT tab and import '
                                 'it into Exodia using the task response panel.'}
            except Exception as exc:
                self.last_error=str(exc)[:400]
                if page is not None:
                    await self.sessions._capture_failure('chatgpt',page)
                    if owns_tab:
                        try:await page.close()
                        except Exception:pass
                self.sessions._status['chatgpt']='dom_error_manual_review'
                if isinstance(exc,(SessionError,OperatorActionRequired,ValueError)):
                    raise
                raise SessionError(f'ChatGPT submission failed ({type(exc).__name__}). '
                                   'Inspect the browser and debug screenshot.') from exc

    async def complete(self,task_id:str,response:str):
        if task_id not in self.tasks:
            raise OperatorActionRequired('ChatGPT task has no open submission tab')
        if not isinstance(response,str) or not 1<=len(response.strip())<=100000:
            raise ValueError('Response must contain 1-100000 characters')
        await self._finish(task_id)
        return {'source':'operator_supplied','automatic_output':False,
                'answer':response.strip()}

    async def cancel(self,task_id:str):
        if task_id not in self.tasks:
            raise OperatorActionRequired('Task is not an open ChatGPT submission')
        await self._finish(task_id)
        return {'task_id':task_id,'status':'cancelled'}

    async def _finish(self,task_id:str):
        job=self.tasks.pop(task_id)
        if job.owns_tab:
            try:await job.page.close()
            except Exception:pass
        self.sessions._status['chatgpt']='awaiting_operator' if self.tasks else 'ready_for_next_prompt'

    async def close(self):
        for task_id in list(self.tasks):
            await self._finish(task_id)
