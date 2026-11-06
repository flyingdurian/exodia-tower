"""Local FastAPI service, JSON API and live event WebSocket."""
from __future__ import annotations
import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import re
from time import monotonic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Request
from fastapi.responses import FileResponse, Response, JSONResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from app.config import Settings
from app.build_info import APP_VERSION, build_info
from app.automation.provider_catalog import selection, public_catalog
from app.core.cache import SpeedrunnerCache
from app.core.router import Router
from app.automation.multi_wrapper import SessionError, OperatorActionRequired, PROVIDERS
from app.automation.chatgpt_bridge import ChatGPTSubmissionBridge
from app.automation.model_instructions import (
    InstructionStore, BROWSER_MODELS, combine_instructions, compose_model_prompt, public_task,
)
from app.rag.engine import CrystalArchives
from app.monitoring.logger import EventLog
from app.companions.director import CompanionDirector
from app.companions.rigs import load_all
from app.core.classifier import classify
from app.social.workflow import EditorialStore, WorkflowError
from app.operations.inbox import Inbox
from app.fleet.liu_bei_preflight import liu_bei_a0_preflight
from app.fleet.liu_bei_variant_preflight import liu_bei_variant_preflight
from app.fleet.liu_bei_runtime import runtime_projection, STATES as LIU_BEI_REVIEW_STATES
from app.fleet.liu_bei_33_review import phase10_projection, validate_library as validate_liu_bei_33
from app.fleet.liu_bei_watcher import LiuBeiA0Watcher
from app.automation.local_llm import OllamaBackend, LocalModelError
from app.automation.public_web import PublicWebResearcher, ResearchError, evidence_prompt
from app.automation.configured_web import ConfiguredWebRunner, WebAdapterError

settings = Settings()
cache = SpeedrunnerCache(settings.database)
archive = CrystalArchives(settings.database, settings.index_root, dense=__import__("app.config", fromlist=["enabled"]).enabled("DENSE_SEARCH"))
events = EventLog()
router = Router(settings, archive, cache, events)
chatgpt_tasks=ChatGPTSubmissionBridge(router.sessions,max_tabs=2,start_spacing=1.5)
model_instructions=InstructionStore(settings.root/'session_data'/'model_instructions.json')
director = CompanionDirector(settings.root, events)
social = EditorialStore(settings.root / "app_data" / "editorial.sqlite")
inbox=Inbox(settings.root/'app_data'/'companion_tasks.sqlite')
inbox.fail_interrupted()
liu_bei_a0_watcher=LiuBeiA0Watcher(settings.root,events)
local_model=OllamaBackend()
researcher=PublicWebResearcher()
web_adapters={slot:ConfiguredWebRunner(settings.root,slot=slot)
              for slot in ("custom_web","web_slot_2","web_slot_3")}
web_adapter=web_adapters["custom_web"]  # first-slot compatibility
active_generations=set()
active_command_jobs={}

def schedule_command_job(task_id, coroutine):
    """Track a task's cancellable local orchestration; not a remote stop guarantee."""
    job=asyncio.create_task(coroutine)
    active_generations.add(job)
    active_command_jobs[task_id]=job
    def release(done):
        active_generations.discard(done)
        if active_command_jobs.get(task_id) is done:
            active_command_jobs.pop(task_id,None)
    job.add_done_callback(release)
    return job

started = monotonic()
app = FastAPI(title='Exodia Tower', version=APP_VERSION, docs_url='/api/docs')

@app.exception_handler(sqlite3.DatabaseError)
async def sqlite_command_storage_boundary(request: Request, error: sqlite3.DatabaseError):
    """Never return raw database exceptions, SQL text, local paths or secrets."""
    events.publish('alert','Local SQLite command storage unavailable','sqlite_database_error')
    return JSONResponse(status_code=503,content={
        'detail':'Local task storage unavailable; inspect SQLite health and local logs.',
        'code':'sqlite_storage_unavailable'})

app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
app.mount('/assets', StaticFiles(directory=settings.root/'frontend'), name='assets')
(settings.root/'app_data'/'artifacts').mkdir(parents=True,exist_ok=True)
app.mount('/artifacts',StaticFiles(directory=settings.root/'app_data'/'artifacts'),name='artifacts')
events.publish('system', 'Exodia Tower boot sequence complete', 'Local mode active')

class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    channel: str = Field(default='auto', pattern='^(auto|api|browser|local)$')
    model_choice: str = Field(default='chatgpt', pattern=r'^(chatgpt|gemini|deepseek|ollama|chatgpt:api|gemini:api|deepseek:api)$')
    transport: str | None = Field(default=None, pattern=r'^(browser|local|api)$')

async def run_stale_task_cleanup_once():
    """Expire inactive local tasks without claiming remote provider cancellation."""
    stale=inbox.cleanup_stale(maximum_idle_seconds=3600)
    for task_id in stale:
        job=active_command_jobs.get(task_id)
        if job is not None and not job.done():
            job.cancel()
    if stale:
        events.publish('task','Stale local task recovery',f"expired_count:{len(stale)}")
    return stale

async def _task_cleanup_watchdog():
    while True:
        try:
            await run_stale_task_cleanup_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            events.publish('alert','Task cleanup check failed','Inspect local SQLite health')
        await asyncio.sleep(120)

@app.on_event('startup')
async def start_task_cleanup_watchdog():
    if getattr(app.state,'task_cleanup_watchdog',None) is None:
        app.state.task_cleanup_watchdog=asyncio.create_task(_task_cleanup_watchdog())
    liu_bei_a0_watcher.start()

@app.on_event('shutdown')
async def stop_browser_sessions():
    await liu_bei_a0_watcher.stop()
    watcher=getattr(app.state,'task_cleanup_watchdog',None)
    if watcher is not None:
        watcher.cancel()
        try:await watcher
        except asyncio.CancelledError:pass
        app.state.task_cleanup_watchdog=None
    await chatgpt_tasks.close()
    await router.close_sessions()
    await asyncio.gather(*(runner.close() for runner in web_adapters.values()))

@app.get('/api/build-info')
async def api_build_info():
    return build_info()

@app.get('/')
async def home():
    return FileResponse(settings.root/'frontend'/'albedo_command.html')

@app.get('/operations-legacy')
async def operations_legacy():
    return FileResponse(settings.root/'frontend'/'exodia_workstations.html')

@app.get('/automation-demo')
async def automation_demo():
    return FileResponse(settings.root/'frontend'/'automation_demo.html')

@app.get('/art-studio')
async def art_studio():
    return FileResponse(settings.root/'frontend'/'kiko_art_lab.html')

@app.get('/companion-art-qa')
async def companion_art_qa():
    return FileResponse(settings.root/'frontend'/'companion_art_qa.html')

@app.get('/puppet-lab')
async def puppet_lab():
    return FileResponse(settings.root/'frontend'/'puppet_lab.html')


# Owner-local, unapproved five-state artwork review. This does not mutate the
# production portrait registry and does not dispatch an AI provider task.
@app.get('/core5-review')
async def albedo_core5_review():
    return FileResponse(settings.root/'frontend'/'core5_review_workbench.html')

@app.get('/api/albedo/core5/review-manifest')
async def albedo_core5_review_manifest():
    from app.companions.core5_review_assets import current_manifest
    return current_manifest(settings.root)

@app.get('/api/albedo/core5/review-assets/{state}')
async def albedo_core5_review_asset(state: str):
    from app.companions.core5_review_assets import local_asset
    file=local_asset(settings.root,state)
    if not file:
        raise HTTPException(404,detail='Unverified or missing Core-Five review image')
    return FileResponse(file,media_type='image/png',headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@app.post('/api/albedo/core5/review-import')
async def albedo_core5_review_import(request: Request,
                                     x_exodia_client:str=Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(403,detail='Local operator authorization required')
    if request.headers.get('content-type','').split(';')[0] not in (
        'application/zip','application/octet-stream'):
        raise HTTPException(415,detail='Upload the actual Gate 1 review ZIP')
    from app.companions.core5_review_assets import import_review_zip,MAX_BUNDLE
    if int(request.headers.get('content-length','0') or '0')>MAX_BUNDLE:
        raise HTTPException(413,detail='Review archive exceeds 65 MiB')
    payload=await request.body()
    if len(payload)>MAX_BUNDLE:raise HTTPException(413,detail='Review archive too large')
    try:
        return await asyncio.to_thread(import_review_zip,settings.root,payload)
    except (ValueError, OSError) as exc:
        raise HTTPException(422,detail=str(exc)) from exc


# Gate 3 / 33-state DEVELOPMENT workbench: never modifies production portrait
# registry, owner sign-offs, the live provider task system or 28-state release.
@app.get('/test-workbench')
@app.get('/state33-review')
async def albedo_state33_review_workbench():
    return FileResponse(settings.root/'frontend'/'test_workbench.html')

@app.get('/api/albedo/state33/manifest')
async def albedo_state33_review_manifest():
    from app.companions.state33_review_assets import manifest
    return manifest(settings.root)

@app.get('/api/albedo/state33/review-assets/{state}')
async def albedo_state33_review_png(state: str):
    from app.companions.state33_review_assets import asset
    file = asset(settings.root, state)
    if file is None:
        raise HTTPException(404,detail='Pending or unverified state artwork')
    return FileResponse(file,media_type='image/png',headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@app.post('/api/albedo/state33/review-import')
async def albedo_state33_review_import(request: Request,
                                        x_exodia_client: str=Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(403,detail='Local operator confirmation required')
    if request.headers.get('content-type','').split(';')[0] not in (
        'application/zip','application/octet-stream'):
        raise HTTPException(415,detail='A state33 review ZIP is required')
    from app.companions.state33_review_assets import import_art,MAX_COMPRESSED
    if int(request.headers.get('content-length','0') or '0')>MAX_COMPRESSED:
        raise HTTPException(413,detail='Review archive exceeds limit')
    body = await request.body()
    if len(body)>MAX_COMPRESSED:
        raise HTTPException(413,detail='Review archive exceeds limit')
    try:
        return await asyncio.to_thread(import_art,settings.root,body)
    except (ValueError,OSError,KeyError) as exc:
        raise HTTPException(422,detail=str(exc)) from exc

@app.post('/api/albedo/state33/gate4-four-correction-import')
async def albedo_gate4_owner_targeted_four_import(request: Request,
                                                   x_exodia_client: str=Header(default='')):
    """Only four independent newly rendered PNG originals can replace old art.

    This is a review-only transaction, never production approval. The 29
    owner-accepted states are checked against their immutable SHA-256 lock.
    """
    if x_exodia_client != 'exodia-dashboard':
        raise HTTPException(403, detail='Local operator confirmation required')
    if request.headers.get('content-type', '').split(';')[0] not in (
            'application/zip', 'application/octet-stream'):
        raise HTTPException(415, detail='Four individual original PNGs in ZIP required')
    from tools.apply_gate4_four_corrections import apply, MAX_ARCHIVE_BYTES
    if int(request.headers.get('content-length','0') or '0') > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, detail='Four-portrait correction ZIP exceeds limit')
    body = await request.body()
    if not body or len(body) > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, detail='Four-portrait correction ZIP exceeds limit')
    import tempfile
    with tempfile.NamedTemporaryFile(prefix='exodia_gate4_four_',suffix='.zip',
                                     delete=False) as file:
        file.write(body)
        temp_path = Path(file.name)
    try:
        report = await asyncio.to_thread(apply, settings.root.parent, temp_path)
    except (ValueError, OSError, KeyError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)
    return report


# Gate 4: owner-accepted visual designs are 1122x1402 source originals.
# This separate import route explicitly creates DEVELOPMENT-ONLY presentation
# resamples; the existing native-production intake remains strict/unmodified.
@app.post('/api/albedo/state33/gate4-four-review-import')
async def albedo_gate4_four_review_only_import(request: Request,
                                               x_exodia_client: str=Header(default='')):
    if x_exodia_client != 'exodia-dashboard':
        raise HTTPException(403,detail='Local operator confirmation required')
    if request.headers.get('content-type','').split(';')[0] not in (
            'application/zip','application/octet-stream'):
        raise HTTPException(415,detail='Four-state resampled-review ZIP required')
    from tools.apply_gate4_four_review_only import apply,MAX_ARCHIVE_BYTES
    from zipfile import BadZipFile
    if int(request.headers.get('content-length','0') or '0') > MAX_ARCHIVE_BYTES:
        raise HTTPException(413,detail='Review-only archive exceeds limit')
    body=await request.body()
    if not body or len(body)>MAX_ARCHIVE_BYTES:
        raise HTTPException(413,detail='Review-only archive exceeds limit')
    try:
        return await asyncio.to_thread(apply,settings.root.parent,body)
    except (ValueError,OSError,KeyError,BadZipFile) as exc:
        raise HTTPException(422,detail=str(exc)) from exc


@app.post('/api/albedo/state33/gate4-four-review-rollback')
async def albedo_gate4_four_review_only_rollback(
        x_exodia_client: str=Header(default='')):
    if x_exodia_client != 'exodia-dashboard':
        raise HTTPException(403,detail='Local operator confirmation required')
    from tools.apply_gate4_four_review_only import rollback
    try:
        return await asyncio.to_thread(rollback,settings.root.parent)
    except (ValueError,OSError,KeyError) as exc:
        raise HTTPException(422,detail=str(exc)) from exc


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


# Optional Kokoro localhost neural voice: never proxies arbitrary remote hosts.
KOKORO_URL='http://127.0.0.1:8880/v1/audio/speech'
VOICE_IDS={'kiko':'af_heart','liu_bei':'am_michael','mira':'af_bella',
 'lyra':'bf_emma','pip':'af_kore','aurelia':'bf_isabella',
 'nyx':'am_fenrir','mochi':'af_sky','orion':'bm_george','nova':'af_nova'}

class CompanionSpeech(BaseModel):
    agent_id: str = Field(pattern=r'^[a-z_]{2,25}$')
    text: str = Field(min_length=1,max_length=1500)

@app.get('/api/voice/status')
async def local_voice_status():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response=await client.get('http://127.0.0.1:8880/v1/models')
        ready=response.status_code==200
        return {'engine':'kokoro','available':ready,'voices':VOICE_IDS if ready else {}}
    except httpx.HTTPError:
        return {'engine':'kokoro','available':False,'voices':{}}

@app.post('/api/voice/speak')
async def companion_neural_speech(body:CompanionSpeech,
                                  x_exodia_client:str=Header(default='')):
    if x_exodia_client!='exodia-dashboard':
        raise HTTPException(403,detail='Local dashboard required')
    if body.agent_id not in VOICE_IDS:
        raise HTTPException(422,detail='Unknown companion')
    spoken=' '.join(body.text.split())[:1000]
    if not spoken:
        raise HTTPException(422,detail='No spoken text')
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0,connect=2.0)) as client:
            response=await client.post(KOKORO_URL,json={
              'model':'kokoro','voice':VOICE_IDS[body.agent_id],
              'input':spoken,'response_format':'mp3','speed':1.05})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(503,detail='Natural voice service unavailable. Start local Kokoro on 127.0.0.1:8880.') from exc
    if len(response.content)>8*1024*1024:
        raise HTTPException(502,detail='Voice audio too large')
    mime=response.headers.get('content-type','audio/mpeg').split(';')[0]
    if mime not in ('audio/mpeg','audio/mp3','audio/wav','audio/x-wav'):
        raise HTTPException(502,detail='Voice service returned invalid media type')
    return Response(response.content,media_type='audio/mpeg' if mime=='audio/mp3' else mime,
                    headers={'Cache-Control':'no-store'})

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
    return {'models':router.sessions.snapshot(),
            'automatic_extraction':{'gemini':True,'chatgpt':True,'deepseek':True},
             'chatgpt_bridge':chatgpt_tasks.snapshot()}

@app.post('/api/web/sessions/{model_choice}/start')
async def start_one_web_session(model_choice:str,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    if model_choice not in PROVIDERS:raise HTTPException(422,detail='Unknown browser provider')
    try:return {'model':model_choice,
                'session':await router.sessions.initialize_one(model_choice)}
    except SessionError as exc:raise HTTPException(503,detail=str(exc)) from exc

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
    try: chosen = selection(body.model_choice, body.transport)
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc
    if body.channel == 'api':
        raise HTTPException(409, detail='Official API transport is not configured. Select a chronos or Ollama model.')
    if chosen.transport == 'local':
        try:
            output = await local_model.generate(body.question.strip(), companion='kiko')
        except (LocalModelError, ValueError) as exc:
            raise HTTPException(503, detail=str(exc)) from exc
        return {'answer':output['answer'], 'route':'local', 'status':'complete',
                'data':{'model':output['model'], 'provider_id':'ollama', 'transport':'local'},
                'cache_hit':False, 'latency_ms':0}
    if body.channel == 'browser': kind='browser'
    elif body.channel == 'local': kind='rag'
    elif body.channel == 'api': kind='reasoning'
    else: kind,_=classify(body.question.strip())
    specialist={'browser':'ninja','rag':'archives','integration':'inventory','system':'strategy','reasoning':'memory'}.get(kind,'liu_bei')
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
    model_choice:str=Field(pattern=r'^(ollama|custom_web|web_slot_2|web_slot_3|chatgpt|gemini|deepseek|chatgpt:api|gemini:api|deepseek:api)$')
    transport:str|None=Field(default=None, pattern=r'^(browser|local|api)$')
    agent_id:str=Field(min_length=1,max_length=64)
    web_research:bool=False
    custom_instructions:str=Field(
        default='',
        max_length=4000,
        description=(
            'Optional directions for this task only, such as a theme or character limit. '
            'Sent to ChatGPT, Gemini, or DeepSeek together with that model\'s saved instructions. '
            'Never included in the created task or later task responses.'
        ),
    )
class CompanionTaskAnswer(BaseModel):
    answer:str=Field(min_length=1,max_length=100000)

class TaskRetryBody(BaseModel):
    # Explicit operator consent is required for browser transports because the
    # old consumer-site request may still be processing after local cancellation.
    confirm_external_redelivery:bool=False

async def _complete_local_task(task_id: str):
    """Run local inference asynchronously; task state is always persisted."""
    try:
        t=inbox.get(task_id)
        prompt=compose_model_prompt(t['prompt'], t.get('private_instructions',''))
        if t['web_research']:
            director.react(t['agent_id'],'working')
            results=await researcher.gather(prompt)
            inbox.update(task_id,'sources',[{'title':x.title,'url':x.url} for x in results])
            inbox.update(task_id,'state','running')
            events.publish('task','Companion completed source collection',
                           f"{t['agent_id']}:public_web:{len(results)}")
            prompt=evidence_prompt(prompt,results)
        result=await local_model.generate(prompt,companion=t['agent_id'])
        inbox.update(task_id,'answer',result['answer'])
        inbox.update(task_id,'state','answered')
        director.react(t['agent_id'],'success')
        events.publish('success','Companion received autonomous model response',
                       f"{t['agent_id']}:ollama")
    except Exception as exc:
        # Never record a failed inference as a successful answer.
        message=str(exc) if isinstance(exc,(LocalModelError,ResearchError,ValueError)) else             'Unexpected local inference error. Check Exodia logs.'
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(t['agent_id'],'alert')
        events.publish('alert','Companion inference failed',f"{t['agent_id']}:ollama")

async def _complete_web_task(task_id: str):
    """All task execution, streaming and companion delivery in one background job."""
    task=inbox.get(task_id)
    def on_phase(state):
        inbox.update(task_id,'state',state)
        events.publish('task','Configured web workflow',f"{task['agent_id']}:{state}")
    try:
        result=await web_adapters[task['provider']].run(compose_model_prompt(task['prompt'], task.get('private_instructions','')),phase=on_phase)
        inbox.update(task_id,'answer',result['answer'])
        inbox.update(task_id,'state','answered')
        director.react(task['agent_id'],'success')
        events.publish('success','Browser output delivered to companion',
                       f"{task['agent_id']}:configured_web")
    except Exception as exc:
        message=str(exc) if isinstance(exc,(WebAdapterError,ValueError)) else (
            'Unexpected configured browser error; review debug snapshots.')
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(task['agent_id'],'alert')
        events.publish('alert','Configured browser workflow failed',
                       f"{task['agent_id']}:configured_web")

async def _submit_chatgpt_task(task_id: str):
    """Send a task to ChatGPT and wait until the visible reply has finished."""
    task=inbox.get(task_id)
    def on_phase(stage):
        inbox.update(task_id,'state',stage)
        director.react(task['agent_id'],'working')
        events.publish('task','ChatGPT browser automation',f"{task['agent_id']}:{stage}")
    try:
        result=await chatgpt_tasks.submit(task_id,compose_model_prompt(task['prompt'], task.get('private_instructions','')),phase=on_phase)
        if isinstance(result.get('timings'),dict):
            inbox.update(task_id,'metrics',result['timings'])
        if result.get('media'):
            inbox.update(task_id,'media',result['media'])
            first_image=next((m for m in result['media']
                              if m.get('kind')=='image' and m.get('url')),None)
            if first_image:inbox.update(task_id,'artifact',first_image['url'])
        inbox.update(task_id,'answer',result['answer'])
        inbox.update(task_id,'state','answered')
        director.react(task['agent_id'],'success')
        events.publish('success','ChatGPT response delivered to companion',
                       f"{task['agent_id']}:chatgpt")
    except Exception as exc:
        message=str(exc) if isinstance(exc,(SessionError,ValueError)) else (
            'ChatGPT browser task failed; inspect its window and screenshots.')
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(task['agent_id'],'alert')
        events.publish('alert','ChatGPT browser task failed',
                       f"{task['agent_id']}:chatgpt")

async def _complete_gemini_task(task_id: str):
    """Gemini browser roundtrip, tied to companion task-state lifecycle."""
    task=inbox.get(task_id)
    def on_phase(stage):
        inbox.update(task_id,'state',stage)
        director.react(task['agent_id'],'working')
        events.publish('task','Gemini browser task progress',
                       f"{task['agent_id']}:{stage}")
    try:
        output=await router.sessions.send_prompt_robust(
            'gemini',compose_model_prompt(task['prompt'], task.get('private_instructions','')),phase=on_phase)
        if isinstance(output.get('timings'),dict):
            inbox.update(task_id,'metrics',output['timings'])
        if output.get('media'):
            inbox.update(task_id,'media',output['media'])
            first_image=next((m for m in output['media']
                              if m.get('kind')=='image' and m.get('url')),None)
            if first_image:inbox.update(task_id,'artifact',first_image['url'])
        inbox.update(task_id,'answer',output['answer'])
        inbox.update(task_id,'state','answered')
        director.react(task['agent_id'],'success')
        events.publish('success','Gemini response delivered to companion',
                       f"{task['agent_id']}:gemini")
    except Exception as exc:
        message=str(exc) if isinstance(exc,(SessionError,ValueError)) else (
            "Gemini automation failed. Inspect the browser and local debug screenshots.")
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(task['agent_id'],'alert')
        events.publish('alert','Gemini browser task failed',f"{task['agent_id']}:gemini")

async def _complete_deepseek_task(task_id: str):
    """DeepSeek browser roundtrip, using the same visible-browser steps as Gemini."""
    task=inbox.get(task_id)
    def on_phase(stage):
        inbox.update(task_id,'state',stage)
        director.react(task['agent_id'],'working')
        events.publish('task','DeepSeek browser task progress',
                       f"{task['agent_id']}:{stage}")
    try:
        output=await router.sessions.send_prompt_robust(
            'deepseek',compose_model_prompt(task['prompt'], task.get('private_instructions','')),phase=on_phase)
        if isinstance(output.get('timings'),dict):
            inbox.update(task_id,'metrics',output['timings'])
        if output.get('media'):
            inbox.update(task_id,'media',output['media'])
            first_image=next((m for m in output['media']
                              if m.get('kind')=='image' and m.get('url')),None)
            if first_image:inbox.update(task_id,'artifact',first_image['url'])
        inbox.update(task_id,'answer',output['answer'])
        inbox.update(task_id,'state','answered')
        director.react(task['agent_id'],'success')
        events.publish('success','DeepSeek response delivered to companion',
                       f"{task['agent_id']}:deepseek")
    except Exception as exc:
        message=str(exc) if isinstance(exc,(SessionError,ValueError)) else (
            "DeepSeek automation failed. Inspect the browser and local debug screenshots.")
        inbox.update(task_id,'error',message[:700])
        inbox.update(task_id,'state','failed')
        director.react(task['agent_id'],'alert')
        events.publish('alert','DeepSeek browser task failed',f"{task['agent_id']}:deepseek")


@app.get('/api/command/model-options')
async def command_model_options():
    return public_catalog()

@app.get('/api/command/providers')
async def command_providers():
    return {'model_options':public_catalog(), 'ollama':await local_model.status(),
            'configured_web':web_adapter.snapshot(),
            'configured_slots':{key:runner.snapshot() for key,runner in web_adapters.items()},
             'chatgpt':chatgpt_tasks.snapshot(),
            'gemini':router.sessions.snapshot()['gemini'],
            'website_workspaces':'gemini_auto;chatgpt_auto;deepseek_auto'}

@app.get('/api/command/tasks')
async def command_list():
    return {'tasks':[public_task(task) for task in inbox.list()],'sessions':router.sessions.snapshot(),
            'automatic_extraction':{'gemini':True,'chatgpt':True,'deepseek':True}}

@app.post(
    '/api/command/tasks',
    status_code=201,
    summary='Create a model task',
    description=(
        'Send a prompt to the selected model. custom_instructions is optional and is delivered '
        'only to ChatGPT, Gemini, or DeepSeek, after any instructions saved for that model. '
        'This response, GET /api/command/tasks, and later task updates return the original prompt '
        'and the answer. They omit custom_instructions and private_instructions. '
        'See docs/MODEL_INSTRUCTIONS.md.'
    ),
)
async def command_create(body:CompanionTaskBody,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try: chosen = selection(body.model_choice, body.transport)
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc
    if body.agent_id not in director.known:raise HTTPException(422,detail='Unknown companion')
    if body.web_research and body.model_choice!='ollama':
        raise HTTPException(422,detail='Public research currently requires Ollama. Disable that option for configured browser tasks.')
    if body.model_choice in web_adapters and not web_adapters[body.model_choice].snapshot()['configured']:
        raise HTTPException(422,detail=body.model_choice+' is unconfigured. Copy examples/custom_web.example.json to session_data/'+body.model_choice+'.json and restart.')
    try:
        saved_text=model_instructions.text_for(chosen.provider_id) if chosen.provider_id in BROWSER_MODELS else ''
        private=combine_instructions(saved_text, body.custom_instructions)
        if private: compose_model_prompt(body.prompt, private)
        t=inbox.create(body.agent_id,chosen.provider_id,body.prompt,web_research=body.web_research,private_instructions=private)
    except ValueError as e:raise HTTPException(422,detail=str(e))
    if body.model_choice=='ollama':
        t=inbox.update(t['id'],'state','researching' if body.web_research else 'running')
        director.react(body.agent_id,'working')
        schedule_command_job(t['id'],_complete_local_task(t['id']))
        events.publish('task','Autonomous companion '+('live research' if body.web_research else 'inference')+' started',f"{body.agent_id}:ollama")
    elif body.model_choice in web_adapters:
        t=inbox.update(t['id'],'state','opening')
        director.react(body.agent_id,'working')
        schedule_command_job(t['id'],_complete_web_task(t['id']))
        events.publish('task','Autonomous configured website task started',
                       f"{body.agent_id}:custom_web")
    elif body.model_choice=='gemini':
        t=inbox.update(t['id'],'state','opening')
        director.react(body.agent_id,'working')
        schedule_command_job(t['id'],_complete_gemini_task(t['id']))
        events.publish('task','Gemini browser task started',f"{body.agent_id}:gemini")
    elif body.model_choice=='deepseek':
        t=inbox.update(t['id'],'state','opening')
        director.react(body.agent_id,'working')
        schedule_command_job(t['id'],_complete_deepseek_task(t['id']))
        events.publish('task','DeepSeek browser task started',f"{body.agent_id}:deepseek")
    elif body.model_choice=='chatgpt':
        t=inbox.update(t['id'],'state','opening')
        director.react(body.agent_id,'working')
        schedule_command_job(t['id'],_submit_chatgpt_task(t['id']))
        events.publish('task','ChatGPT browser prompt dispatch started',
                       f"{body.agent_id}:chatgpt")
    else:
        director.react(body.agent_id,'thinking')
        events.publish('task','Manual website task created',f"{body.agent_id}:{body.model_choice}")
    return public_task(t)

@app.get(
    '/api/command/model-instructions',
    summary='Read saved model instructions',
    description=(
        'Return the standing instructions saved for ChatGPT, Gemini, and DeepSeek. '
        'This editor endpoint returns the saved text. Task responses do not.'
    ),
)
async def read_model_instructions(x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    saved=model_instructions.read()
    return {'models':[{'provider':name,'text':saved[name]} for name in BROWSER_MODELS]}

class ModelInstructionBody(BaseModel):
    provider:str=Field(pattern=r'^(chatgpt|gemini|deepseek)$', description='chatgpt, gemini, or deepseek')
    text:str=Field(
        default='',
        max_length=4000,
        description='Standing instructions for this model. Empty clears them. Not returned on task responses.',
    )

@app.put(
    '/api/command/model-instructions',
    summary='Save model instructions',
    description=(
        'Replace the standing instructions for one browser model. The saved text is sent with '
        'later tasks for that model and is returned by this settings endpoint. '
        'Task create and task list responses still omit it.'
    ),
)
async def write_model_instructions(body:ModelInstructionBody,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:saved=model_instructions.save(body.provider, body.text)
    except ValueError as exc:raise HTTPException(422,detail=str(exc)) from exc
    return {'models':[{'provider':name,'text':saved[name]} for name in BROWSER_MODELS]}

@app.get('/api/fleet/liu_bei/33-review')
async def liu_bei_33_review_status(task_id: str | None = None,
                                  preview_state: str | None = None,
                                  x_exodia_client: str = Header(default='')):
    """Task-bound, read-only 33-state vocabulary review; never serves state art."""
    require_local_dashboard(x_exodia_client)
    if preview_state is not None:
        try:
            _manifest, canonical = await asyncio.to_thread(validate_liu_bei_33, settings.root)
        except Exception:
            raise HTTPException(503, detail='Liu Bei canonical review unavailable')
        if preview_state not in canonical:
            raise HTTPException(422, detail='Unsupported canonical preview state')
    task = None
    if task_id is not None:
        if len(task_id) > 128 or re.fullmatch(r'[0-9a-zA-Z-]+', task_id) is None:
            raise HTTPException(422, detail='Invalid task identifier')
        try:
            task = inbox.get(task_id)
        except KeyError:
            raise HTTPException(404, detail='Task not found')
        if task.get('agent_id') != 'liu_bei':
            raise HTTPException(409, detail='Selected task belongs to another companion')
    try:
        return await asyncio.to_thread(
            phase10_projection, settings.root, task=task, preview_state=preview_state)
    except Exception:
        events.publish('alert', 'Liu Bei 33-state review unavailable',
                       'liu_bei_33_read_only_contract_error')
        raise HTTPException(503, detail='Liu Bei 33-state review unavailable')


@app.get('/api/fleet/liu_bei/pilot-runtime')
async def liu_bei_pilot_runtime(task_id: str | None = None, preview_state: str | None = None,
                              x_exodia_client: str = Header(default='')):
    """Live command-center Liu Bei review state; never a native image URL or approval."""
    require_local_dashboard(x_exodia_client)
    if preview_state is not None and preview_state not in LIU_BEI_REVIEW_STATES:
        raise HTTPException(422, detail='Unsupported Liu Bei review state')
    task = None
    if task_id is not None:
        if len(task_id) > 128 or re.fullmatch(r'[0-9a-zA-Z-]+',task_id) is None:
            raise HTTPException(422, detail='Invalid task identifier')
        try: task = inbox.get(task_id)
        except KeyError: raise HTTPException(404, detail='Task not found')
        if task.get('agent_id') != 'liu_bei':
            raise HTTPException(409, detail='Selected task belongs to another companion')
    try:
        return await asyncio.to_thread(
            runtime_projection, settings.root, task=task, manual_preview=preview_state)
    except Exception:
        # Never leak source or reference paths, hashes, local exceptions,
        # browser sessions, or anything from the private task store.
        events.publish('alert', 'Liu Bei review pilot unavailable',
                       'liu_bei_review_policy_failure')
        raise HTTPException(503, detail='Liu Bei review pilot is not available')

@app.get('/api/fleet/liu_bei/variant-preflight')
async def liu_bei_variant_preflight_status(x_exodia_client: str=Header(default='')):
    """Local-only review of four independent candidate PNGs; never registers art."""
    require_local_dashboard(x_exodia_client)
    try:
        return await asyncio.to_thread(liu_bei_variant_preflight, settings.root)
    except Exception:
        # Source paths, annotations and raw errors never leave local preflight.
        events.publish('alert','Liu Bei variant preflight unavailable','liu_bei_variant_policy_error')
        raise HTTPException(503,detail='Liu Bei variant preflight unavailable')


@app.get('/api/fleet/liu_bei-a0/watch-status')
async def liu_bei_watch_status(x_exodia_client: str=Header(default='')):
    """Safe, non-secret live watcher snapshot; requires local dashboard access."""
    require_local_dashboard(x_exodia_client)
    return liu_bei_a0_watcher.snapshot()

@app.get('/api/fleet/liu_bei-a0/preflight')
async def liu_bei_a0_preflight_status(x_exodia_client: str=Header(default='')):
    """Local-only read-only Phase 5 status; never auto-register or release artwork."""
    require_local_dashboard(x_exodia_client)
    try:
        return await asyncio.to_thread(liu_bei_a0_preflight,settings.root)
    except Exception:
        # Unknown local file names, hashes, annotations, paths and exception
        # messages must never appear in response telemetry or remote logs.
        events.publish('alert','Liu Bei A0 preflight check unavailable','liu_bei_a0_preflight_error')
        raise HTTPException(503,detail='Liu Bei A0 preflight unavailable; review the local intake gate')

@app.get('/api/fleet/readiness')
async def fleet_review_readiness(selected_agent: str = 'kiko', task_id: str | None = None,
                                 x_exodia_client: str = Header(default='')):
    """Read-only ten-companion engineering status, never provider/art mutation."""
    require_local_dashboard(x_exodia_client)
    from app.fleet import fleet_readiness as fleet_service
    if selected_agent not in fleet_service.EXPECTED_IDS:
        raise HTTPException(422, detail='Unknown EXODIA companion')
    task = None
    if task_id is not None:
        if len(task_id) > 128 or re.fullmatch(r'[A-Za-z0-9-]+', task_id) is None:
            raise HTTPException(422, detail='Invalid task identifier')
        try:
            task = inbox.get(task_id)
        except KeyError:
            raise HTTPException(404, detail='Task not found')
        if task.get('agent_id') != selected_agent:
            raise HTTPException(409, detail='Selected task belongs to another companion')
    try:
        return await asyncio.to_thread(
            fleet_service.fleet_projection, settings.root, selected_agent=selected_agent, task=task)
    except Exception:
        events.publish('alert', 'Fleet state readiness unavailable',
                       'fleet_review_immutable_contract_error')
        raise HTTPException(503, detail='Fleet state review unavailable')


@app.get('/api/command/history-health')
async def command_history_health(x_exodia_client: str=Header(default='')):
    """Local-only, aggregate, read-only SQLite status with no sensitive rows."""
    require_local_dashboard(x_exodia_client)
    return await asyncio.to_thread(inbox.history_health)

@app.get('/api/command/tasks/history')
async def command_history(limit:int=50,offset:int=0,x_exodia_client:str=Header(default='')):
    """Paginated history from durable SQLite, including linked retry attempts."""
    require_local_dashboard(x_exodia_client)
    try:page=inbox.list_page(limit,offset)
    except ValueError as exc:raise HTTPException(422,detail=str(exc)) from exc
    return {**page,'tasks':[public_task(task) for task in page['tasks']]}

@app.get('/api/command/tasks/{task_id}/events')
async def command_task_events(task_id:str,x_exodia_client:str=Header(default='')):
    """Return sanitized state transitions only: no prompt/private instructions."""
    require_local_dashboard(x_exodia_client)
    try:timeline=inbox.events(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    return {'task_id':task_id,'events':timeline}

@app.post('/api/command/tasks/{task_id}/retry',status_code=201)
async def command_retry(task_id:str,body:TaskRetryBody,
                        x_exodia_client:str=Header(default='')):
    """A deliberate, bounded retry creates a linked new task, never replays blindly.

    Browser redelivery needs an explicit true flag; duplicated HTTP calls return
    the already-created successor. No official API choice is silently substituted.
    """
    require_local_dashboard(x_exodia_client)
    try:source=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    provider=source['provider']
    if provider!='ollama' and not body.confirm_external_redelivery:
        raise HTTPException(409,detail=(
            'External resend requires confirm_external_redelivery=true; '
            'the previous browser-site request may still finish remotely.'))
    if provider in web_adapters and not web_adapters[provider].snapshot()['configured']:
        raise HTTPException(422,detail='Original configured browser transport is not available')
    try:next_task,created=inbox.retry(task_id,max_retries=3)
    except ValueError as exc:raise HTTPException(409,detail=str(exc)) from exc
    # If a process crashed after the durable retry row was inserted but before
    # the job was scheduled, an explicit repeat of the same POST resumes that
    # still-draft attempt. Never resend a task that reached 'opening' or later.
    if not created and (next_task['state']!='draft' or
                        next_task['id'] in active_command_jobs):
        return public_task(next_task)
    try:
        if provider=='ollama':
            next_task=inbox.update(next_task['id'],'state',
                                   'researching' if next_task['web_research'] else 'running')
            schedule_command_job(next_task['id'],_complete_local_task(next_task['id']))
        elif provider in web_adapters:
            next_task=inbox.update(next_task['id'],'state','opening')
            schedule_command_job(next_task['id'],_complete_web_task(next_task['id']))
        elif provider=='chatgpt':
            next_task=inbox.update(next_task['id'],'state','opening')
            schedule_command_job(next_task['id'],_submit_chatgpt_task(next_task['id']))
        elif provider=='gemini':
            next_task=inbox.update(next_task['id'],'state','opening')
            schedule_command_job(next_task['id'],_complete_gemini_task(next_task['id']))
        elif provider=='deepseek':
            next_task=inbox.update(next_task['id'],'state','opening')
            schedule_command_job(next_task['id'],_complete_deepseek_task(next_task['id']))
        else:
            inbox.update(next_task['id'],'error','Original provider is no longer supported')
            next_task=inbox.update(next_task['id'],'state','failed')
    except Exception:
        # The attempt remains auditable even if its local dispatch cannot start.
        try:
            inbox.update(next_task['id'],'error','Local retry scheduling failed')
            inbox.update(next_task['id'],'state','failed')
        except (ValueError,KeyError):pass
        raise HTTPException(503,detail='Local retry scheduling failed')
    events.publish('task','Operator-authorized model task retry',
                   f"{source['agent_id']}:{provider}:attempt{next_task['retry_index']}")
    return public_task(next_task)

@app.post('/api/command/tasks/{task_id}/prepare')
async def command_prepare(task_id:str,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:t=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    if t['provider'] in ('ollama','gemini','chatgpt','deepseek') or t['provider'] in web_adapters:raise HTTPException(409,detail='Automatic tasks start when created; browser preparation not required')
    if t['state']!='draft':raise HTTPException(409,detail='Already prepared')
    try:info=await router.models.generate(t['prompt'],t['provider'])
    except (SessionError,ValueError) as e:raise HTTPException(409,detail=str(e))
    saved=inbox.update(task_id,'state','awaiting_operator')
    director.react(t['agent_id'],'working')
    return {'task':public_task(saved),'instructions':info}

@app.post('/api/command/tasks/{task_id}/response')
async def command_response(task_id:str,body:CompanionTaskAnswer,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:t=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    if t['state']!='awaiting_operator':raise HTTPException(409,detail='Prepare the prompt first')
    try:
        if t['provider']=='chatgpt':
            await chatgpt_tasks.complete(task_id,body.answer)
        else:
            router.models.record_operator_response(t['provider'],body.answer)
    except (SessionError,ValueError) as e:raise HTTPException(409,detail=str(e))
    inbox.update(task_id,'answer',body.answer.strip())
    saved=inbox.update(task_id,'state','answered')
    director.react(t['agent_id'],'success')
    events.publish('success','Operator-delivered response',f"{t['agent_id']}:{t['provider']}")
    return public_task(saved)

@app.post('/api/command/tasks/{task_id}/cancel')
async def command_cancel(task_id:str,x_exodia_client:str=Header(default='')):
    require_local_dashboard(x_exodia_client)
    try:task=inbox.get(task_id)
    except KeyError:raise HTTPException(404,detail='Task not found')
    try:saved=inbox.cancel(task_id)
    except ValueError as exc:raise HTTPException(409,detail=str(exc)) from exc
    # Local cancellation prevents late task results; consumer sites may keep
    # processing requests already submitted. This is not a remote revoke API.
    job=active_command_jobs.get(task_id)
    if job and not job.done():job.cancel()
    elif task['provider']=='chatgpt' and task['state']=='awaiting_operator':
        try:await chatgpt_tasks.cancel(task_id)
        except SessionError:pass
    # A different active task may still own this companion's working state.
    other_active=any(
        other_id!=task_id and not other_job.done()
        and inbox.get(other_id)['agent_id']==task['agent_id']
        and inbox.get(other_id)['state'] not in ('answered','failed','cancelled')
        for other_id,other_job in list(active_command_jobs.items())
    )
    if not other_active:director.react(task['agent_id'],'rest')
    events.publish('task','Local command task cancelled',f"{task['agent_id']}:{task['provider']}")
    return public_task(saved)

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
    return public_task(inbox.update(task_id,'artifact',f"/artifacts/{fname}"))
