import {signalForState,applySignalLayer} from './signal_overlay.mjs';

/**
 * Separate Gate-4 development-review stage. Never modifies or bypasses the
 * production PortraitStateManager: release.enabled must stay false, and these
 * SHA-verified previews are visibly NOT certified native production artwork.
 */
export const MANIFEST='/api/albedo/state33/manifest';
export const MOOD_TO_REVIEW=Object.freeze({
 idle:'idle', sleeping:'sleeping', processing:'working', waiting:'awaiting_command',
 thinking:'thinking', failed:'defeat', frustration:'angered', happy:'happy',
 excited:'excited', proud:'celebrating',
});
const SHA=/^[a-f0-9]{64}$/i;
const IMAGE_PREFIX='/api/albedo/state33/review-assets/';
const ACCEPTED=new Set([
 'OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT',
 'REVIEW_ONLY_OWNER_ACCEPTED_NON_NATIVE'
]);

export function validDevelopmentManifest(manifest){
 if(!manifest||manifest.count!==33||manifest.production_release_enabled!==false||
    manifest.owner_development_review_only_count!==4||
    !Array.isArray(manifest.state_order)||manifest.state_order.length!==33||
    new Set(manifest.state_order).size!==33)return false;
 const states=manifest.states||{};
 if(Object.keys(states).length!==33||
    new Set(manifest.state_order.map(key=>states[key]?.sha256)).size!==33||
    new Set(manifest.state_order.map(key=>states[key]?.source_sha256)).size!==33)return false;
 return manifest.state_order.every(key=>{
  const item=states[key];
  return item?.key===key&&SHA.test(item.sha256||'')&&SHA.test(item.source_sha256||'')&&
    item.image_url===IMAGE_PREFIX+key&&
    item.owner_approved===false&&item.native_production_certified===false&&
    ACCEPTED.has(item.owner_development_status);
 });
}

export class DevelopmentPortraitStage {
 constructor({doc=globalThis.document,fetcher=globalThis.fetch?.bind(globalThis)}={}){
  this.doc=doc;this.fetcher=fetcher;this.manifest=null;this.layer=null;
  this.frames=[];this.cached=new Map();this.front=0;this.request=0;
  this.state=null;this.agent='kiko';this.telemetry={};this.signal=null;
  this.status='uninitialized';this.lastVerifiedHash=null;
 }
 async initialize(){
  if(!this.fetcher)return false;
  try{
   const response=await this.fetcher(MANIFEST,{cache:'no-store'});
   if(!response.ok)return false;
   const body=await response.json();
   if(!validDevelopmentManifest(body))return false;
   this.manifest=body;this.status='ready';return true;
  }catch(_){this.status='manifest_unavailable';return false;}
 }
 mount(card){
  if(!this.manifest||!card)return false;
  this.card=card;
  const layer=this.doc.createElement('div');
  layer.className='exodia-portrait-state-layer';layer.hidden=true;
  layer.setAttribute('role','img');
  layer.setAttribute('aria-label','SHA-verified Albedo development review portrait; not native production artwork');
  for(let i=0;i<2;i++){
   const img=this.doc.createElement('img');img.className='exodia-portrait-state-frame';
   img.alt='';img.setAttribute('aria-hidden','true');layer.appendChild(img);this.frames.push(img);
  }
  this.signals=this.doc.createElement('div');this.signals.className='exodia-signal-layer';
  applySignalLayer(this.signals,'none');layer.appendChild(this.signals);
  this.badge=this.doc.createElement('span');this.badge.className='review-portrait-status';this.badge.hidden=true;
  this.unavailable=this.doc.createElement('div');this.unavailable.className='review-portrait-error';
  this.unavailable.textContent='REVIEW IMAGE UNAVAILABLE · SHA VERIFICATION REQUIRED';this.unavailable.hidden=true;
  card.append(layer,this.badge,this.unavailable);this.layer=layer;
  return true;
 }
 async verify(item){
  const existing=this.cached.get(item.key);
  if(existing)return existing;
  if(item.image_url!==IMAGE_PREFIX+item.key||!SHA.test(item.sha256))throw Error('unsafe_asset_reference');
  const response=await this.fetcher(item.image_url,{cache:'no-store'});
  if(!response.ok)throw Error('review_asset_unavailable');
  const blob=await response.blob();
  if(blob.type&&blob.type!=='image/png')throw Error('review_asset_not_png');
  if(!globalThis.crypto?.subtle)throw Error('sha_verification_unavailable');
  const bytes=await blob.arrayBuffer();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
    .map(c=>c.toString(16).padStart(2,'0')).join('');
  if(hash!==item.sha256)throw Error('review_sha_mismatch');
  const url=URL.createObjectURL(blob);
  const img=new Image();img.src=url;
  try{
   await img.decode();
   if(img.naturalWidth!==1536||img.naturalHeight!==1920)throw Error('review_canvas_mismatch');
  }catch(error){URL.revokeObjectURL(url);throw error;}
  const result={url,sha256:hash};this.cached.set(item.key,result);return result;
 }
 fallback(){
  ++this.request;this.state=null;this.lastVerifiedHash=null;
  if(this.layer)this.layer.hidden=true;
  if(this.badge)this.badge.hidden=true;
  if(this.unavailable)this.unavailable.hidden=true;
  this.card?.classList.remove('portrait-registry-active','review-portrait-unavailable');
 }
 async setState(raw,agent='kiko'){
  this.agent=agent;
  if(!this.layer||agent!=='kiko'){this.fallback();return false;}
  const mood=String(raw||'idle').trim().toLowerCase().replace(/[\s-]+/g,'_');
  const key=MOOD_TO_REVIEW[mood]||this.manifest?.states?.[mood]?.key||'idle';
  const item=this.manifest.states[key];
  if(!item){this.fallback();return false;}
  if(this.state===key&&!this.layer.hidden){this.setSignal();return true;}
  const token=++this.request;
  let result;
  try{result=await this.verify(item);}catch(_){
   if(token===this.request){
    this.layer.hidden=true;this.badge.hidden=true;this.unavailable.hidden=false;
    this.card.classList.add('review-portrait-unavailable');
    this.card.classList.remove('portrait-registry-active');
    this.state=null;this.status='asset_unavailable';this.lastVerifiedHash=null;
   }
   return false;
  }
  if(token!==this.request)return false;
  const incoming=1-this.front,next=this.frames[incoming],old=this.frames[this.front];
  next.style.transition='none';next.style.opacity='0';next.src=result.url;
  this.layer.hidden=false;this.badge.hidden=false;this.unavailable.hidden=true;
  this.card.classList.add('portrait-registry-active');
  this.card.classList.remove('review-portrait-unavailable');
  this.layer.setAttribute('aria-label','Albedo '+item.label+' · SHA-verified development-only review artwork, NOT native production');
  this.badge.textContent=item.review_is_resampled_from_low_resolution
   ?'OWNER-ACCEPTED REVIEW · RESAMPLED / NOT NATIVE · PRODUCTION LOCKED'
   :'OWNER-ACCEPTED DEVELOPMENT REVIEW · PRODUCTION LOCKED';
  void next.offsetWidth;
  const duration=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches?0:200;
  next.style.transition='opacity '+duration+'ms ease-in-out';
  old.style.transition='opacity '+duration+'ms ease-in-out';
  old.style.opacity='0';next.style.opacity='1';
  this.front=incoming;this.state=key;this.lastVerifiedHash=result.sha256;this.status='verified';
  this.setSignal();return true;
 }
 setSignal(telemetry={}){
  this.telemetry={...this.telemetry,...telemetry};
  if(this.state){this.signal=signalForState(this.manifest,this.state,this.telemetry);
   applySignalLayer(this.signals,this.signal);}
 }
 destroy(){this.fallback();for(const result of this.cached.values())URL.revokeObjectURL(result.url);
  this.cached.clear();this.layer?.remove();this.badge?.remove();this.unavailable?.remove();}
}
