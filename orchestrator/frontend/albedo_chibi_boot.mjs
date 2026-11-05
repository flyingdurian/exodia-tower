/** Bind command task phases to the isolated operations-floor chibi sprite. */
import {AlbedoChibiController,validateChibiManifest} from './albedo_chibi_controller.mjs';
import {AlbedoChibiRenderer} from './albedo_chibi_renderer.mjs';

export async function startAlbedoChibi({doc=document,win=window,loadManifest=()=>fetch('/assets/albedo_chibi_manifest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Manifest unavailable');return r.json();})}={}){
  const root=doc.getElementById('chibiOperations');if(!root)return null;
  const status=doc.getElementById('chibiArtStatus');
  let controller,renderer;
  try{
    const manifest=await loadManifest();validateChibiManifest(manifest);
    controller=new AlbedoChibiController(manifest);
    renderer=new AlbedoChibiRenderer(root,manifest);
  }catch(_){status.textContent='CHIBI FLOOR UNAVAILABLE · MANIFEST CHECK FAILED';root.dataset.ready='error';return null;}
  const comp=doc.getElementById('companion');
  const tasks=[];let lastKey=null;let taskAgent='kiko';
  const currentAgent=()=>comp?.value||'kiko';
  const update=(state='idle',agentId=currentAgent())=>{
    // A task for Albedo is not permission to show her on another companion's stage.
    controller.dispatchTaskState(state,agentId==='kiko'&&currentAgent()==='kiko'?'kiko':'offstage');
    renderer.draw(controller.snapshot());
  };
  const onTask=event=>{
    const task=event.detail||{};
    // Task events contain only state/agent IDs, never the user prompt or private instructions.
    const state=task.state||'idle';const agent=task.agentId||currentAgent();
    const key=state+'|'+agent; if(key===lastKey)return;
    lastKey=key;tasks[0]=state;taskAgent=agent;update(state,agent);
  };
  win.addEventListener('exodia:command-task',onTask);
  comp?.addEventListener('change',()=>update(tasks[0]||'idle',taskAgent));
  const demo=root.querySelectorAll('[data-chibi-go]');
  for(const button of demo)button.addEventListener('click',()=>{
    if(currentAgent()!=='kiko')return;
    controller.goToZone(button.dataset.chibiGo);renderer.draw(controller.snapshot());
  });
  const reduced=win.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false;
  let raf=0,previous=null;
  const render=now=>{
    const dt=previous===null?0:Math.max(0,(now-previous)/1000);previous=now;
    if(controller.enabled&&!controller.arrived){if(reduced)controller.finish();else controller.tick(dt);renderer.draw(controller.snapshot());}
    raf=win.requestAnimationFrame(render);
  };
  update();if(win.__exodiaLastPublicTaskState)onTask({detail:win.__exodiaLastPublicTaskState});
  raf=win.requestAnimationFrame(render);root.dataset.ready='1';
  const runtime={controller,renderer,stop(){win.cancelAnimationFrame(raf);win.removeEventListener('exodia:command-task',onTask);renderer.destroy();},update};
  win.__exodiaChibiRuntime=runtime;
  return runtime;
}
if(typeof document!=='undefined')startAlbedoChibi();
