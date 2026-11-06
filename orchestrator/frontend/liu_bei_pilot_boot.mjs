/* Phase 7: Liu Bei review-only state projection inside the existing command center.
   No portrait generation, no animation impersonation, no approval mutations. */
const panel = document.querySelector('#liu_beiPilotPane');
const companion = document.querySelector('#companion');
const floor = document.querySelector('#chibiOperations');
const stateLabel = document.querySelector('#liu_beiPilotState');
const statusLabel = document.querySelector('#liu_beiPilotStatus');
const absence = document.querySelector('#liu_beiPilotFallback');
const buttons = [...document.querySelectorAll('[data-liu_bei-preview]')];
const HEADER = {'X-Exodia-Client':'exodia-dashboard'};
const STATES = new Set(['neutral','confident','angered','working','pointing']);

let chosen = {agentId:'kiko',taskId:'',state:'idle'};
let manual = null;
let revision = 0;
let lastRequest=null;

function refreshButtonState(){
  for(const item of buttons)
    item.setAttribute('aria-pressed', String(item.dataset.liu_beiPreview === (manual||'automatic')));
}
function isLiu Bei(){
  return companion?.value === 'liu_bei';
}
function showForSelection(){
  const enabled=isLiu Bei();
  if(panel)panel.hidden=!enabled;
  if(floor)floor.hidden=enabled;
  if(!enabled){
    revision+=1;
    lastRequest=null;
  }
  return enabled;
}

async function update(){
  if(!showForSelection())return;
  const taskId=chosen.agentId==='liu_bei' ? chosen.taskId : '';
  const params=new URLSearchParams();
  if(taskId)params.set('task_id',taskId);
  if(manual)params.set('preview_state',manual);
  const key=params.toString();
  if(key===lastRequest)return;
  lastRequest=key;
  const serial=++revision;
  statusLabel.textContent='Validating Liu Bei review-only state…';
  try{
    const response=await fetch('/api/fleet/liu_bei/pilot-runtime?'+key,{headers:HEADER});
    if(!response.ok)throw Error('Liu Bei local review preflight unavailable');
    const record=await response.json();
    if(serial!==revision||!isLiu Bei())return;
    if(record.character_id!=='liu_bei'||record.production_release_enabled!==false||
       !STATES.has(record.selected_state)||record.display?.asset_url!==null||
       record.states?.length!==5||record.states.some(x=>x.asset_url!==null)){
      throw Error('Liu Bei review contract invalid');
    }
    const kind=record.display.current_behavior||record.selected_state;
    stateLabel.textContent=record.selected_state.toUpperCase()+' · '+kind.toUpperCase();
    absence.textContent='NATIVE LIU BEI ART PENDING';
    statusLabel.textContent=(record.review_preview?'Manual review preview · ':'Task-bound review state · ')+
      kind+'. '+(record.native_a0_intake?.technical_source_pass?
      'A0 source preflight observed; exact-SHA owner approval still pending.':
      'Native A0 identity not yet technically accepted.');
  }catch(_){
    if(serial!==revision||!isLiu Bei())return;
    stateLabel.textContent='REVIEW LOCKED';
    absence.textContent='NO VERIFIED LIU BEI STATE ART';
    statusLabel.textContent='The Liu Bei review validator is unavailable. No artwork will be displayed.';
    lastRequest=null;
  }
}

for(const button of buttons){
  button.addEventListener('click',()=>{
    manual=button.dataset.liu_beiPreview==='automatic'?null:button.dataset.liu_beiPreview;
    refreshButtonState();
    lastRequest=null;
    void update();
  });
}

if(companion){
  companion.addEventListener('change',()=>{
    manual=null;
    refreshButtonState();
    lastRequest=null;
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
  if(taskChanged||isLiu Bei()){
    const key=new URLSearchParams({
      ...(next.agentId==='liu_bei'&&next.taskId?{task_id:next.taskId}:{}),
      ...(manual?{preview_state:manual}:{})
    }).toString();
    if(key!==lastRequest)void update();
  }
});
refreshButtonState();
showForSelection();
