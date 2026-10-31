import {KikoArtEngine,ALBEDO_PERFORMANCES} from './kiko_art_engine.mjs';

export const MOTION_MODES=Object.freeze({
  idle:{art:'video',intent:'breathing, eyelids and ambient movement'},
  sleeping:{art:'rig',intent:'eyelids closed, resting torso and lowered arms'},
  processing:{art:'rig',intent:'alternate arm and hand movements, focused gaze'},
  waiting:{art:'rig',intent:'hand near cheek and searching glance'},
  thinking:{art:'rig',intent:'head tilt and thoughtful hand pose'},
  failed:{art:'rig',intent:'shoulders slumped and head down'},
  frustration:{art:'rig',intent:'head shake and clenched arm motions'},
  happy:{art:'rig',intent:'smile and repeated hand wave'},
  excited:{art:'rig',intent:'raised arms and repeated full-body jump'},
  proud:{art:'rig',intent:'upright posture and hands at hips'}
});
export function validatePerformanceMap(){
 const keys=Object.keys(MOTION_MODES);
 if(keys.length!==10 || keys.some(k=>!ALBEDO_PERFORMANCES.includes(k)))
   throw Error('Albedo performances incomplete');
 return true;
}
export class AlbedoMotionStage {
  constructor(canvas,video,{fetcher=fetch,clock=requestAnimationFrame}={}){
    this.canvas=canvas;this.video=video;this.fetcher=fetcher;this.clock=clock;
    this.state='idle';this.ready=false;this.failed=false;this.paused=false;this.engine=null;
    this.loadingPhase='created';
    this.frame=0;this.renderedFrames=0;this.lastFrame=0;this.onStatus=null;
  }
  async initialize(){
    validatePerformanceMap();
    try{
      this.loadingPhase='fetching';
      this.onStatus?.({loading:'Fetching animation artwork and rig data'});
      const [a,b]=await Promise.all([
        this.fetcher('/assets/artwork/kiko_prime/manifest.json').then(r=>{if(!r.ok)throw Error('art manifest missing');return r.json()}),
        this.fetcher('/assets/rigs/kiko.json').then(r=>{if(!r.ok)throw Error('rig manifest missing');return r.json()})
      ]);
      this.loadingPhase='constructing';
      this.onStatus?.({loading:'Building the articulated character skeleton'});
      this.engine=new KikoArtEngine(this.canvas,a,b);
      this.engine.transparentStage=true;
      this.loadingPhase='decoding';
      // The approved 3 MB master may remain undecoded in headed/headless Chromium.
      // Do not block the entire animated character on one unrelated image decode.
      // Registered layers populate independently as their individual images finish.
      let qa;
      for(let i=0;i<60;i++){
        qa=this.engine.getArtQA();
        if(i%5===0)this.onStatus?.({loading:'Decoding character art: '+qa.ready.length+' registered layers'});
        if(qa.ready.includes('head')&&qa.ready.includes('torso'))break;
        await new Promise(resolve=>setTimeout(resolve,200));
      }
      qa=this.engine.getArtQA();
      if(!qa.ready.includes('head')||!qa.ready.includes('torso'))
        throw Error('Essential Albedo art layers did not decode; inspect local assets.');
      this.ready=true;this.loadingPhase='ready';
      this.onStatus?.({ready:true,layers:qa.ready.length,missing:qa.rejected.map(x=>x.name),
          production_ready:false,mode:'registered pre-production articulated art'});
      this.setState(this.state);
      this.lastFrame=performance.now();
      const loop=stamp=>{
        if(!this.ready)return;
        const dt=Math.min(.05,Math.max(0,(stamp-this.lastFrame)/1000));this.lastFrame=stamp;
        if(!this.paused){this.engine.step(dt);this.renderedFrames++;}
        this.frame=this.clock(loop);
      };
      this.frame=this.clock(loop);
      return true;
    }catch(e){
      this.failed=true;this.loadingPhase='error';this.onStatus?.({ready:false,error:String(e.message||e),production_ready:false});
      this.video.hidden=false;this.canvas.hidden=true;return false;
    }
  }
  setState(state){
    if(!Object.hasOwn(MOTION_MODES,state))throw Error('Unknown Albedo state');
    this.state=state;
    if(!this.ready)return;
    this.engine.setPerformance(state);
    // Idle retains genuine historical multi-frame footage. Other states use actual moving joints/face.
    const useRig=MOTION_MODES[state].art==='rig';
    this.canvas.hidden=!useRig;
    this.video.hidden=useRig;
    if(useRig)this.video.pause();
    else if(!this.paused)this.video.play().catch(()=>{});
    this.onStatus?.({ready:true,state,mode:useRig?'articulated proof':'pre-existing idle footage',
      intent:MOTION_MODES[state].intent,layers:this.engine.getArtQA().ready.length,
      production_ready:false});
  }
  setPaused(paused){
    this.paused=Boolean(paused);
    this.engine&&(this.engine.reducedMotion=this.paused);
    if(this.paused)this.video.pause();
    else if(this.state==='idle')this.video.play().catch(()=>{});
  }
  snapshot(){
    return {state:this.state,ready:this.ready,loadingPhase:this.loadingPhase,
      registeredLayers:this.engine?.getArtQA().ready.length||0,
      layerFailures:this.engine?.layerFailures||[],
      renderedFrames:this.renderedFrames,
      active_media:this.state==='idle'?'video':'articulated_canvas',
      production_ready:false};
  }
  destroy(){
    this.ready=false;cancelAnimationFrame(this.frame);
  }
}
