/** Gate 3 / EXODIA 33-state REAL APP review workbench.
 * A missing original is NEVER represented by a reused/cloned portrait. */
const $=id=>document.getElementById(id);
const ICONS={expression:'✧',action:'⌘'};
const REQUIRED_SCHEMA='exodia.state33-review-workbench/v1';
let registry=null,selected=0,token=0,active=0,stages=[],visited=new Set();
let autoTimer=null,autoCursor=0,autoAdvanceCount=0;
const autoRequestedStates=new Set();
const cached=new Map();
let lastTaskKey=null;

function updateStatus(msg){$('loadStatus').textContent=msg;}
function badgeFor(item){
 if(item.art_status==='OWNER_ACCEPTED_DEVELOPMENT_RESAMPLED_REVIEW_ONLY'
    && item.review_is_resampled_from_low_resolution===true)
   return 'DEVELOPMENT ACCEPTED · RESAMPLED, NOT NATIVE';
 if(item.owner_approved_lowres_design_reference?.visual_design_approved_exact_sha)
   return 'DESIGN APPROVED · NATIVE PENDING';
 if(item.owner_development_status==='CORRECTION_REQUIRED')return 'REGENERATION REQUIRED';
 if(item.owner_development_status==='CORRECTION_RENDERED_OWNER_REVIEW_PENDING')return 'CORRECTED · OWNER REVIEW PENDING';
 if(item.owner_development_status==='OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT')return 'DEVELOPMENT ACCEPTED';
 if(item.art_status==='CONCEPT_REVIEW_AVAILABLE')return 'CONCEPT / SHA OK';
 if(item.art_status==='INDEPENDENT_ART_UNAPPROVED_REVIEW')return 'NATIVE CANDIDATE / REVIEW';
 if(item.tentative_reference_approved)return 'TENTATIVE REF · IMPORT ART';
 return 'ART PENDING';
}
function createStage(){
 const frame=$('portraitFrame');
 const loading=frame.querySelector('.portrait-loading');
 if(loading)loading.remove();
 for(let i=0;i<2;i++){
  const div=document.createElement('div');div.className='portrait-display-layer';
  Object.assign(div.style,{position:'absolute',inset:'0',opacity:'0',transition:'none',pointerEvents:'none'});
  const img=document.createElement('img');img.className='portrait-preview-layer';img.alt='';img.draggable=false;
  Object.assign(img.style,{position:'absolute',inset:'0',height:'100%',width:'100%',objectFit:'contain',opacity:'1'});
  const missing=document.createElement('div');missing.className='portrait-missing-layer';
  missing.innerHTML='<span class="missing-sigil">✧</span><b></b><p>Independent original artwork not yet available</p><small>NO PROXY · GENERATION AUTHORIZED</small>';
  div.append(img,missing);frame.append(div);
  stages.push({div,img,missing});
 }
}
function clearPreviewCache(){
 for(const url of cached.values())URL.revokeObjectURL(url);
 cached.clear();
}
function signalLabel(signal){
 return {none:'RESTING',focus_resonance:'FOCUSED',triumphant_halo:'JOY / SUCCESS',
 warning_pulse:'CAUTION',strain_glitch:'STRAIN'}[signal]||'ACTIVE';
}
function addButtons(){
 const menu=$('stateMenu');menu.replaceChildren();
 registry.state_order.forEach((state,index)=>{
  if(index===0||index===5){
   const header=document.createElement('div');
   header.className='state-group-heading';
   header.textContent=index===0?'01 · Core-Five tentative references':'02 · 28 distinct art assignments';
   menu.appendChild(header);
  }
  const item=registry.states[state];
  const button=document.createElement('button');
  button.type='button';button.className='state-button';button.dataset.state=state;
  button.dataset.availability=item.art_status;button.dataset.category=item.category;
  button.dataset.ownerReview=item.owner_development_status||'UNREVIEWED';
  button.setAttribute('aria-pressed',String(selected===index));
  const symbol=document.createElement('span');symbol.className='glyph';symbol.textContent=ICONS[item.category]||'✦';
  const detail=document.createElement('span');detail.className='detail';
  const strong=document.createElement('strong');strong.textContent=item.label;
  const small=document.createElement('small');small.textContent=badgeFor(item);
  detail.append(strong,small);
  const arrow=document.createElement('span');arrow.className='arrow';arrow.textContent='›';
  button.append(symbol,detail,arrow);
  button.addEventListener('click',()=>select(index));
  menu.appendChild(button);
 });
}
async function verifiedImage(item){
 const key=item.key;
 if(cached.has(key))return cached.get(key);
 if(!item.image_url||!item.sha256||!/^[a-f0-9]{64}$/i.test(item.sha256))
   throw Error('Image URL/hash absent');
 if(!/^\/api\/albedo\/(?:core5|state33)\/review-assets\/[a-z_]+$/.test(item.image_url))
   throw Error('Non-local image URL prohibited');
 const r=await fetch(item.image_url,{cache:'no-store'});
 if(!r.ok)throw Error('Image not verified: HTTP '+r.status);
 const blob=await r.blob();
 const bytes=await blob.arrayBuffer();
 const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
  .map(b=>b.toString(16).padStart(2,'0')).join('');
 if(hash!==item.sha256)throw Error('Image SHA mismatch');
 const objUrl=URL.createObjectURL(blob);
 const probe=new Image();probe.src=objUrl;
 try{await probe.decode();}catch(e){URL.revokeObjectURL(objUrl);throw e;}
 if(probe.naturalWidth!==1536||probe.naturalHeight!==1920){
   URL.revokeObjectURL(objUrl);throw Error('Incorrect 1536×1920 image canvas');
 }
 cached.set(key,objUrl);
 return objUrl;
}
function detail(item){
 $('stateKey').textContent=item.key.toUpperCase();
 $('stateTitle').textContent=item.label;
 $('statusLabel').textContent=item.label.toUpperCase();
 $('innerState').textContent=signalLabel(item.signal_overlay);
 $('statusText').textContent=item.pose_direction||'Pending independently authored state artwork';
 $('actionDetails').textContent=item.pose_direction||'Pose production awaiting original image';
 $('sourceName').textContent=item.source_filename||'NO INDEPENDENT SOURCE YET';
 $('assetHash').textContent=item.sha256||'NOT GENERATED / NOT VERIFIED';
 $('artStatusTag').textContent=item.art_status;
 $('ownerDevelopmentStatus').textContent=(
  item.art_status==='OWNER_ACCEPTED_DEVELOPMENT_RESAMPLED_REVIEW_ONLY'
   ?'Owner accepted development artwork · source 1122×1402 · presentation 1536×1920 RESAMPLED, NOT NATIVE · production pending'
  :item.owner_approved_lowres_design_reference?.visual_design_approved_exact_sha
   ?'Owner approved exact design SHA '+item.owner_approved_lowres_design_reference.sha256.slice(0,12)
    +' · 1122×1402 · native rerender still required · original reviewed art shown'
   :item.owner_development_status==='OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT'
   ?'Accepted for continued development · NOT production'
   :item.owner_development_status==='CORRECTION_REQUIRED'
    ?'Needs independent replacement · original review art shown'
    :item.owner_development_status==='CORRECTION_RENDERED_OWNER_REVIEW_PENDING'
     ?'Corrected candidate · owner review pending'
     :'Unreviewed'
 );
 $('registryStatus').textContent='33 / 33 pending production art';
 $('gestureBeam').hidden=item.key!=='pointing';
 $('portraitFrame').setAttribute('aria-label','Albedo '+item.label+' — '+item.art_status);
 const eye=item.measurements?.eye_y;
 const sh=item.measurements?.shoulder_y;
 $('dualAnchors').textContent=Number.isFinite(eye)&&Number.isFinite(sh)
  ?eye.toFixed(2)+' / '+sh.toFixed(2)+' (provisional only)'
  :'NOT MEASURED';
 $('headWidth').textContent=Number.isFinite(item.measurements?.head_width_px)
  ?item.measurements.head_width_px.toFixed(2)+'px (unapproved)'
  :'NOT CERTIFIED';
 $('geometryVerdict').textContent=item.geometry_status==='ACTUAL_PIXELS_GEOMETRY_FAIL_OWNER_UNREVIEWED'
  ?'FAIL · real pixels, owner unreviewed':item.geometry_status;
 const coords=pt=>pt&&Number.isFinite(pt.x)&&Number.isFinite(pt.y)
  ?'('+pt.x.toFixed(1)+', '+pt.y.toFixed(1)+')':null;
 const m=item.measurements||{};
 $('irisDetail').textContent=coords(m.iris_left)&&coords(m.iris_right)
  ?coords(m.iris_left)+' / '+coords(m.iris_right):'Not measured';
 $('shoulderDetail').textContent=coords(m.shoulder_left)&&coords(m.shoulder_right)
  ?coords(m.shoulder_left)+' / '+coords(m.shoulder_right):'Not measured';
 $('centerDetail').textContent=Number.isFinite(m.center_x_px)
  ?m.center_x_px.toFixed(2)+' (Δ '+m.center_delta_px.toFixed(2)+'px)':'Not measured';
 $('frameCount').textContent=visited.size+' / 33';
 document.querySelectorAll('[data-state]').forEach(el=>
  el.setAttribute('aria-pressed',String(el.dataset.state===item.key)));
 $('portraitFrame').closest('.hero').dataset.signal=item.signal_overlay||'none';
}
async function select(index){
 if(!registry)return;
 const order=registry.state_order;
 const nextIndex=(index+order.length)%order.length;
 const state=order[nextIndex],item=registry.states[state];
 const req=++token;
 updateStatus('Preparing '+item.label+' — '+badgeFor(item));
 let url=null;
 let assetError=null;
 try{if(item.image_url)url=await verifiedImage(item);}
 catch(error){
  assetError=error.message;
  url=null;
 }
 if(req!==token)return;
 const next=1-active;
 const stage=stages[next];
 if(url){
  stage.img.src=url;stage.img.hidden=false;stage.missing.style.display='none';
 } else {
  stage.img.hidden=true;stage.img.removeAttribute('src');
  stage.missing.style.display='flex';
  stage.missing.querySelector('b').textContent=item.label.toUpperCase();
  stage.missing.querySelector('small').textContent=
   assetError?'SHA/CANVAS VERIFICATION REJECTED':'NO PROXY · GENERATION AUTHORIZED';
 }
 const ms=matchMedia('(prefers-reduced-motion:reduce)').matches?0:Math.min(650,Number($('transitionSpeed').value)||0);
 const prev=stages[active];
 stage.div.style.transition='none';stage.div.style.opacity='0';
 void stage.div.offsetWidth;
 stage.div.style.transition='opacity '+ms+'ms ease-in-out';
 prev.div.style.transition='opacity '+ms+'ms ease-in-out';
 stage.div.style.opacity='1';prev.div.style.opacity='0';
 active=next;selected=nextIndex;visited.add(state);detail(item);
 if(assetError){
  $('artStatusTag').textContent='ASSET INTEGRITY REJECTED';
  updateStatus(item.label+': IMAGE REJECTED — '+assetError+'. Production remains locked.');
 }else{
  updateStatus(item.label+': '+(url?'SHA-VERIFIED UNAPPROVED ART':'NO ART FILE — original pose outstanding')
   +' · '+registry.artwork_available_count+' / 33 images available'
   +(item.review_is_resampled_from_low_resolution?' · RESAMPLED NOT NATIVE':'') );
 }
 $('autoCycle').title='33-state demo; missing art has no substituted portrait';
}
async function loadManifest(retain=false){
 const res=await fetch('/api/albedo/state33/manifest',{cache:'no-store'});
 if(!res.ok)throw Error('33-state manifest unavailable: HTTP '+res.status);
 const m=await res.json();
 if(m.schema!==REQUIRED_SCHEMA||m.count!==33||m.state_order.length!==33||
    m.additional_state_count!==28||m.production_release_enabled!==false||
    m.owner_production_approved_count!==0||
    m.production_status!=='ALL_33_PENDING_PRODUCTION_ART'||
    new Set(m.state_order).size!==33||
    m.state_order.slice(0,5).join(',')!=='idle,working,explaining,monitoring,pointing'||
    m.state_order.some(s=>!m.states[s]||m.states[s].production_status!=='pending_production_art'||
      m.states[s].owner_approved!==false))
   throw Error('Invalid/unsafe 33-state review manifest');
 registry=m;clearPreviewCache();addButtons();
 await select(retain?selected:0);
}
function updateAutoplay(){
 if(autoTimer){clearInterval(autoTimer);autoTimer=null;}
 if($('autoCycle').checked){
  autoCursor=selected;
  autoAdvanceCount=0;
  autoRequestedStates.clear();
  autoTimer=setInterval(()=>{
   if(!registry)return;
   // Advance the requested sequence independently of potentially delayed
   // image decoding. Every tick requests the NEXT unique state in order,
   // never repeats a state while a large PNG is still loading.
   autoCursor=(autoCursor+1)%registry.state_order.length;
   autoAdvanceCount++;
   autoRequestedStates.add(registry.state_order[autoCursor]);
   select(autoCursor);
  },4000);
 }
}
function registerInput(buttonId,inputId,endpoint){
 $(buttonId).addEventListener('click',async()=>{
  const file=$(inputId).files?.[0];
  if(!file||!file.name.toLowerCase().endsWith('.zip')){updateStatus('Select a ZIP archive first.');return;}
  if(file.size>170*1024*1024){updateStatus('Archive too large');return;}
  const button=$(buttonId);button.disabled=true;
  try{
   updateStatus('Validating SHA-256, original image identity and clone safeguards…');
   const r=await fetch(endpoint,{method:'POST',headers:{
      'Content-Type':'application/zip','X-Exodia-Client':'exodia-dashboard'},body:file});
   if(!r.ok){const j=await r.json().catch(()=>({detail:'Import request failed'}));throw Error(j.detail);}
   await loadManifest(true);
  }catch(error){updateStatus('REVIEW IMPORT REJECTED: '+error.message);}
  finally{button.disabled=false;}
 });
}
async function pollTask(){
 if(!$('observeTasks').checked||!registry)return;
 try{
  const r=await fetch('/api/command/tasks',{cache:'no-store'});
  if(!r.ok)return;
  const json=await r.json();const task=(json.tasks||[]).find(t=>t.agent_id==='kiko');
  if(!task)return;
  const key=task.id+':'+task.state;
  if(key===lastTaskKey)return;
  lastTaskKey=key;
  const status=String(task.state||'').toLowerCase();
  const pose=/answered|complete|success/.test(status)?'explaining':
      /running|processing|generating|submitted/.test(status)?'working':
      /waiting|pending|queued/.test(status)?'monitoring':'idle';
  const index=registry.state_order.indexOf(pose);
  if(index!==-1)await select(index);
 }catch(error){updateStatus('Live task observer unavailable; manual 33-state preview remains active.');}
}
function clock(){const d=new Date();$('clock').textContent=d.toLocaleTimeString('en-CA',{hour:'2-digit',minute:'2-digit'});}
createStage();clock();setInterval(clock,30000);
$('autoCycle').addEventListener('change',updateAutoplay);
$('transitionSpeed').addEventListener('input',e=>$('speedValue').textContent=e.target.value+' ms');
$('ambientMotion').addEventListener('change',e=>document.body.classList.toggle('quiet-ambience',!e.target.checked));
$('restart').addEventListener('click',()=>select(0));
$('copyDebug').addEventListener('click',()=>{
 if(!registry)return;
 const payload={selected:registry.state_order[selected],status:registry.states[registry.state_order[selected]],
  assets_loaded:registry.artwork_available_count,art_count:33,
  production_release_enabled:false,owner_production_approved_count:0};
 if(navigator.clipboard?.writeText)navigator.clipboard.writeText(JSON.stringify(payload,null,2))
    .then(()=>updateStatus('33-state telemetry copied'))
    .catch(()=>updateStatus('Clipboard permission not available'));
});
document.addEventListener('keydown',e=>{
 if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;
 if(e.key==='ArrowRight'){e.preventDefault();select(selected+1);}
 if(e.key==='ArrowLeft'){e.preventDefault();select(selected-1);}
});
registerInput('coreImport','coreZip','/api/albedo/core5/review-import');
registerInput('reviewOnlyImport','reviewOnlyZip','/api/albedo/state33/gate4-four-review-import');
$('reviewRollback').addEventListener('click',async()=>{
 if(!window.confirm('Restore the previous four development review portraits from the verified local rollback snapshot? The 29 protected originals will remain unchanged.'))return;
 const button=$('reviewRollback');button.disabled=true;
 try{
  const r=await fetch('/api/albedo/state33/gate4-four-review-rollback',{
   method:'POST',headers:{'X-Exodia-Client':'exodia-dashboard'}});
  if(!r.ok){const e=await r.json().catch(()=>({detail:'Rollback rejected'}));throw Error(e.detail);}
  await loadManifest(true);
  updateStatus('Four-portrait review rollback verified; 29 protected assets unchanged.');
 }catch(error){updateStatus('REVIEW ROLLBACK REJECTED: '+error.message);}
 finally{button.disabled=false;}
});
registerInput('stateImport','stateZip','/api/albedo/state33/gate4-four-correction-import');
setInterval(pollTask,4000);
window.addEventListener('beforeunload',clearPreviewCache);
window.__exodia33={get selected(){return registry?.state_order[selected]||null;},
 get inspected(){return visited.size;},get loaded(){return registry?.artwork_available_count||0;},
 get releaseEnabled(){return false;},
 get autoAdvances(){return autoAdvanceCount;},
 get autoUniqueRequested(){return autoRequestedStates.size;}};
loadManifest().catch(e=>updateStatus('33-state workbench rejected manifest: '+e.message));
