/** Bind ONLY public task metadata to Albedo's SHA-gated, eight-way floor controller. */
import {AlbedoChibiController,validateChibiManifest} from './albedo_chibi_controller.mjs';
import {AlbedoChibiRenderer} from './albedo_chibi_renderer.mjs';
import {AlbedoRoomBehavior} from './albedo_room_behavior.mjs';
import {IdleChoreography,routeCoordinates} from './albedo_chibi_choreography.mjs';

export async function startAlbedoChibi({
  doc=document,win=window,
  loadManifest=()=>fetch('/assets/albedo_chibi_manifest.json',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('Manifest unavailable');return r.json();})
}={}){
  const root=doc.getElementById('chibiOperations');if(!root)return null;
  const status=doc.getElementById('chibiArtStatus');
  let controller,renderer,manifest;
  try{
    manifest=await loadManifest();
    validateChibiManifest(manifest);
    controller=new AlbedoChibiController(manifest);
    renderer=new AlbedoChibiRenderer(root,manifest);
  }catch(_){
    if(status)status.textContent='CHIBI FLOOR UNAVAILABLE · MANIFEST CHECK FAILED';
    root.dataset.ready='error';
    return null;
  }
  const floor=root.querySelector('#chibiFloor');
  const compass=root.querySelector('#chibiHeadingReadout');
  const stride=root.querySelector('#chibiStrideReadout');
  const motionToggle=root.querySelector('#chibiMotionToggle');
  const reduced=win.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false;
  let motionEnabled=!reduced;
  let manualRoute=false;
  const choreography=new IdleChoreography();
  const routeLine=floor?.querySelector?.('#chibiRouteLine');
  const routeTarget=floor?.querySelector?.('#chibiRouteTarget');
  const activity=root.querySelector?.('#chibiActivityReadout');
  let lastIdleStep=-1;
  const measure=()=>{
    if(floor?.clientHeight>0&&floor?.clientWidth>0){
      controller.setFloorAspect(floor.clientWidth/floor.clientHeight);
    }
  };
  measure();
  const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(measure):null;
  observer?.observe(floor);

  const comp=doc.getElementById('companion');
  const behavior=new AlbedoRoomBehavior(manifest,{selectedAgent:comp?.value||'kiko'});
  const cue=doc.createElement('span');
  cue.id='chibiBehaviorCue';
  cue.setAttribute('role','status');
  root.querySelector('#chibiZoneState')?.parentElement?.append(cue);
  const inStage=()=> (comp?.value||'kiko')==='kiko' && controller.enabled;
  const cuesText=(snap,beat)=>snap.mode==='walk'?
    'En route · '+snap.waypoints_remaining+' waypoint(s)':
    beat.label+' · '+beat.heading.toUpperCase()+' gaze (technical proof)';
  const paint=()=>{
    const snap=controller.snapshot();
    renderer.draw(snap);
    if(compass)compass.textContent=snap.heading.toUpperCase();
    if(stride)stride.textContent=String(snap.frame).padStart(2,'0')+'/04';
    const cue=choreography.snapshot();
    root.dataset.idleBeat=String(cue.beat);
    root.dataset.activity=cue.behavior;
    if(activity)activity.textContent=cuesText(snap,cue);
    if(routeLine&&routeTarget){
      const route=routeCoordinates(snap,controller.waypoints);
      routeLine.setAttribute('d',route.path);
      routeTarget.setAttribute('cx',String((route.target.x*1000).toFixed(1)));
      routeTarget.setAttribute('cy',String((route.target.y*1000).toFixed(1)));
      routeTarget.hidden=route.count===0;
    }
    root.dataset.motionOff=String(!motionEnabled);
    root.dataset.direction=snap.heading;
    for(const button of root.querySelectorAll?.('[data-chibi-zone]')||[]){
      if(button.dataset?.chibiZone===snap.zone)
        button.setAttribute?.('aria-current','location');
      else button.removeAttribute?.('aria-current');
    }
  };
  const apply=decision=>{
    manualRoute=false;
    choreography.setBehavior(decision.behavior);
    choreography.reset();
    lastIdleStep=-1;
    controller.dispatchTaskState(decision.state,decision.visible?'kiko':'offstage');
    root.dataset.behavior=decision.behavior;
    root.dataset.taskPhase=decision.state;
    root.dataset.manualRoute='false';
    cue.textContent=decision.visible?decision.cue:
      'Albedo off stage · another companion or task selected';
    if(!motionEnabled&&!controller.arrived)controller.finish();
    paint();
  };
  let previousVisualKey='';
  const onTask=event=>{
    // No user prompts, result bodies, credentials or browser session data.
    const decision=behavior.ingest(event?.detail||{});
    if(!decision.accepted)return;
    const nextKey=JSON.stringify([decision.taskId,decision.agentId,decision.state]);
    if(nextKey===previousVisualKey)return; // Poll-only updatedAt cannot reset manual paths.
    previousVisualKey=nextKey;
    apply(decision);
  };
  const onCompanion=()=>{
    manualRoute=false;
    apply(behavior.selectCompanion(comp?.value||'kiko'));
  };
  const moveToZone=name=>{
    if(!inStage()||!Object.hasOwn(manifest.zones,name))return false;
    controller.goToZone(name);
    choreography.reset();lastIdleStep=-1;
    manualRoute=true;
    root.dataset.manualRoute='true';
    cue.textContent='Operator floor navigation · task telemetry remains authoritative';
    if(!motionEnabled&&!controller.arrived)controller.finish();
    paint();return true;
  };
  const moveToPoint=(x,y)=>{
    if(!inStage())return false;
    controller.goToPoint(x,y);
    choreography.reset();lastIdleStep=-1;
    manualRoute=true;
    root.dataset.manualRoute='true';
    cue.textContent='Manual waypoint · no provider or task dispatch';
    if(!motionEnabled&&!controller.arrived)controller.finish();
    paint();return true;
  };
  win.addEventListener('exodia:command-task',onTask);
  comp?.addEventListener('change',onCompanion);
  const demo=typeof doc.querySelectorAll==='function'?
    doc.querySelectorAll('[data-chibi-go]'):root.querySelectorAll('[data-chibi-go]');
  for(const button of demo||[]){
    button.addEventListener('click',()=>{moveToZone(button.dataset.chibiGo);});
  }
  // These buttons are part of the visible command-floor interaction, not QA.
  for(const button of root.querySelectorAll?.('[data-chibi-zone]')||[]){
    if(!Object.hasOwn(manifest.zones,button.dataset?.chibiZone))continue;
    button.addEventListener('click',()=>{moveToZone(button.dataset.chibiZone);});
  }
  const onFloorClick=event=>{
    if(event.target?.closest?.('[data-chibi-zone]'))return;
    const rect=floor.getBoundingClientRect();
    if(!rect.width||!rect.height)return;
    const x=(event.clientX-rect.left)/rect.width;
    const y=(event.clientY-rect.top)/rect.height;
    if(Number.isFinite(x)&&Number.isFinite(y))moveToPoint(x,y);
  };
  floor?.addEventListener?.('click',onFloorClick);
  // Keyboard moves the registered foot anchor, not a DOM cutout.
  const onFloorKey=event=>{
    if(event?.target!==floor||event.altKey||event.ctrlKey||event.metaKey)return;
    const deltas={ArrowUp:[0,-1],ArrowDown:[0,1],
      ArrowLeft:[-1,0],ArrowRight:[1,0]};
    const axis=deltas[event.key];if(!axis||!inStage())return;
    event.preventDefault?.();
    const step=event.shiftKey?.07:.035;
    moveToPoint(controller.target.x+axis[0]*step,
      controller.target.y+axis[1]*step);
  };
  floor?.addEventListener?.('keydown',onFloorKey);

  const onMotionToggle=()=>{
    motionEnabled=!motionEnabled;
    motionToggle?.setAttribute('aria-pressed',String(motionEnabled));
    if(motionToggle)motionToggle.textContent=motionEnabled?'Motion on':'Motion off';
    if(!motionEnabled&&!controller.arrived)controller.finish();
    choreography.pause(!motionEnabled);
    lastIdleStep=-1;
    paint();
  };
  if(motionToggle){
    motionToggle.setAttribute('aria-pressed',String(motionEnabled));
    motionToggle.textContent=motionEnabled?'Motion on':'Motion off';
    motionToggle.addEventListener('click',onMotionToggle);
  }
  let raf=0,previous=null;
  const render=now=>{
    const dt=previous===null?0:Math.max(0,(now-previous)/1000);
    previous=now;
    if(doc?.hidden){previous=null;raf=win.requestAnimationFrame(render);return;}
    if(controller.enabled&&!controller.arrived){
      if(!motionEnabled)controller.finish();
      else controller.tick(dt);
      if(controller.arrived){choreography.reset();lastIdleStep=-1;}
      paint();
    }else if(controller.enabled&&controller.arrived&&motionEnabled){
      const cue=choreography.tick(dt,{idle:true,motion:motionEnabled});
      if(cue.steps!==lastIdleStep){
        lastIdleStep=cue.steps;
        controller.faceIdle(cue.heading);
        paint();
      }
    }
    raf=win.requestAnimationFrame(render);
  };
  apply(behavior.snapshot());
  if(win.__exodiaLastPublicTaskState)
    onTask({detail:win.__exodiaLastPublicTaskState});
  raf=win.requestAnimationFrame(render);
  root.dataset.ready='1';
  const runtime={
    controller,renderer,behavior,choreography,moveToPoint,moveToZone,
    stop(){
      win.cancelAnimationFrame(raf);
      win.removeEventListener('exodia:command-task',onTask);
      comp?.removeEventListener('change',onCompanion);
      floor?.removeEventListener?.('click',onFloorClick);
      floor?.removeEventListener?.('keydown',onFloorKey);
      motionToggle?.removeEventListener?.('click',onMotionToggle);
      observer?.disconnect();renderer.destroy();
    },
    update:apply,
    get manualRoute(){return manualRoute;}
  };
  win.__exodiaChibiRuntime=runtime;
  return runtime;
}
if(typeof document!=='undefined')startAlbedoChibi();
