"""Local FastAPI service, JSON API and live event WebSocket."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
from time import monotonic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from app.config import Settings
from app.core.cache import SpeedrunnerCache
from app.core.router import Router
from app.rag.engine import CrystalArchives
from app.monitoring.logger import EventLog
from app.companions.director import CompanionDirector
from app.core.classifier import classify

settings = Settings()
cache = SpeedrunnerCache(settings.database)
archive = CrystalArchives(settings.database, settings.index_root, dense=__import__("app.config", fromlist=["enabled"]).enabled("DENSE_SEARCH"))
events = EventLog()
router = Router(settings, archive, cache, events)
director = CompanionDirector(settings.root, events)
started = monotonic()
app = FastAPI(title='The Command Tower', version='0.2.0', docs_url='/api/docs')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
app.mount('/assets', StaticFiles(directory=settings.root/'frontend'), name='assets')
events.publish('system', 'Command Tower boot sequence complete', 'Local mode active')

class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    channel: str = Field(default='auto', pattern='^(auto|api|browser|local)$')

@app.get('/')
async def home():
    return FileResponse(settings.root/'frontend'/'index.html')

@app.get('/companions')
async def companion_studio():
    return FileResponse(settings.root/'frontend'/'companions.html')

@app.get('/api/companions')
async def companions():
    return {'agents':director.agents,'states':director.snapshot(),'motion_tier':'interactive_2_5d'}

class ReactionBody(BaseModel):
    state: str = Field(min_length=3, max_length=16)

@app.post('/api/companions/{agent_id}/react')
async def companion_react(agent_id: str, body: ReactionBody):
    from fastapi import HTTPException
    try: return director.react(agent_id, body.state)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.get('/api/stats')
async def stats():
    return {'mode':'local', 'uptime_seconds':round(monotonic()-started),
            'indexed_chunks':archive.count(), 'cache_entries':cache.count(),
            'last_route':router.last_route, 'events':len(events.latest(160)),
            'config':settings.public_config(),
            'now':datetime.now(timezone.utc).isoformat()}

@app.get('/api/events')
async def recent_events():
    return {'events':events.latest(35)}

@app.post('/api/ask')
async def ask(body: AskBody):
    if body.channel == 'browser': kind='browser'
    elif body.channel == 'local': kind='rag'
    elif body.channel == 'api': kind='reasoning'
    else: kind,_=classify(body.question.strip())
    specialist={'browser':'ninja','rag':'archives','integration':'inventory','system':'strategy','reasoning':'memory'}.get(kind,'router')
    director.react('kiko','working')
    director.react(specialist,'working')
    result = await router.answer(body.question.strip(), body.channel)
    outcome='alert' if result.get('error') or result.get('data',{} ) and isinstance(result.get('data'),dict) and result['data'].get('browser_error') else 'rest' if result.get('cache_hit') else 'success'
    director.react(specialist,outcome)
    director.react('kiko',outcome)
    if result.get('cache_hit'): director.react('cache','rest')
    return result

@app.post('/api/index')
async def index_workspace():
    events.publish('task','Indexing local workspace',str(settings.index_root.name))
    director.react('archives','working')
    result = await asyncio.to_thread(archive.index_tree)
    cache.clear()  # invalidate potentially stale RAG answers
    events.publish('success','Crystal Archives synchronized',f"{result['files']} files · {result['chunks']} chunks")
    director.react('archives','success' if not result.get('errors') else 'alert')
    return result

@app.post('/api/cache/clear')
async def clear_cache():
    cache.clear()
    director.react('cache','success')
    events.publish('system','Cache cleared by operator')
    return {'cleared':True}

@app.post('/api/integrations/{provider}/check')
async def check_integration(provider: str):
    if provider not in {'github','etsy','youtube','gmail'}:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='Unknown provider')
    director.react('inventory','working')
    result = await router.answer(f'check {provider} metrics')
    director.react('inventory','alert' if result.get('error') else 'success')
    return result

@app.websocket('/ws/events')
async def updates(websocket: WebSocket):
    origin = websocket.headers.get('origin','')
    if origin and origin not in ('http://localhost:8765', 'http://127.0.0.1:8765',
                                 f'http://localhost:{settings.port}', f'http://127.0.0.1:{settings.port}'):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    q = events.subscribe()
    try:
        await websocket.send_json({'kind':'init', 'message':'Command link established'})
        while True:
            event = await q.get()
            await websocket.send_json(event)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        events.unsubscribe(q)


@app.get('/api/snapshots')
async def snapshots():
    files = sorted((settings.root/'debug_snapshots').glob('dom-error-*.png'),
                   key=lambda p:p.stat().st_mtime, reverse=True)
    return {'latest': files[0].name if files else None, 'count':len(files)}

@app.get('/api/snapshots/{name}')
async def snapshot_file(name: str):
    from fastapi import HTTPException
    if not re.fullmatch(r'dom-error-\d{8}-\d{6}\.png',name):
        raise HTTPException(status_code=404,detail='Not found')
    file = settings.root/'debug_snapshots'/name
    if not file.is_file():
        raise HTTPException(status_code=404,detail='Not found')
    return FileResponse(file, media_type='image/png',headers={'Cache-Control':'no-store',
                                                               'X-Content-Type-Options':'nosniff'})
