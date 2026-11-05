"""Task-bound, user-initiated ChatGPT browser submission with automatic response extraction.

Equipped with longest-content markdown block extraction, source deduplication, media capping, and artifact persistence.
"""
from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from app.automation.multi_wrapper import (
    MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS,
    type_composer_text,
)
from app.automation.model_instructions import user_request_text
from app.automation.gemini_media import media_intent

ARTIFACTS_DIR = Path("app_data/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

EDITOR_SELECTORS=(
    '#prompt-textarea[contenteditable="true"]',
    'div#prompt-textarea',
    '[data-testid="composer-input"][contenteditable="true"]',
    '[role="textbox"][contenteditable="true"]',
    'textarea[name="prompt"]',
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
    """Robust extraction with longest-content markdown block parsing, deduplicated media capping, and strict locks."""

    def __init__(self,sessions:MultiWebSessionManager,*,max_tabs:int=2,start_spacing:float=0.0,
                 idle_stable_s:float=1.5,confirmed_idle_s:float=0.45,max_wait_s:float=300.0,poll_s:float=0.25):
        if max_tabs<1 or start_spacing<0 or idle_stable_s<0 or confirmed_idle_s<=0 or max_wait_s<=0 or poll_s<=0:
            raise ValueError('Invalid ChatGPT limits')
        if confirmed_idle_s>idle_stable_s:
            confirmed_idle_s=idle_stable_s
        self.sessions=sessions
        self.max_tabs=max_tabs
        self.start_spacing=start_spacing
        self.idle_stable_s=idle_stable_s
        self.confirmed_idle_s=confirmed_idle_s
        self.max_wait_s=max_wait_s
        self.poll_s=poll_s
        self.tasks:dict[str,BrowserJob]={}
        self.start_lock=asyncio.Lock()
        self.last_start=0.0
        self.last_error=None

    def snapshot(self):
        return {'mode':'automatic_submit_automatic_result',
                'automatic_output_extraction':True,
                'pending_tasks':list(self.tasks),
                'pending_count':len(self.tasks),
                'max_pending_tabs':self.max_tabs,
                'last_error':self.last_error}

    async def _visible(self,page,selectors,timeout:float=3.0):
        deadline=monotonic()+timeout
        while monotonic()<deadline:
            for selector in selectors:
                try:
                    candidate=page.locator(selector).first
                    if await candidate.is_visible(timeout=50):
                        return candidate
                except Exception:
                    pass
            await asyncio.sleep(0.01)
        return None

    @staticmethod
    def _challenge_url(url:str)->bool:
        """A verification address only. This does not interact with the page."""
        value=(url or "").lower()
        host=(urlparse(value).hostname or "")
        return host=="challenges.cloudflare.com" or host.endswith(".challenges.cloudflare.com") or "cdn-cgi/challenge" in value or "challenges.cloudflare.com" in value

    async def _baseline(self,page):
        """Text and images already on the open chat, so a reused tab cannot return them."""
        try:
            raw=await page.evaluate("""() => {
                /* exodia-baseline */
                const main=document.querySelector('main');
                const text=main && main.innerText ? main.innerText.trim() : '';
                const srcs=[...document.querySelectorAll('img')]
                    .map(img => img.currentSrc || img.src || '')
                    .filter(Boolean);
                return {text, srcs};
            }""")
        except Exception:
            return '', set()
        if not isinstance(raw, dict):
            return '', set()
        return (raw.get('text') or '').strip(), set(raw.get('srcs') or [])

    async def _await_composer(self,page):
        """Find the composer. A verification page is left untouched and is not reloaded."""
        started=monotonic()
        while monotonic()-started<180:
            try:
                current=page.url or ""
            except Exception:
                current=""
            if self._challenge_url(current):
                await asyncio.sleep(0.5)
                continue
            editor=await self._visible(page,EDITOR_SELECTORS,timeout=0.8)
            if editor is not None:
                return editor
            if monotonic()-started>=4:
                return None
            await asyncio.sleep(0.25)
        return None

    async def submit(self,task_id:str,prompt:str,*,phase=None):
        if not task_id or len(task_id)>128:
            raise ValueError('Invalid task ID')
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:
            raise ValueError('Prompt must contain 1-12000 characters')
        if task_id in self.tasks:
            raise OperatorActionRequired('ChatGPT task already active; complete or cancel existing run')

        t_begin=monotonic()
        if 'chatgpt' not in self.sessions._contexts:
            if phase:phase('opening')
            await self.sessions.initialize_one('chatgpt')
        context=self.sessions._contexts.get('chatgpt')
        if context is None:
            raise SessionError('ChatGPT browser context is unavailable')
        
        async with self.start_lock:
            if len(self.tasks)>=self.max_tabs:
                raise OperatorActionRequired(
                    f'ChatGPT has {len(self.tasks)} active task tab(s). '
                    'Wait for completion or cancel one before starting another.')
            if task_id in self.tasks:
                raise OperatorActionRequired('ChatGPT task already submitted')

        page = None
        owns_tab = True
        try:
            if phase:phase('opening')

            # Each task gets its own tab so the previous conversation cannot
            # mix into this answer. The anchor tab stays open for the sign-in.
            # A verification address is not loaded a second time.
            if hasattr(context, 'new_page'):
                page = await context.new_page()
            else:
                page = self.sessions._pages.get('chatgpt')
                owns_tab = False
            if page is None:
                raise SessionError('No ChatGPT browser tab available')

            job = BrowserJob(task_id, page, monotonic(), owns_tab)
            self.tasks[task_id] = job

            base_url = PROVIDERS['chatgpt'].url.rstrip('/')
            try:
                current=page.url or ""
            except Exception:
                current=""
            if not self._challenge_url(current):
                await page.goto(base_url, wait_until='domcontentloaded', timeout=12000)
            if not self._challenge_url(getattr(page,'url','')):
                self.sessions._check_destination('chatgpt', page.url)

            t_editor=monotonic()
            editor=await self._await_composer(page)
            editor_ready=monotonic()
            if editor is None:
                raise OperatorActionRequired(
                    'ChatGPT composer not found. Finish any verification in the open '
                    'ChatGPT window, then create a new task. The check is not retried automatically.')
            
            prompt_text=prompt.strip()
            request_text=user_request_text(prompt_text)
            prior_text, prior_images=await self._baseline(page)
            # Instructions can be long and can mention pictures. Judge the
            # visitor's request only, so a real image task still returns the file.
            is_image_prompt = media_intent(request_text) and len(request_text) < 600

            if phase:phase('typing')
            t_typing=monotonic()
            
            await editor.click(timeout=2000)
            await page.keyboard.press('ControlOrMeta+A')
            typing=await type_composer_text(page, prompt_text, prefer_insert=True)
            
            typed_at=monotonic()

            send=await self._visible(page,SEND_SELECTORS,timeout=1.0)
            if phase:phase('submitting')
            if send is not None:
                await send.click(timeout=1500)
                submission='send_clicked'
            else:
                await page.keyboard.press('Enter')
                submission='enter_submitted'
            submitted_at=monotonic()

            if phase:phase('waiting_for_reply')
            
            print("[ChatGPT Debug] Waiting until ChatGPT has finished generating...")
            answer = ""
            raw_image_candidates = []
            start_wait = monotonic()
            last_seen_text = ""
            last_image_signature = ()
            idle_since = None
            stream_complete = False
            still_generating = True

            while monotonic() - start_wait < self.max_wait_s:
                try:
                    eval_result = await page.evaluate("""async (promptText) => {
                        const visible = (el) => {
                            if (!el) return false;
                            const style = window.getComputedStyle(el);
                            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        };
                        const stopBtn = document.querySelector(
                            'button[data-testid="stop-button"], button[data-testid="stop-generating-button"], button[aria-label="Stop generating"], button[aria-label="Stop response"], button[aria-label="Stop streaming"], button.stop-button'
                        );
                        const sendBtn = document.querySelector(
                            'button[data-testid="send-button"], button[data-testid="composer-send-button"], button[aria-label="Send message"], button[aria-label="Send prompt"]'
                        );
                        const stopVisible = visible(stopBtn);
                        const sendEnabled = visible(sendBtn) && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true';
                        const streamingCursor = !!document.querySelector(
                            'main .result-streaming, main [data-is-streaming="true"]'
                        );
                        const main = document.querySelector('main');
                        let assistantText = '';
                        let turnCount = 0;
                        let candidates = [];
                        let finishedControls = false;

                        if (main) {
                            const turns = main.querySelectorAll(
                                '[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article'
                            );
                            turnCount = turns.length;
                            const latest = turns.length ? turns[turns.length - 1] : null;

                            if (latest) {
                                let rawText = latest.innerText ? latest.innerText.trim() : '';
                                if (rawText.includes(promptText)) {
                                    rawText = rawText.replace(promptText, '').trim();
                                }
                                assistantText = rawText;
                                finishedControls = !!latest.querySelector(
                                    '[data-testid="copy-turn-action-button"], button[aria-label="Copy"], button[aria-label="Copy message"], button[aria-label="Good response"]'
                                );
                            }

                            if (!assistantText) {
                                const blocks = [...main.querySelectorAll(
                                    'div.markdown, [class*="markdown"], [class*="prose"], [data-message-content]'
                                )].filter(el => el.innerText?.trim());

                                if (blocks.length > 0) {
                                    const best = blocks.reduce((a, b) =>
                                        b.innerText.trim().length > a.innerText.trim().length ? b : a
                                    );
                                    let bestText = best.innerText.trim();
                                    if (bestText.includes(promptText)) {
                                        bestText = bestText.replace(promptText, '').trim();
                                    }
                                    assistantText = bestText;
                                }
                            }

                            const imgs = [];
                            const visit = (root) => {
                                if (!root?.querySelectorAll) return;
                                root.querySelectorAll('img').forEach((img) => imgs.push(img));
                                root.querySelectorAll('*').forEach((el) => { if (el.shadowRoot) visit(el.shadowRoot); });
                            };
                            visit(document);
                            imgs.forEach((img, index) => {
                                let src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                                const rect = img.getBoundingClientRect();
                                const width = img.naturalWidth || rect.width || img.width || 0;
                                const height = img.naturalHeight || rect.height || img.height || 0;
                                const isSmall = width < 150 || height < 150 || src.startsWith('data:image/svg') || src.includes('avatar') || src.includes('logo') || src.includes('icon');
                                if (!isSmall && src) {
                                    candidates.push({ src, width, height, index });
                                }
                            });
                        }

                        const composerIdle = sendEnabled && !stopVisible && !streamingCursor;
                        // Missing composer or copy controls is not evidence that
                        // ChatGPT is still writing. Only a visible stop control
                        // or an active streaming marker holds the reply open.
                        const isGenerating = stopVisible || streamingCursor;
                        return { foundText: assistantText, candidates, isGenerating, turnCount, composerIdle, finishedControls, stopVisible };
                    }""", prompt_text)
                    
                    current_text = (eval_result.get('foundText') or '').strip()
                    if prior_text and current_text==prior_text:
                        current_text=''
                    candidates = [item for item in eval_result.get('candidates', [])
                                  if item.get('src') not in prior_images]
                    is_generating = bool(eval_result.get('isGenerating'))
                    composer_idle = bool(eval_result.get('composerIdle'))
                    finished_controls = bool(eval_result.get('finishedControls'))
                    turn_count = eval_result.get('turnCount', 0)
                    still_generating = is_generating
                    
                    print(f"[ChatGPT Poll] Gen: {is_generating} | Stop: {bool(eval_result.get('stopVisible'))} | Idle: {composer_idle} | DoneUI: {finished_controls} | Turns: {turn_count} | Images: {len(candidates)} | TextLen: {len(current_text)} | Preview: {current_text[:30]}...")
                    
                    if is_image_prompt and candidates:
                        raw_image_candidates = candidates

                    lower_text = current_text.lower()
                    if "hit the free plan limit" in lower_text or "free plan limit for image generations" in lower_text:
                        print("[ChatGPT Poll] Free plan limit message detected. Capturing immediately.")
                        answer = current_text
                        stream_complete = True
                        still_generating = False
                        break

                    is_transient = len(current_text) < 60 and any(w in lower_text for w in ["searching the web", "thinking", "analyzing", "browsing", "reading"])
                    text_changed = current_text != last_seen_text
                    image_signature = tuple(item.get('src') for item in raw_image_candidates)
                    image_changed = image_signature != last_image_signature
                    if text_changed:
                        last_seen_text = current_text
                    if image_changed:
                        last_image_signature = image_signature
                    if current_text and current_text != prompt_text and not is_transient:
                        answer = current_text

                    text_ready = (
                        not is_generating
                        and not is_transient
                        and current_text
                        and current_text != prompt_text
                        and len(current_text) >= 30
                    )
                    image_ready = is_image_prompt and not is_generating and bool(raw_image_candidates)
                    reply_finished = text_ready or image_ready

                    # Copy controls mean the turn is complete. Without them,
                    # keep the longer unchanged-text hold so a pause is not returned.
                    settle_s = self.confirmed_idle_s if finished_controls and not is_generating else self.idle_stable_s
                    if reply_finished and not text_changed and not image_changed:
                        if idle_since is None:
                            idle_since = monotonic()
                        elif monotonic() - idle_since >= settle_s:
                            print("[ChatGPT Poll] Reply finished: generation stopped, text stable. Closing after capture.")
                            stream_complete = True
                            still_generating = False
                            break
                    else:
                        idle_since = None
                except Exception as poll_exc:
                    print(f"[ChatGPT Poll Exception]: {type(poll_exc).__name__}: {poll_exc}")
                    idle_since = None
                if stream_complete:
                    break
                await asyncio.sleep(self.poll_s)

            finished_at = monotonic()
            if not stream_complete:
                if still_generating or not answer.strip():
                    raise SessionError(
                        "ChatGPT was still generating or returned no finished reply. "
                        "Partial responses are not captured."
                    )
                raise SessionError(
                    "ChatGPT reply did not stay finished long enough to capture. "
                    "Partial responses are not returned."
                )
            
            media_list = []
            seen_sources = set()

            for cand in raw_image_candidates:
                src = cand["src"]
                if src in seen_sources:
                    continue
                seen_sources.add(src)

                try:
                    file_bytes = None
                    mime = "image/png"
                    
                    if src.startswith('blob:'):
                        try:
                            base64_data = await page.evaluate("""async (imgSrc) => {
                                const res = await fetch(imgSrc);
                                const blob = await res.blob();
                                return await new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result);
                                    reader.readAsDataURL(blob);
                                });
                            }""", src)
                            
                            if base64_data and "," in base64_data:
                                header, encoded = base64_data.split(",", 1)
                                if ":" in header and ";" in header:
                                    mime = header.split(":")[1].split(";")[0]
                                file_bytes = base64.b64decode(encoded)
                        except Exception as blob_err:
                            print(f"[Blob Fetch Error]: {blob_err}")
                    else:
                        try:
                            response = await page.context.request.get(
                                src,
                                headers={"Referer": page.url},
                            )
                            if response.ok:
                                file_bytes = await response.body()
                                mime = response.headers.get("content-type", "image/png")
                        except Exception as req_err:
                            print(f"[Request Context Error]: {req_err}")

                    if not file_bytes:
                        try:
                            img_locator = page.locator('main img').nth(cand['index'])
                            file_bytes = await img_locator.screenshot(type='png')
                            mime = "image/png"
                        except Exception as screenshot_err:
                            print(f"[Screenshot Fallback Error]: {screenshot_err}")

                    if file_bytes:
                        ext = "png"
                        if "jpeg" in mime or "jpg" in mime:
                            ext = "jpg"
                        elif "webp" in mime:
                            ext = "webp"

                        filename = f"{uuid4().hex}.{ext}"
                        file_path = ARTIFACTS_DIR / filename
                        file_path.write_bytes(file_bytes)
                        
                        media_list.append({
                            "kind": "image",
                            "url": f"/artifacts/{filename}"
                        })

                    if len(media_list) >= 4:
                        break
                except Exception as save_err:
                    print(f"[Artifact Processing Error]: {save_err}")

            if not answer.strip() and last_seen_text.strip():
                answer = last_seen_text

            if not answer.strip() and not media_list: 
                raise SessionError("ChatGPT returned no readable text or media within the timeout window.")

            if not answer.strip() and media_list:
                answer = "Generated image"

            self.sessions._status['chatgpt']='ready_for_next_prompt'
            self.last_error=None

            timings={'editor_wait_s':round(editor_ready-t_editor,3),
                     'typing_s':round(typed_at-t_typing,3),
                     'submit_s':round(submitted_at-typed_at,3),
                     'first_text_s':None,
                     'stream_completion_s':round(finished_at-submitted_at,3),
                     'total_s':round(finished_at-t_begin,3),
                     'typing_method':typing}
            return {'task_id':task_id,
                    'status':'answered',
                    'submission':submission,
                    'typing_method':typing,
                    'automatic_output':True,
                    'answer':answer.strip()[:100000],
                    'media': media_list,
                    'timings':timings}
        except asyncio.CancelledError:
            self.sessions._status['chatgpt']='ready_for_next_prompt'
            self.last_error=None
            raise
        except Exception as exc:
            self.last_error=str(exc)[:400]
            if page is not None:
                try:
                    await self.sessions._capture_failure('chatgpt', page)
                except Exception:
                    pass
            self.sessions._status['chatgpt']='dom_error_manual_review'
            if isinstance(exc,(SessionError,OperatorActionRequired,ValueError)):
                raise
            raise SessionError(f'ChatGPT submission/extraction failed ({type(exc).__name__}). '
                               'Inspect the browser and debug screenshot.') from exc
        finally:
            self.tasks.pop(task_id, None)
            if owns_tab and page is not None:
                try:
                    await page.close()
                except Exception:
                    pass

    async def complete(self,task_id:str,response:str):
        return {'source':'operator_supplied','automatic_output':True,
                'answer':response.strip()}

    async def cancel(self,task_id:str):
        if task_id not in self.tasks:
            raise OperatorActionRequired('Task is not an open ChatGPT submission')
        await self._finish(task_id)
        return {'task_id': task_id, 'status': 'cancelled'}

    async def _finish(self,task_id:str):
        job=self.tasks.pop(task_id, None)
        if job and job.owns_tab:
            try:await job.page.close()
            except Exception:pass
        self.sessions._status['chatgpt']='ready_for_next_prompt'

    async def close(self):
        for task_id in list(self.tasks):
            await self._finish(task_id)