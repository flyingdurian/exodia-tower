"""Dual-channel command routing, fallbacks, local RAG and safe caching."""
from __future__ import annotations
import os
import json
from time import perf_counter
from app.core.classifier import classify
from app.mcp.clients import service_overview, ServiceError
from app.prompts.builder import build_messages
from app.automation.stealth import BrowserAssistant, BrowserUnavailable
from app.automation.multi_wrapper import MultiWebSessionManager, SessionError, OperatorActionRequired, PROVIDERS
from app.core.zero_api import ZeroAPIModelRouter

class Router:
    def __init__(self, settings, archives, cache, events):
        self.settings = settings
        self.archives = archives
        self.cache = cache
        self.events = events
        self.browser = BrowserAssistant(settings.root, settings.allowed_hosts)
        self.sessions = MultiWebSessionManager(settings.root, headless=getattr(settings, 'web_headless', False))
        self.models = ZeroAPIModelRouter(self.sessions)
        self.last_route = 'idle'
        self.live_metrics = {}

    async def start_sessions(self) -> dict:
        if not getattr(self.settings,"web_sessions_enabled",True):
            raise SessionError("Web sessions disabled in configuration.")
        return await self.sessions.initialize_all()

    async def close_sessions(self) -> None:
        await self.sessions.close()

    async def _llm(self, question: str, knowledge: str = "", metrics: str = "",
                   model_choice: str = "chatgpt") -> dict:
        messages=build_messages(question,user_state=os.getenv("USER_STATE",""),
                                live_metrics=metrics,retrieved_knowledge=knowledge)
        prompt="\n\n".join(m["content"] for m in messages)
        return await self.models.generate(prompt,model_choice)

    async def answer(self, question: str, channel: str = 'auto', model_choice: str = 'chatgpt') -> dict:
        start = perf_counter()
        if model_choice not in PROVIDERS:
            raise ValueError('Unknown model')
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
            status = 'complete'
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
                    self.events.publish('alert','Read-only page capture failed',type(exc).__name__)
                    raise
            else:
                results = self.archives.search(question, limit=3)
                evidence = '\n'.join(f"[{r['source']}] {r['snippet']}" for r in results)
                handoff = await self._llm(question, knowledge=evidence, metrics=json.dumps(self.live_metrics)[:5000], model_choice=model_choice)
                answer = handoff['action']
                status = handoff['status']
                data = {'model_handoff':handoff,'sources':results}
            self.events.publish('success' if status == 'complete' else 'task', 'Task completed' if status == 'complete' else 'Operator action required', action)
            return {'answer':answer, 'data':data, 'route':action, 'cache_hit':hit,
                    'latency_ms':round((perf_counter()-start)*1000), 'status':status}
        except (ServiceError, BrowserUnavailable, SessionError) as exc:
            self.events.publish('alert', 'Action needs attention', str(exc))
            return {'answer':str(exc), 'data':None, 'route':action, 'error':True,
                    'latency_ms':round((perf_counter()-start)*1000)}
        except Exception as exc:
            # Protect remote response bodies and secrets from leaking into logs or UI.
            self.events.publish('alert', 'Task execution failed', type(exc).__name__)
            return {'answer':f'Action failed: {type(exc).__name__}. Check local sessions and connection status.',
                    'data':None, 'route':action, 'error':True,
                    'latency_ms':round((perf_counter()-start)*1000)}
