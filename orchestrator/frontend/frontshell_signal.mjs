/* Public-only Frontshell task signal classifier; no provider authentication claims. */
export const PUBLIC_TASK_PHASES=Object.freeze([
  'idle','draft','queued','cooldown','opening','researching','typing',
  'submitting','running','rendering_media','waiting_for_reply',
  'awaiting_operator','answered','failed','cancelled'
]);
const BUSY=new Set(['queued','cooldown','opening','researching','typing',
  'submitting','running','rendering_media']);
const WAITING=new Set(['waiting_for_reply','awaiting_operator']);
const TITLES=Object.freeze({
  idle:'STANDBY · LOCAL',draft:'DRAFT · LOCAL',
  queued:'TASK QUEUED',cooldown:'TASK PREPARING',
  opening:'WORKSPACE OPENING',researching:'RESEARCH ACTIVE',
  typing:'TASK PREPARING',submitting:'TASK SUBMITTING',
  running:'TASK RUNNING',rendering_media:'MEDIA PROCESSING',
  waiting_for_reply:'AWAITING REPLY',awaiting_operator:'OPERATOR ATTENTION',
  answered:'RESPONSE RECEIVED',failed:'TASK NEEDS REVIEW',
  cancelled:'LOCALLY CANCELLED'
});
export function presentPublicTask(detail){
  const state=typeof detail?.state==='string'&&
    PUBLIC_TASK_PHASES.includes(detail.state)?detail.state:'idle';
  const agentId=typeof detail?.agentId==='string'&&
    /^[a-z][a-z0-9_]{0,31}$/.test(detail.agentId)?detail.agentId:'';
  const phase=BUSY.has(state)?'working':WAITING.has(state)?'waiting':
    state==='answered'?'success':state==='failed'?'error':'idle';
  return Object.freeze({
    state,phase,agentId,
    title:agentId&&agentId!=='kiko'?
      'OTHER AGENT · '+(phase==='working'?'ACTIVE':phase==='error'?'REVIEW':'TASK'):
      TITLES[state],
    // A task being present is not evidence a signed-in browser/provider exists.
    providerAuthenticated:false,
    artReleased:false
  });
}
