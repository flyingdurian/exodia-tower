/* Phase 10: 33-state review UI. Names only; zero art URLs or owner approvals. */
import {safeThirtyThreeReview} from './liu_bei_33_review_contract.mjs';
import {publicTaskSignal} from './liu_bei_review_contract.mjs';

const details = document.querySelector('#liuBei33Registry');
const companion = document.querySelector('#companion');
const label = document.querySelector('#liuBei33Status');
const slot = document.querySelector('#liuBei33List');
const buttonsClass = 'liu-bei-pilot-buttons';
const HEADER = {'X-Exodia-Client':'exodia-dashboard'};
let task = publicTaskSignal(window.__exodiaLastPublicTaskState);
let preview = null;
let generation = 0;
let lastKey = '';

function active(){ return companion?.value === 'liu_bei' && details?.open; }
function updateVisibility() {
  if (!details) return;
  details.hidden = companion?.value !== 'liu_bei';
  if (details.hidden) { generation += 1; lastKey = ''; }
}
async function update() {
  updateVisibility();
  if (!active()) return;
  const params = new URLSearchParams();
  if (task.agentId === 'liu_bei' && task.taskId) params.set('task_id',task.taskId);
  if (preview) params.set('preview_state',preview);
  const query = params.toString();
  const key = JSON.stringify([query,task.state,task.updatedAt]);
  if (key === lastKey) return;
  lastKey = key;
  const serial = ++generation;
  label.textContent = 'Checking canonical 33-state review contract…';
  try {
    const r = await fetch('/api/fleet/liu_bei/33-review' + (query?'?'+query:''),
                          {headers:HEADER});
    if (!r.ok) throw new Error('Review unavailable');
    const safe = safeThirtyThreeReview(await r.json());
    if (serial !== generation || !active()) return;
    slot.replaceChildren();
    const list = document.createElement('div');
    list.className = buttonsClass;
    list.setAttribute('aria-label','Thirty-three pending portrait states');
    for (const state of safe.states) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = state.label;
      button.dataset.stateKey = state.key;
      button.setAttribute('aria-pressed',String(state.key===safe.selectedState));
      button.title = state.category + ' · no approved state art';
      button.addEventListener('click',()=>{
        preview = state.key;
        lastKey = '';
        void update();
      });
      list.append(button);
    }
    const follow = document.createElement('button');
    follow.type='button';
    follow.textContent='Follow live task';
    follow.setAttribute('aria-pressed',String(!preview));
    follow.addEventListener('click',()=>{
      preview=null;
      lastKey='';
      void update();
    });
    list.prepend(follow);
    slot.append(list);
    label.textContent = safe.status + ' · ' +
      (safe.reviewPreview?'manual label: ':'task label: ') +
      safe.selectedState + ' · PRODUCTION LOCKED';
  } catch (_) {
    if (serial !== generation || !active()) return;
    slot.replaceChildren();
    label.textContent='33-state registry unavailable · no artwork released';
    lastKey='';
  }
}
details?.addEventListener('toggle',()=>{void update();});
companion?.addEventListener('change',()=>{
  preview=null;lastKey='';updateVisibility();void update();
});
window.addEventListener('exodia:command-task',event=>{
  const next = publicTaskSignal(event.detail);
  const changedTask = next.agentId!==task.agentId || next.taskId!==task.taskId;
  const changedState = next.state!==task.state || next.updatedAt!==task.updatedAt;
  if (changedTask) preview=null;
  task=next;
  // Don't repeatedly read large native preflight/registry files when the
  // command center republishes an unchanged task during its refresh loop.
  if (changedTask || changedState) void update();
});
window.addEventListener('focus',()=>{
  if (active()) {lastKey='';void update();}
});
updateVisibility();
