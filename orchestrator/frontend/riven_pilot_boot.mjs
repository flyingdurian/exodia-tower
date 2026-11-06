/* Phase 7: Riven review-only state projection inside the existing command center.
   No portrait generation, no animation impersonation, no approval mutations. */
const panel = document.querySelector('#rivenPilotPane');
const companion = document.querySelector('#companion');
const floor = document.querySelector('#chibiOperations');
const stateLabel = document.querySelector('#rivenPilotState');
const statusLabel = document.querySelector('#rivenPilotStatus');
const absence = document.querySelector('#rivenPilotFallback');
const buttons = [...document.querySelectorAll('[data-riven-preview]')];
const HEADER = {'X-Exodia-Client':'exodia-dashboard'};
const STATES = new Set(['neutral','confident','angered','working','pointing']);

let chosen = {agentId:'kiko',taskId:'',state:'idle'};
let manual = null;
let revision = 0;
let lastRequest = '';

function refreshButtonState(){
  for(const item of buttons)
    item.setAttribute('aria-pressed', String(item.dataset.rivenPreview === (manual||'automatic')));
}
function isRiven(){
  return companion?.value === 'router';
}
function showForSelection(){
  const enabled=isRiven();
  if(panel)panel.hidden=!enabled;
  if(floor)floor.hidden=enabled;
  if(!enabled){
    revision+=1;
    lastRequest='';
  }
  return enabled;
}

async function update(){
  if(!showForSelection())return;
  const taskId=chosen.agentId==='router' ? chosen.taskId : '';
  const params=new URLSearchParams();
  if(taskId)params.set('task_id',taskId);
  if(manual)params.set('preview_state',manual);
  const key=params.toString();
  if(key===lastRequest)return;
  lastRequest=key;
  const serial=++revision;
  statusLabel.textContent='Validating Riven review-only state…';
  try{
    const response=await fetch('/api/fleet/riven/pilot-runtime?'+key,{headers:HEADER});
    if(!response.ok)throw Error('Riven local review preflight unavailable');
    const record=await response.json();
    if(serial!==revision||!isRiven())return;
    if(record.character_id!=='router'||record.production_release_enabled!==false||
       !STATES.has(record.selected_state)||record.display?.asset_url!==null||
       record.states?.length!==5||record.states.some(x=>x.asset_url!==null)){
      throw Error('Riven review contract invalid');
    }
    const kind=record.display.current_behavior||record.selected_state;
    stateLabel.textContent=record.selected_state.toUpperCase()+' · '+kind.toUpperCase();
    absence.textContent='NATIVE RIVEN ART PENDING';
    statusLabel.textContent=(record.review_preview?'Manual review preview · ':'Task-bound review state · ')+
      kind+'. '+(record.native_a0_intake?.technical_source_pass?
      'A0 source preflight observed; exact-SHA owner approval still pending.':
      'Native A0 identity not yet technically accepted.');
  }catch(_){
    if(serial!==revision||!isRiven())return;
    stateLabel.textContent='REVIEW LOCKED';
    absence.textContent='NO VERIFIED RIVEN STATE ART';
    statusLabel.textContent='The Riven review validator is unavailable. No artwork will be displayed.';
    lastRequest='';
  }
}

for(const button of buttons){
  button.addEventListener('click',()=>{
    manual=button.dataset.rivenPreview==='automatic'?null:button.dataset.rivenPreview;
    refreshButtonState();
    lastRequest='';
    void update();
  });
}

if(companion){
  companion.addEventListener('change',()=>{
    manual=null;
    refreshButtonState();
    lastRequest='';
    void update();
  });
}
window.addEventListener('exodia:command-task', event=>{
  const incoming=event.detail||{};
  const next={agentId:incoming.agentId||'kiko',
              taskId:incoming.taskId||'',
              state:incoming.state||'idle'};
  const taskChanged=next.taskId!==chosen.taskId;
  chosen=next;
  if(taskChanged)manual=null;
  refreshButtonState();
  if(taskChanged||isRiven()){
    const key=new URLSearchParams({
      ...(next.agentId==='router'&&next.taskId?{task_id:next.taskId}:{}),
      ...(manual?{preview_state:manual}:{})
    }).toString();
    if(key!==lastRequest)void update();
  }
});
refreshButtonState();
showForSelection();
