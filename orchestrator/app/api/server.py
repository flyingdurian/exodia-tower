"""Local FastAPI service, JSON API and live event WebSocket."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
from time import monotonic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from app.config import Settings
from app.core.cache import SpeedrunnerCache
from app.core.router import Router
from app.automation.multi_wrapper import SessionError, OperatorActionRequired, PROVIDERS
from app.rag.engine import CrystalArchives
from app.monitoring.logger import EventLog
from app.companions.director import CompanionDirector
from app.companions.rigs import load_all
from app.core.classifier import classify
from app.social.workflow import EditorialStore, WorkflowError
from app.operations.inbox import Inbox
from app.automation.local_llm import OllamaBackend, LocalModelError

settings = Settings()
cache = SpeedrunnerCache(settings.database)
archive = CrystalArchives(settings.database, settings.index_root, dense=__import__("app.config", fromlist=["enabled"]).enabled("DENSE_SEARCH"))
events = EventLog()
router = Router(settings, archive, cache, events)
director = CompanionDirector(settings.root, events)
social = EditorialStore(settings.root / "app_data" / "editorial.sqlite")
inbox=Inbox(settings.root/'app_data'/'companion_tasks.sqlite')
inbox.fail_interrupted()
local_model=OllamaBackend()
active_generations=set()
started = monotonic()
app = FastAPI(title='Exodia Tower', version='0.3.0', docs_url='/api/docs')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
app.mount('/assets', StaticFiles(directory=settings.root/'frontend'), name='assets')
(settings.root/'app_data'/'artifacts').mkdir(parents=True,exist_ok=True)
app.mount('/artifacts',StaticFiles(directory=settings.root/'app_data'/'artifacts'),name='artifacts')
events.publish('system', 'Exodia Tower boot sequence complete', 'Local mode active')

class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    channel: str = Field(default='auto', pattern='^(auto|api|browser|local)$')
    model_choice: str = Field(default='chatgpt', pattern='^(chatgpt|gemini|deepseek)$')

@app.on_event('shutdown')
async def stop_browser_sessions():
    await router.close_sessions()

@app.get('/')
async def home():
    return FileResponse(settings.root/'frontend'/'exodia_workstations.html')

@app.get('/art-studio')
async def art_studio():
    return FileResponse(settings.root/'frontend'/'kiko_art_lab.html')

@app.get('/puppet-lab')
async def puppet_lab():
    return FileResponse(settings.root/'frontend'/'puppet_lab.html')

@app.get('/legacy')
async def legacy():return FileResponse(settings.root/'frontend'/'index.html')

@app.get('/rig-lab')
async def rig_lab():
    return FileResponse(settings.root/'frontend'/'rig_lab.html')

@app.get('/api/rigs')
async def rig_manifests():
    rigs=load_all(settings.root)
    return {'rigs':{k:{'bones':len(v['bones']), 'emotions':len(v['poses']),
                       'status':v['status'],'production_ready':v['production_ready']}
                    for k,v in rigs.items()}}

@app.get('/companions')
async def companion_studio():
    return FileResponse(settings.root/'frontend'/'companions.html')

@app.get('/api/companions')
async def companions():
    return {'agents':director.agents,'states':director.snapshot(),'motion_tier':'projection_navigation',
            'articulated_rigs_ready':False}

class ReactionBody(BaseModel):
    state: str = Field(min_length=3, max_length=16)

@app.post('/api/companions/{agent_id}/react')
async def companion_react(agent_id: str, body: ReactionBody):
    from fastapi import HTTPException
    try: return director.react(agent_id, body.state)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.get('/api/web/sessions')
async def web_sessions():
    return {'models':router.sessions.snapshot(),'automatic_extraction':False}

@app.post('/api/web/sessions/start')
async def start_web_sessions(x_exodia_client: str = Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(status_code=403,detail='Local operator confirmation required')
    try: return {'models':await router.start_sessions()}
    except SessionError as exc: raise HTTPException(status_code=503,detail=str(exc)) from exc

class ModelPrompt(BaseModel):
    prompt: str = Field(min_length=1,max_length=12000)

@app.post('/api/web/sessions/{model_choice}/prepare')
async def prepare_web_prompt(model_choice: str,body: ModelPrompt,x_exodia_client: str = Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(status_code=403,detail='Local operator confirmation required')
    try: return await router.models.generate(body.prompt,model_choice)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except SessionError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc

class OperatorResponse(BaseModel):
    response: str = Field(min_length=1,max_length=100000)

@app.post('/api/web/sessions/{model_choice}/record')
async def record_web_answer(model_choice: str,body: OperatorResponse,x_exodia_client: str = Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(status_code=403,detail='Local operator confirmation required')
    try: return router.models.record_operator_response(model_choice,body.response)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except SessionError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc

@app.get('/api/stats')
async def stats():
    return {'mode':'local', 'uptime_seconds':round(monotonic()-started),
            'indexed_chunks':archive.count(), 'cache_entries':cache.count(),
            'last_route':router.last_route, 'events':len(events.latest(160)),
            'config':settings.public_config(), 'web_sessions':router.sessions.snapshot(),
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
    result = await router.answer(body.question.strip(), body.channel, body.model_choice)
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
    if not re.fullmatch(r'dom-error-\d{8}-\d{6}(?:-\d{6}-(?:chatgpt|gemini|deepseek))?\.png',name):
        raise HTTPException(status_code=404,detail='Not found')
    file = settings.root/'debug_snapshots'/name
    if not file.is_file():
        raise HTTPException(status_code=404,detail='Not found')
    return FileResponse(file, media_type='image/png',headers={'Cache-Control':'no-store',
                                                               'X-Content-Type-Options':'nosniff'})


# All social API mutations are guarded against cross-site form posts and unrelated pages.
# The service remains bound to localhost; this is not multi-user authentication.
def require_local_dashboard(x_exodia_client: str = Header(default='')):
    if x_exodia_client != 'exodia-dashboard':
        raise HTTPException(status_code=403, detail='Local dashboard request header required')

class SocialCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    concept: str = Field(default='', max_length=4000)
    platforms: list[str] = Field(min_length=1, max_length=3)
    source_urls: list[str] = Field(default_factory=list, max_length=12)

class SocialPatch(BaseModel):
    fields: dict

class SocialAdvance(BaseModel):
    stage: str

class SocialApproval(BaseModel):
    confirmation: str

@app.get('/api/social/status')
async def social_status():
    return {'summary': social.summary(), 'connections':{
        'youtube':'not_connected','tiktok':'not_connected','instagram':'not_connected'},
        'agent':'nova','capabilities':['local_drafts','research_briefs','review_queue'],
        'restrictions':['no_external_uploads','no_analytics_claims','no_autopublishing']}

@app.get('/api/social/jobs')
async def social_jobs():
    return {'jobs': social.list()}

@app.get('/api/social/jobs/{job_id}')
async def social_job(job_id: str):
    try: return social.get(job_id)
    except KeyError: raise HTTPException(status_code=404, detail='Not found')

@app.post('/api/social/jobs', status_code=201)
async def social_create(body: SocialCreate, x_exodia_client: str = Header(default='')):
    require_local_dashboard(x_exodia_client)
    try: job=social.create(body.title, body.platforms, body.concept, body.source_urls)
    except WorkflowError as e: raise HTTPException(status_code=422, detail=str(e))
    director.react('nova','success')
    events.publish('task', 'Nova created an editorial draft', job['title'])
    return job

@app.patch('/api/social/jobs/{job_id}')
async def social_update(job_id: str, body: SocialPatch, x_exodia_client: str = Header(default='')):
    require_local_dashboard(x_exodia_client)
    try: return social.update(job_id,body.fields)
    except KeyError: raise HTTPException(status_code=404, detail='Not found')
    except WorkflowError as e: raise HTTPException(status_code=422, detail=str(e))

@app.post('/api/social/jobs/{job_id}/advance')
async def social_advance(job_id: str, body: SocialAdvance, x_exodia_client: str = Header(default='')):
    require_local_dashboard(x_exodia_client)
    try: job=social.advance(job_id,body.stage)
    except KeyError: raise HTTPException(status_code=404, detail='Not found')
    except WorkflowError as e: raise HTTPException(status_code=422, detail=str(e))
    director.react('nova','thinking')
    events.publish('task', 'Nova advanced a draft',f"{job['title']} → {job['stage']}")
    return job

@app.post('/api/social/jobs/{job_id}/approve')
async def social_approve(job_id: str,body:SocialApproval,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try: job=social.approve(job_id,body.confirmation)
    except KeyError: raise HTTPException(status_code=404,detail='Not found')
    except WorkflowError as e: raise HTTPException(status_code=422,detail=str(e))
    director.react('nova','success')
    events.publish('success','Content approved for future submission',job['title'])
    return job

@app.get('/api/social/jobs/{job_id}/brief')
async def social_brief(job_id: str):
    try: return social.brief(job_id)
    except KeyError: raise HTTPException(status_code=404,detail='Not found')

@app.post('/api/social/jobs/{job_id}/publish')
async def social_publish_disabled(job_id: str,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:social.get(job_id)
    except KeyError: raise HTTPException(status_code=404,detail='Not found')
    raise HTTPException(status_code=409,detail='Publishing disabled until authorized official platform adapters and per-post approval are verified')


# U2 — browser task inbox. Persist only operator-supplied output, never scraped output.
class CompanionTaskBody(BaseModel):
    prompt:str=Field(min_length=1,max_length=12000)
    model_choice:str=Field(pattern='^(ollama|chatgpt|gemini|deepseek)$')
    agent_id:str=Field(min_length=1,max_length=64)
class CompanionTaskAnswer(BaseModel):
    answer:str=Field(min_length=1,max_length=100000)

async def _complete_local_task(task_id: str):
    """Run local inference asynchronously; task state is always persisted."""
    try:
        t=inbox.get(task_id)
        result=await local_model.generate(t['prompt'],companion=t['agent_id'])
        inbox.update(task_id,'answer',result['answer'])
        inbox.update(task_id,'state','answered')
        director.react(t['agent_id'],'success')
        events.publish('success','Companion received autonomous model response',
                       f"{t['agent_id']}:ollama")
    except Exception as exc:
        # Never record a failed inference as a successful answer.
        message=str(exc) if isinstance(exc,(LocalModelError,ValueError)) else             'Unexpected local inference error. Check Exodia logs.'
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(t['agent_id'],'alert')
        events.publish('alert','Companion inference failed',f"{t['agent_id']}:ollama")

@app.get('/api/command/providers')
async def command_providers():
    return {'ollama':await local_model.status(),
            'website_workspaces':'manual_only'}

@app.get('/api/command/tasks')
async def command_list():
    return {'tasks':inbox.list(),'sessions':router.sessions.snapshot(),'automatic_extraction':False}

@app.post('/api/command/tasks',status_code=201)
async def command_create(body:CompanionTaskBody,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    if body.agent_id not in director.known:raise HTTPException(422,detail='Unknown companion')
    try:t=inbox.create(body.agent_id,body.model_choice,body.prompt)
    except ValueError as e:raise HTTPException(422,detail=str(e))
    if body.model_choice=='ollama':
        t=inbox.update(t['id'],'state','running')
        director.react(body.agent_id,'working')
        job=asyncio.create_task(_complete_local_task(t['id']))
        active_generations.add(job)
        job.add_done_callback(active_generations.discard)
        events.publish('task','Autonomous companion inference started',f"{body.agent_id}:ollama")
    else:
        director.react(body.agent_id,'thinking')
        events.publish('task','Manual website task created',f"{body.agent_id}:{body.model_choice}")
    return t

@app.post('/api/command/tasks/{task_id}/prepare')
async def command_prepare(task_id:str,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:t=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    if t['provider']=='ollama':raise HTTPException(409,detail='Local inference starts automatically; no browser preparation needed')
    if t['state']!='draft':raise HTTPException(409,detail='Already prepared')
    try:info=await router.models.generate(t['prompt'],t['provider'])
    except (SessionError,ValueError) as e:raise HTTPException(409,detail=str(e))
    saved=inbox.update(task_id,'state','awaiting_operator')
    director.react(t['agent_id'],'working')
    return {'task':saved,'instructions':info}

@app.post('/api/command/tasks/{task_id}/response')
async def command_response(task_id:str,body:CompanionTaskAnswer,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:t=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    if t['state']!='awaiting_operator':raise HTTPException(409,detail='Prepare the prompt first')
    try:router.models.record_operator_response(t['provider'],body.answer)
    except (SessionError,ValueError) as e:raise HTTPException(409,detail=str(e))
    inbox.update(task_id,'answer',body.answer.strip())
    saved=inbox.update(task_id,'state','answered')
    director.react(t['agent_id'],'success')
    events.publish('success','Operator-delivered response',f"{t['agent_id']}:{t['provider']}")
    return saved

@app.post('/api/command/tasks/{task_id}/artifact')
async def command_artifact(task_id:str,request:Request,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:t=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    if t['state']!='answered':raise HTTPException(409,detail='Record response before image')
    content_type=request.headers.get('content-type','').split(';')[0].lower()
    extensions={'image/png':('.png',b'\x89PNG\r\n\x1a\n'),'image/jpeg':('.jpg',b'\xff\xd8\xff'),'image/webp':('.webp',b'RIFF')}
    if content_type not in extensions:raise HTTPException(415,detail='PNG, JPEG or WebP only')
    content=bytearray()
    async for chunk in request.stream():
        if len(content)+len(chunk)>8*1024*1024:raise HTTPException(413,detail='Image exceeds 8 MiB')
        content.extend(chunk)
    ext,magic=extensions[content_type]
    if not content.startswith(magic) or (ext=='.webp' and content[8:12]!=b'WEBP'):
        raise HTTPException(415,detail='Invalid image header')
    from uuid import uuid4
    fname=f"{uuid4().hex}{ext}"
    (settings.root/'app_data'/'artifacts'/fname).write_bytes(content)
    return inbox.update(task_id,'artifact',f"/artifacts/{fname}")
