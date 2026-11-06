/** Bind command task phases to the isolated operations-floor chibi sprite. */
import {AlbedoChibiController,validateChibiManifest} from './albedo_chibi_controller.mjs';
import {AlbedoChibiRenderer} from './albedo_chibi_renderer.mjs';
import {AlbedoRoomBehavior} from './albedo_room_behavior.mjs';

export async function startAlbedoChibi({doc=document,win=window,loadManifest=()=>fetch('/assets/albedo_chibi_manifest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Manifest unavailable');return r.json();})}={}){
  const root=doc.getElementById('chibiOperations');if(!root)return null;
  const status=doc.getElementById('chibiArtStatus');
  let controller,renderer,manifest;
  try{
    manifest=await loadManifest();validateChibiManifest(manifest);
    controller=new AlbedoChibiController(manifest);
    renderer=new AlbedoChibiRenderer(root,manifest);
  }catch(_){status.textContent='CHIBI FLOOR UNAVAILABLE · MANIFEST CHECK FAILED';root.dataset.ready='error';return null;}
  // Floor movement uses physical pixel aspect so diagonals do not cover extra
  // distance in wide responsive layouts or accelerate the walk cycle.
  const floor=root.querySelector('#chibiFloor');
  const measure=()=>{
    if(floor?.clientHeight>0&&floor?.clientWidth>0)controller.setFloorAspect(floor.clientWidth/floor.clientHeight);
  };
  measure();const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(measure):null;
  if(observer)observer.observe(floor);
  const comp=doc.getElementById('companion');
  const behavior=new AlbedoRoomBehavior(manifest,{selectedAgent:comp?.value||'kiko'});
  const cue=doc.createElement('span');cue.id='chibiBehaviorCue';
  cue.setAttribute('role','status');
  root.querySelector('#chibiZoneState')?.parentElement?.append(cue);
  const apply=decision=>{
    controller.dispatchTaskState(decision.state,decision.visible?'kiko':'offstage');
    root.dataset.behavior=decision.behavior;
    root.dataset.taskPhase=decision.state;
    cue.textContent=decision.visible?decision.cue:'Albedo off stage · another companion or task selected';
    renderer.draw(controller.snapshot());
  };
  const onTask=event=>{
    // Source emits public task ID/state/owner/revision only. No user text enters.
    const decision=behavior.ingest(event?.detail||{});
    if(decision.accepted)apply(decision);
  };
  const onCompanion=()=>apply(behavior.selectCompanion(comp?.value||'kiko'));
  win.addEventListener('exodia:command-task',onTask);
  comp?.addEventListener('change',onCompanion);
  const demo=typeof doc.querySelectorAll==='function'?doc.querySelectorAll('[data-chibi-go]'):root.querySelectorAll('[data-chibi-go]');
  for(const button of demo)button.addEventListener('click',()=>{
    if((comp?.value||'kiko')!=='kiko')return;
    controller.goToZone(button.dataset.chibiGo);renderer.draw(controller.snapshot());
  });
  const reduced=win.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false;
  let raf=0,previous=null;
  const render=now=>{
    const dt=previous===null?0:Math.max(0,(now-previous)/1000);previous=now;
    if(controller.enabled&&!controller.arrived){if(reduced)controller.finish();else controller.tick(dt);renderer.draw(controller.snapshot());}
    raf=win.requestAnimationFrame(render);
  };
  apply(behavior.snapshot());if(win.__exodiaLastPublicTaskState)onTask({detail:win.__exodiaLastPublicTaskState});
  raf=win.requestAnimationFrame(render);root.dataset.ready='1';
  const runtime={controller,renderer,behavior,stop(){win.cancelAnimationFrame(raf);win.removeEventListener('exodia:command-task',onTask);comp?.removeEventListener('change',onCompanion);observer?.disconnect();renderer.destroy();},update:apply};
  win.__exodiaChibiRuntime=runtime;
  return runtime;
}
if(typeof document!=='undefined')startAlbedoChibi();
