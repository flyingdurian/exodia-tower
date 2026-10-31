"""Dual-channel command routing, fallbacks, local RAG and safe caching."""
from __future__ import annotations
import os
import json
from time import perf_counter
from app.core.classifier import classify
from app.mcp.clients import service_overview, ServiceError
from app.prompts.builder import build_messages
from app.security.vault import get_secret
from app.automation.stealth import BrowserAssistant, BrowserUnavailable

class Router:
    def __init__(self, settings, archives, cache, events):
        self.settings = settings
        self.archives = archives
        self.cache = cache
        self.events = events
        self.browser = BrowserAssistant(settings.root, settings.allowed_hosts)
        self.last_route = 'idle'
        self.live_metrics = {}

    async def _llm(self, question: str, knowledge: str = '', metrics: str = '') -> str:
        key = get_secret('OPENAI_API_KEY')
        if not key:
            return ('No reasoning API is configured. Add OPENAI_API_KEY to .env for model responses, '
                    'or use document search and connected service checks locally.')
        import httpx
        messages = build_messages(question, user_state=os.getenv('USER_STATE',''), live_metrics=metrics, retrieved_knowledge=knowledge)
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post('https://api.openai.com/v1/responses',
                                  headers={'Authorization':f'Bearer {key}',
                                           'Content-Type':'application/json'},
                                  json={'model':self.settings.openai_model,
                                        'input':messages, 'max_output_tokens':650})
            r.raise_for_status()
            obj = r.json()
            output = []
            for item in obj.get('output',[]):
                for part in item.get('content',[]):
                    if part.get('type') == 'output_text':
                        output.append(part.get('text', ''))
            if not output:
                return 'Model returned no displayable text.'
            return '\n'.join(output)

    async def answer(self, question: str, channel: str = 'auto') -> dict:
        start = perf_counter()
        action, service = classify(question)
        if channel == 'api':
            action = 'reasoning'  # use reasoning API explicitly
        elif channel == 'local':
            action = 'rag'
        elif channel == 'browser':
            action = 'browser'
        self.last_route = action
        self.events.publish('task', 'Kiko started a task', action)
        hit = False
        try:
            if action == 'system':
                answer = 'Exodia Tower is running locally. Check the connection cards for configured credentials; configuration does not prove authentication.'
                data = self.settings.public_config()
            elif action == 'integration' and service:
                data = await service_overview(service)
                # Retain a small, non-sensitive snapshot for next reasoning request.
                self.live_metrics[service] = {k:v for k,v in data.items() if k not in ('sample_message_ids',)}
                answer = f'{service.title()} API check completed. These are returned provider fields (not invented dashboard metrics).'
            elif action == 'rag':
                # The namespace is invalidated on reindex through the API.
                cached = self.cache.get('rag', question)
                if cached is not None:
                    hit = True
                    answer, data = cached, None
                else:
                    results = self.archives.search(question)
                    data = {'sources': results}
                    answer = ('\n\n'.join(f"{r['source']}: {r['snippet']}" for r in results)
                              if results else 'Nothing relevant is indexed yet. Click Index workspace to load local documents.')
                    self.cache.put('rag', question, answer, ttl_seconds=7200)
            elif action == 'browser':
                if not self.settings.browser_enabled or not self.settings.browser_read_url:
                    raise BrowserUnavailable('Browser channel is disabled. Set BROWSER_ENABLED=true, an HTTPS allowlist and BROWSER_READ_URL.')
                try:
                    data = await self.browser.read_page(self.settings.browser_read_url)
                    answer = f"Read-only page capture from {data['url']}. The result is a page snapshot, not an AI-generated response."
                except BrowserUnavailable as exc:
                    self.events.publish('alert','Browser read failed; API failover', str(exc))
                    if get_secret('OPENAI_API_KEY'):
                        answer = await self._llm(question, knowledge='Browser source was unavailable; do not claim to have read it.')
                        data = {'fallback':'API reasoning', 'browser_error':str(exc)}
                    else:
                        answer = 'Browser unavailable and no reasoning API is configured. ' + str(exc)
                        data = {'fallback':'manual', 'browser_error':str(exc)}
            else:
                results = self.archives.search(question, limit=3)
                evidence = '\n'.join(f"[{r['source']}] {r['snippet']}" for r in results)
                answer = await self._llm(question, knowledge=evidence, metrics=json.dumps(self.live_metrics)[:5000])
                data = {'sources':results} if results else None
            self.events.publish('success', 'Task completed', action + (' (cached)' if hit else ''))
            return {'answer':answer, 'data':data, 'route':action, 'cache_hit':hit,
                    'latency_ms':round((perf_counter()-start)*1000)}
        except (ServiceError, BrowserUnavailable) as exc:
            self.events.publish('alert', 'Action needs attention', str(exc))
            return {'answer':str(exc), 'data':None, 'route':action, 'error':True,
                    'latency_ms':round((perf_counter()-start)*1000)}
        except Exception as exc:
            # Protect remote response bodies and secrets from leaking into logs or UI.
            self.events.publish('alert', 'API request failed', type(exc).__name__)
            return {'answer':f'Action failed: {type(exc).__name__}. Check credentials, quotas, or network.',
                    'data':None, 'route':action, 'error':True,
                    'latency_ms':round((perf_counter()-start)*1000)}
