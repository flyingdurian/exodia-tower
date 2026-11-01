"""Task-bound, user-initiated ChatGPT browser submission with automatic response extraction.

Equipped with longest-content markdown block extraction, source deduplication, media capping, and artifact persistence.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from app.automation.multi_wrapper import (
    MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS,
)

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

    def __init__(self,sessions:MultiWebSessionManager,*,max_tabs:int=2,start_spacing:float=0.0):
        if max_tabs<1 or start_spacing<0:raise ValueError('Invalid ChatGPT limits')
        self.sessions=sessions
        self.max_tabs=max_tabs
        self.start_spacing=start_spacing
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
            await page.goto(base_url, wait_until='domcontentloaded', timeout=12000)
            self.sessions._check_destination('chatgpt', page.url)

            t_editor=monotonic()
            editor=await self._visible(page,EDITOR_SELECTORS,timeout=4.0)
            editor_ready=monotonic()
            if editor is None:
                raise OperatorActionRequired(
                    'ChatGPT composer not found. Complete any on-screen '
                    'prompts or reviews manually, then create a new task.')
            
            prompt_text=prompt.strip()
            prompt_lower = prompt_text.lower()
            is_image_prompt = any(k in prompt_lower for k in ["generate", "draw", "create an image", "picture of", "photo of", "illustrate", "apple", "pineapple", "banana", "cat", "dog"])

            if phase:phase('typing')
            t_typing=monotonic()
            
            await editor.click(timeout=2000)
            await page.keyboard.press('ControlOrMeta+A')
            
            if hasattr(page.keyboard,'insert_text'):
                await page.keyboard.insert_text(prompt_text)
                typing='insert_text'
            else:
                await page.keyboard.type(prompt_text,delay=0)
                typing='keyboard_type'
            
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
            
            print("[ChatGPT Debug] Starting extraction loop with clean content block selection...")
            answer = ""
            raw_image_candidates = []
            max_wait = 180.0
            start_wait = monotonic()
            last_seen_text = ""
            last_change_time = monotonic()

            while monotonic() - start_wait < max_wait:
                await asyncio.sleep(0.5)
                try:
                    eval_result = await page.evaluate("""async (promptText) => {
                        const stopBtn = document.querySelector('button[data-testid="stop-button"], button[aria-label="Stop generating"], button[aria-label="Stop response"], button.stop-button, [data-icon="stop"]');
                        const isGenerating = stopBtn !== null && window.getComputedStyle(stopBtn).display !== 'none';

                        const main = document.querySelector('main');
                        let assistantText = '';
                        let turnCount = 0;
                        let candidates = [];

                        if (main) {
                            const turns = main.querySelectorAll(
                                '[data-message-author-role="assistant"], [data-testid*="conversation-turn"], article'
                            );
                            turnCount = turns.length;

                            if (turns.length > 0) {
                                const latest = turns[turns.length - 1];
                                let rawText = latest.innerText ? latest.innerText.trim() : '';
                                if (rawText.includes(promptText)) {
                                    rawText = rawText.replace(promptText, '').trim();
                                }
                                assistantText = rawText;
                            }

                            // CLEAN CONTENT BLOCK STRATEGY: Select the longest markdown/prose/content block to avoid UI chrome
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

                            const latestTurn = turns.length ? turns[turns.length - 1] : null;
                            const imageScope = latestTurn || main;
                            if (imageScope) {
                                const imgs = imageScope.querySelectorAll('img');
                                imgs.forEach((img, index) => {
                                    let src = img.src || img.getAttribute('data-src') || '';
                                    const width = img.naturalWidth || img.width || 0;
                                    const height = img.naturalHeight || img.height || 0;
                                    const isSmall = width < 150 || height < 150 || src.startsWith('data:image/svg') || src.includes('avatar') || src.includes('logo') || src.includes('icon');
                                    if (!isSmall && src) {
                                        candidates.push({ src, width, height, index });
                                    }
                                });
                            }
                        }

                        return { foundText: assistantText, candidates, isGenerating, turnCount };
                    }""", prompt_text)
                    
                    current_text = eval_result['foundText'].strip()
                    candidates = eval_result.get('candidates', [])
                    is_generating = eval_result['isGenerating']
                    turn_count = eval_result.get('turnCount', 0)
                    
                    print(f"[ChatGPT Poll] Gen: {is_generating} | Turns: {turn_count} | Scoped Images: {len(candidates)} | TextLen: {len(current_text)} | Preview: {current_text[:30]}...")
                    
                    if candidates:
                        raw_image_candidates = candidates

                    lower_text = current_text.lower()
                    if "hit the free plan limit" in lower_text or "free plan limit for image generations" in lower_text:
                        print("[ChatGPT Poll] Free plan limit message detected. Capturing immediately.")
                        answer = current_text
                        break

                    is_transient = len(current_text) < 60 and any(w in lower_text for w in ["searching the web", "thinking", "analyzing", "browsing", "reading"])
                    
                    if is_image_prompt:
                        if len(raw_image_candidates) > 0:
                            if not is_generating or (monotonic() - start_wait > 4.0):
                                print("[ChatGPT Poll] Generated high-res image detected and stable. Breaking loop.")
                                answer = current_text if current_text else "Generated image"
                                break
                        else:
                            continue
                    else:
                        has_valid_content = (current_text and current_text != prompt_text and not is_transient)
                        if has_valid_content:
                            if current_text != last_seen_text:
                                last_seen_text = current_text
                                last_change_time = monotonic()
                            
                            if (
                                current_text
                                and not is_generating
                                and monotonic() - last_change_time >= 5.0
                            ):
                                print("[ChatGPT Poll] Text response stable for 5s and generation finished. Breaking loop.")
                                answer = current_text
                                break
                            
                            if monotonic() - last_change_time >= 15.0 and len(current_text) > 10:
                                print("[ChatGPT Poll] Text response stable for 15s timeout fallback. Breaking loop.")
                                answer = current_text
                                break
                except Exception as poll_exc:
                    print(f"[ChatGPT Poll Exception]: {type(poll_exc).__name__}: {poll_exc}")

            finished_at = monotonic()
            
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