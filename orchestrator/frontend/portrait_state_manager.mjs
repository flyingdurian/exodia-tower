import {signalForState,applySignalLayer} from './signal_overlay.mjs';
/** EXODIA verified static-portrait state controller: no per-state transforms. */
export const SCHEMA='exodia.portrait-state-registry/v1';
export const REGISTRY_URL='/assets/companions/production/kiko/portrait_registry.json';
export function resolveState(name,registry){
  const id=String(name||'idle').trim().toLowerCase().replace(/[\s-]+/g,'_');
  return registry.runtime_aliases?.[id] || (registry.states?.[id]?id:'idle');
}
export function registryValid(r){
  return r?.schema===SCHEMA&&r?.character_id==='kiko'&&r?.canvas?.width===1536&&
    r?.canvas?.height===1920&&r?.canvas?.aspect_ratio==='4:5'&&
    Object.keys(r.states||{}).length===33&&Object.keys(r.loops||{}).length===3;
}
export function eligible(r,item){
  return r?.release?.enabled===true&&item?.status==='verified'&&
    /^frames\/(?:expression|action)s\/[a-z_]+\.png$/.test(item.path||'')&&
    /^[0-9a-f]{64}$/.test(item.sha256||'')&&
    /^[0-9a-f]{64}$/.test(item.registration_sha256||'')&&
    typeof item.owner_approval_reference==='string'&&item.owner_approval_reference.length>=8;
}
async function verifiedBlob(response,sha){
  if(!response.ok||!globalThis.crypto?.subtle)return null;
  const blob=await response.blob();
  if(blob.type&&blob.type!=='image/png')return null;
  const bytes=await blob.arrayBuffer();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
  if(hash!==sha)return null;
  const url=URL.createObjectURL(blob);
  const image=new Image();image.src=url;
  try{await image.decode();}catch(_){URL.revokeObjectURL(url);return null;}
  if(image.naturalWidth!==1536||image.naturalHeight!==1920){URL.revokeObjectURL(url);return null;}
  return url;
}
export class PortraitStateManager {
  constructor({doc=globalThis.document,fetcher=globalThis.fetch?.bind(globalThis),manifestUrl=REGISTRY_URL}={}){
    this.doc=doc;this.fetcher=fetcher;this.manifestUrl=manifestUrl;this.registry=null;
    this.layer=null;this.images=[];this.current='';this.front=0;this.sequence=0;this.cache=new Map();
    this.signalLayer=null;this.signal='none';this.telemetry={hp:1,alert:false,specialCasting:false,strained:false};
  }
  async initialize(){
    if(!this.fetcher)return false;
    try{
      const response=await this.fetcher(this.manifestUrl,{cache:'no-store'});
      if(!response.ok)return false;
      const r=await response.json();
      if(!registryValid(r)||r.release?.enabled!==true||
         r.release?.mode!=='static_portraits'||
         typeof r.release?.owner_static_release_reference!=='string'||
         r.release.owner_static_release_reference.length<8||
         !Object.values(r.states).every(item=>eligible(r,item))||
         new Set(Object.values(r.states).map(item=>item.sha256)).size!==33)return false;
      this.registry=r;return true;
    }catch(_){return false;}
  }
  mount(card){
    if(!this.registry||!card)return false;
    this.card=card;this.layer=this.doc.createElement('div');
    this.layer.className='exodia-portrait-state-layer';this.layer.hidden=true;
    this.layer.setAttribute('role','img');this.layer.setAttribute('aria-label','Albedo portrait');
    for(let i=0;i<2;i++){const img=this.doc.createElement('img');img.className='exodia-portrait-state-frame';
      img.alt='';img.setAttribute('aria-hidden','true');this.layer.appendChild(img);this.images.push(img);}
    this.signalLayer=this.doc.createElement('div');this.signalLayer.className='exodia-signal-layer';applySignalLayer(this.signalLayer,'none');
    this.layer.appendChild(this.signalLayer);
    card.appendChild(this.layer);return true;
  }
  fallback(){
    ++this.sequence;this.current='';
    if(this.layer)this.layer.hidden=true;
    this.signal='none';applySignalLayer(this.signalLayer,'none');
    this.card?.classList.remove('portrait-registry-active');
  }
  async setState(raw,agentId='kiko'){
    if(!this.layer||agentId!=='kiko'){this.fallback();return false;}
    const state=resolveState(raw,this.registry),item=this.registry.states[state];
    if(!eligible(this.registry,item)){this.fallback();return false;}
    if(this.current===state&&!this.layer.hidden){this.setSignal();return true;}
    const token=++this.sequence;
    let src=this.cache.get(state);
    if(!src){
      try{src=await verifiedBlob(await this.fetcher('/assets/companions/production/kiko/'+item.path,{cache:'no-store'}),item.sha256);}
      catch(_){src=null;}
      if(!src||token!==this.sequence){if(src)URL.revokeObjectURL(src);return false;}
      this.cache.set(state,src);
    }
    if(token!==this.sequence)return false;
    const incoming=1-this.front,newImg=this.images[incoming],old=this.images[this.front];
    newImg.style.transition='none';newImg.style.opacity='0';newImg.src=src;
    this.layer.hidden=false;this.card.classList.add('portrait-registry-active');
    this.layer.setAttribute('aria-label','Albedo '+item.label);
    void newImg.offsetWidth;
    const reduce=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    const duration=reduce?0:180;
    newImg.style.transition='opacity '+duration+'ms ease-in-out';
    old.style.transition='opacity '+duration+'ms ease-in-out';
    old.style.opacity='0';newImg.style.opacity='1';
    this.front=incoming;this.current=state;this.setSignal();
    return true;
  }
  setSignal(telemetry={}){this.telemetry={...this.telemetry,...telemetry};this.signal=signalForState(this.registry,this.current,this.telemetry);applySignalLayer(this.signalLayer,this.signal);return this.signal;}
  destroy(){this.fallback();this.layer?.remove();for(const x of this.cache.values())URL.revokeObjectURL(x);this.cache.clear();}
}
