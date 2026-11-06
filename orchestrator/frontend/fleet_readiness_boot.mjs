/* Phase 11 developer readiness panel. No image, provider call or task mutation. */
import {AGENT_IDS, safeFleetReview} from './fleet_readiness_contract.mjs';
import {publicTaskSignal} from './liu_bei_review_contract.mjs';

const pane = document.querySelector('#fleetReadinessPanel');
const status = document.querySelector('#fleetReadinessStatus');
const list = document.querySelector('#fleetReadinessList');
const companion = document.querySelector('#companion');
const HEADER = {'X-Exodia-Client':'exodia-dashboard'};
let task = publicTaskSignal(window.__exodiaLastPublicTaskState);
let requestKey = '';
let revision = 0;

async function refresh() {
  if (!pane?.open) {revision += 1; return;}
  const selected = companion?.value;
  if (!AGENT_IDS.includes(selected)) {
    status.textContent = 'Unknown companion · review unavailable';
    list.replaceChildren();
    return;
  }
  const params = new URLSearchParams({selected_agent:selected});
  if (task.agentId === selected && task.taskId)
    params.set('task_id',task.taskId);
  const key=JSON.stringify([params.toString(),task.state,task.updatedAt]);
  if (key===requestKey) return;
  requestKey=key;
  const serial=++revision;
  status.textContent='Validating fleet state contracts…';
  try {
    const response = await fetch('/api/fleet/readiness?'+params.toString(),
                                 {headers:HEADER});
    if (!response.ok) throw new Error('Fleet status not available');
    const safe=safeFleetReview(await response.json());
    if (serial!==revision || !pane.open || companion?.value!==safe.selectedAgent) return;
    list.replaceChildren();
    for (const agent of safe.companions) {
      const item=document.createElement('li');
      const name=document.createElement('b');
      name.textContent=agent.name+' ('+agent.id+')';
      const note=document.createElement('small');
      note.textContent=' · '+agent.state;
      item.append(name,note);
      if (agent.id===safe.selectedAgent) item.setAttribute('aria-current','true');
      list.append(item);
    }
    status.textContent='10 companions · 330 planned canonical states · '+
      safe.selectedAgent+' '+safe.lifecycle+' ('+safe.stage+') · native release locked';
  } catch (_) {
    if (serial!==revision || !pane.open) return;
    requestKey='';
    list.replaceChildren();
    status.textContent='Fleet review validation unavailable · no release claimed';
  }
}
pane?.addEventListener('toggle',()=>{requestKey='';void refresh();});
companion?.addEventListener('change',()=>{requestKey='';void refresh();});
window.addEventListener('exodia:command-task',event=>{
  task=publicTaskSignal(event.detail);
  requestKey='';
  void refresh();
});
window.addEventListener('focus',()=>{
  if (pane?.open) {requestKey='';void refresh();}
});
