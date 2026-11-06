/* Phase 7: task-driven, review-only Liu Bei in the existing command center.
 * Never display artwork or infer A0 approval from a technical PNG check. */
import {STATE_KEYS, publicTaskSignal, reviewRequestKey, safeReviewProjection}
  from './liu_bei_review_contract.mjs';

const panel = document.querySelector('#liu_beiPilotPane');
const companion = document.querySelector('#companion');
const floor = document.querySelector('#chibiOperations');
const stateLabel = document.querySelector('#liu_beiPilotState');
const statusLabel = document.querySelector('#liu_beiPilotStatus');
const absence = document.querySelector('#liu_beiPilotFallback');
const buttons = [...document.querySelectorAll('[data-liu_bei-preview]')];
const HEADER = {'X-Exodia-Client': 'exodia-dashboard'};

let chosen = publicTaskSignal(window.__exodiaLastPublicTaskState);
let manual = null;
let revision = 0;
let lastRequest = null;

function refreshButtonState() {
  for (const item of buttons)
    item.setAttribute('aria-pressed', String(item.dataset.liu_beiPreview === (manual || 'automatic')));
}

function isLiuBei() {
  return companion?.value === 'liu_bei';
}

function showForSelection() {
  const selected = isLiuBei();
  if (panel) panel.hidden = !selected;
  if (floor) floor.hidden = selected;
  if (!selected) {
    revision += 1; // invalidate in-flight results from a previous selection
    lastRequest = null;
  }
  return selected;
}

async function update({force = false} = {}) {
  if (!showForSelection()) return;
  const taskId = chosen.agentId === 'liu_bei' ? chosen.taskId : '';
  const params = new URLSearchParams();
  if (taskId) params.set('task_id', taskId);
  if (manual) params.set('preview_state', manual);

  // Critically, key includes task state and updatedAt, not only the URL.
  // An existing task can transition running -> answered without changing ID.
  const key = reviewRequestKey(chosen, manual);
  if (!force && key === lastRequest) return;
  lastRequest = key;
  const serial = ++revision;
  statusLabel.textContent = 'Validating Liu Bei review-only state…';
  try {
    const query = params.toString();
    const response = await fetch('/api/fleet/liu_bei/pilot-runtime' +
      (query ? '?' + query : ''), {headers: HEADER});
    if (!response.ok) throw Error('Liu Bei local review preflight unavailable');
    const record = await response.json();
    if (serial !== revision || !isLiuBei()) return;
    const safe = safeReviewProjection(record);
    stateLabel.textContent = safe.state.toUpperCase() + ' · ' + safe.behavior.toUpperCase();
    absence.textContent = 'NATIVE LIU BEI ART PENDING';
    const technical = safe.technicalSourcePass
      ? (safe.geometryConsistent
         ? 'Native technical and annotated geometry checks passed; human source review remains separate.'
         : 'Native PNG technical check passed; landmark verification remains pending.')
      : 'Native A0 source has not passed the local technical gate.';
    statusLabel.textContent =
      (safe.preview ? 'Manual review preview · ' : 'Task-bound review state · ') +
      safe.behavior + '. ' + technical;
  } catch (_) {
    if (serial !== revision || !isLiuBei()) return;
    stateLabel.textContent = 'REVIEW LOCKED';
    absence.textContent = 'NO VERIFIED LIU BEI STATE ART';
    statusLabel.textContent = 'The Liu Bei review validator is unavailable. No artwork will be displayed.';
    lastRequest = null;
  }
}

for (const button of buttons) {
  button.addEventListener('click', () => {
    const requested = button.dataset.liu_beiPreview;
    if (requested !== 'automatic' && !STATE_KEYS.includes(requested)) return;
    manual = requested === 'automatic' ? null : requested;
    refreshButtonState();
    lastRequest = null;
    void update();
  });
}

companion?.addEventListener('change', () => {
  manual = null;
  refreshButtonState();
  lastRequest = null;
  void update();
});

window.addEventListener('exodia:command-task', event => {
  const next = publicTaskSignal(event.detail);
  const changedTask = next.taskId !== chosen.taskId || next.agentId !== chosen.agentId;
  const changedSignal = reviewRequestKey(next, manual) !== reviewRequestKey(chosen, manual);
  chosen = next;
  if (changedTask) manual = null;
  refreshButtonState();
  if (isLiuBei() && (changedTask || changedSignal)) void update();
});

// The A0 watcher may change with no task event; revalidate only while selected.
// This does not submit tasks, inspect passwords or serve unapproved image URLs.
window.setInterval(() => { if (isLiuBei()) void update({force: true}); }, 15000);
window.addEventListener('focus', () => { if (isLiuBei()) void update({force: true}); });

refreshButtonState();
showForSelection();
if (isLiuBei()) void update();
