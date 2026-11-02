/** EXODIA Gate 2: five-source, hash-verified and deliberately unapproved art viewer.
 * Runs inside existing FastAPI project; never writes the production registry. */
const STATES=Object.freeze(['idle','working','explaining','monitoring','pointing']);
const $=id=>document.getElementById(id);
const modes={
  idle:['RELAXED / STANDBY','Available for the next mission'],
  working:['ACTIVE / WORKSTATION','Working at the holographic command interface'],
  explaining:['EXPLAINING / GUIDANCE','Presenting instructions or commentary'],
  monitoring:['MONITORING / ALERTNESS','Observing provider and task status'],
  pointing:['POINTING / EMPHASIS','Extended index finger: verify entire arm and wrist anatomy']
};
const stateName=k=>k.charAt(0).toUpperCase()+k.slice(1);
let manifest,selected='idle',token=0,frontIndex=0,images=[],seen=new Set();
const cache=new Map();
function status(value){$('status').textContent=value;}
function updateButtons(){
  const nav=$('stateMenu');nav.replaceChildren();
  for(const state of STATES){
    const item=manifest.states[state];
    const button=document.createElement('button');
    button.type='button';button.className='choice';
    button.dataset.state=state;
    button.setAttribute('aria-pressed',String(selected===state));
    const title=document.createElement('b');title.textContent=stateName(state);
    const detail=document.createElement('small');
    detail.textContent=item.availability==='unapproved_concept_review'?'Source hash verified':'Awaiting review ZIP';
    button.append(title,detail);
    button.disabled=item.availability!=='unapproved_concept_review';
    button.addEventListener('click',()=>selectState(state));
    nav.appendChild(button);
  }
}
async function downloadAndVerify(state){
  if(cache.has(state))return cache.get(state);
  const item=manifest.states[state];
  if(item.availability!=='unapproved_concept_review'||!item.image_url||!/^[a-f0-9]{64}$/i.test(item.sha256)){
    throw new Error('Image unverified or unavailable');
  }
  const res=await fetch(item.image_url,{cache:'no-store'});
  if(!res.ok)throw new Error('Image HTTP '+res.status);
  const blob=await res.blob();
  const buffer=await blob.arrayBuffer();
  const hex=[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))]
    .map(x=>x.toString(16).padStart(2,'0')).join('');
  if(hex!==item.sha256)throw new Error('Browser SHA mismatch: '+state);
  const image=await createImageBitmap(blob);
  if(image.width!==1536||image.height!==1920){
    image.close();throw new Error('Incorrect 4:5 canvas: '+state);
  }
  image.close();
  const url=URL.createObjectURL(blob);
  cache.set(state,url);
  return url;
}
function showMetadata(state){
 const e=manifest.states[state],m=e.measurements;
 $('assetClass').textContent='UNAPPROVED · RESAMPLED CONCEPT';
 $('sourceFile').textContent=e.source_filename;
 $('sourceSha').textContent=e.source_sha256;
 $('previewSha').textContent=e.sha256;
 $('dims').textContent=e.source_canvas.join('×')+' → '+e.canvas.join('×');
 $('eyeValue').textContent=m.eye_y.toFixed(3)+'px / '+(m.eye_delta>=0?'+':'')+m.eye_delta.toFixed(3);
 $('shoulderValue').textContent=m.shoulder_y.toFixed(3)+'px / '+(m.shoulder_delta>=0?'+':'')+m.shoulder_delta.toFixed(3);
 $('headValue').textContent=m.head_width_px.toFixed(2)+' px (target 614.4)';
 $('geometryValue').textContent=m.numeric_provisional_pass?'MIDPOINT ONLY — PASS':'FAIL';
 $('stateTitle').textContent=modes[state][0];
 $('stateCaption').textContent=modes[state][1];
 $('scene').dataset.activity=state;
 $('portraitFrame').setAttribute('aria-label','Albedo '+state+' — unapproved concept review');
 $('visited').textContent=seen.size+' / 5 states inspected';
 document.querySelectorAll('[data-state]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.state===state)));
}
async function selectState(state){
 if(!STATES.includes(state))return;
 const request=++token;
 if(manifest?.states?.[state]?.availability!=='unapproved_concept_review')return;
 try{
   status('Verifying '+state+' PNG SHA and dimensions…');
   const source=await downloadAndVerify(state);
   if(request!==token)return;
   const next=images.length===2?(frontIndex===0?1:0):0;
   const shown=images[next],prev=images[frontIndex===0?1:0];
   if(!shown)throw new Error('Portrait stage unavailable');
   shown.style.transition='none';shown.style.opacity='0';shown.src=source;
   void shown.offsetWidth;
   const ms=matchMedia('(prefers-reduced-motion: reduce)').matches?0:260;
   shown.style.transition='opacity '+ms+'ms ease-in-out';
   shown.style.opacity='1';
   shown.setAttribute('aria-hidden','false');
   const old=images[next===0?1:0];
   if(old){old.style.transition='opacity '+ms+'ms ease-in-out';old.style.opacity='0';old.setAttribute('aria-hidden','true');}
   frontIndex=next;selected=state;seen.add(state);$('emptyPreview').hidden=true;
   showMetadata(state);
   status('Verified '+state+' · SHA '+manifest.states[state].sha256.slice(0,16)+'… · unapproved review');
 }catch(err){status('REJECTED: '+err.message);console.error(err);}
}
function initStage(){
 const frame=$('portraitFrame');
 for(let i=0;i<2;i++){
   const img=document.createElement('img');img.alt='';img.draggable=false;
   img.setAttribute('aria-hidden','true');img.style.opacity='0';frame.appendChild(img);images.push(img);
 }
}
async function refresh(){
 const res=await fetch('/api/albedo/core5/review-manifest',{cache:'no-store'});
 if(!res.ok)throw new Error('Review API unavailable: '+res.status);
 const v=await res.json();
 if(v.schema!=='exodia.core5-live-workbench/v2'||v.release_enabled!==false||
   v.generated_28_states!==0||v.production_masters_loaded!==0||
   STATES.some(s=>v.states[s]?.production_status!=='pending_production_art'||v.states[s]?.owner_approved!==false)){
   throw new Error('Manifest violates production lockdown');
 }
 manifest=v;updateButtons();
 if(v.all_five_loaded)await selectState(selected);
 else status('Five-state viewer ready. Import the verified Gate 1 ZIP; no production files will be changed.');
}
$('importButton').addEventListener('click',async()=>{
 const file=$('reviewZip').files?.[0];
 if(!file){status('Choose the verified Gate 1 review ZIP first.');return;}
 if(!file.name.toLowerCase().endsWith('.zip')||file.size>65*1024*1024){
   status('Invalid ZIP filename or size');return;
 }
 $('importButton').disabled=true;
 try{
   status('Validating all ten original/review images against pinned SHA-256…');
   const res=await fetch('/api/albedo/core5/review-import',{
     method:'POST',headers:{'Content-Type':'application/zip','X-Exodia-Client':'exodia-dashboard'},body:file});
   if(!res.ok){const e=await res.json().catch(()=>({detail:'Upload failed'}));throw new Error(e.detail||'Upload failed');}
   for(const url of cache.values())URL.revokeObjectURL(url);cache.clear();
   selected='idle';await refresh();
 }catch(err){status('IMPORT REJECTED: '+err.message);}
 finally{$('importButton').disabled=false;}
});
async function observeTask(){
 if(!$('observeTasks').checked||!manifest?.all_five_loaded)return;
 try{
  const r=await fetch('/api/command/tasks',{cache:'no-store'});
  if(!r.ok)return;
  const json=await r.json();const tasks=json.tasks||[];
  const task=tasks.find(t=>t.agent_id==='kiko')||tasks[0];
  if(!task)return;
  const current=String(task.state||'').toLowerCase();
  const next=/running|processing|generating|submitted/.test(current)?'working':
             /waiting|pending|queued/.test(current)?'monitoring':
             /answered|complete|success/.test(current)?'explaining':'idle';
  if(next!==selected)await selectState(next);
  $('liveMode').textContent='LIVE TASK OBSERVER — NO TASK MUTATION';
 }catch(e){status('Live task observer offline — manual state controls remain available.');}
}
$('observeTasks').addEventListener('change',e=>{
 $('liveMode').textContent=e.target.checked?'LIVE TASK OBSERVER':'LOCAL ART REVIEW';
});
document.addEventListener('keydown',event=>{
 if(['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))return;
 if(!['ArrowLeft','ArrowRight'].includes(event.key))return;
 const available=STATES.filter(s=>manifest?.states?.[s]?.availability==='unapproved_concept_review');
 if(!available.length)return;
 const index=available.indexOf(selected);
 const advance=event.key==='ArrowRight'?1:-1;
 event.preventDefault();selectState(available[(index+advance+available.length)%available.length]);
});
initStage();
refresh().catch(e=>status('Workbench failed closed: '+e.message));
setInterval(observeTask,4000);
window.addEventListener('beforeunload',()=>{for(const url of cache.values())URL.revokeObjectURL(url);});
