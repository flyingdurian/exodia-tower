/** EXODIA Phase 2: strict read-only provider/task telemetry projection.
 *
 * All four provider cards share ONE local /ws/events transport; they do not
 * claim vendor-owned WebSocket links, sign-in, API authentication or completed E2E.
 * Only provider IDs + task states are read; prompts/results never leave inputs.
 */
export const PROVIDERS=Object.freeze(['chatgpt','gemini','deepseek','ollama']);
export const LIVE_TASK_STATES=Object.freeze([
  'queued','opening','cooldown','researching','typing','submitting',
  'running','rendering_media','waiting_for_reply','awaiting_operator'
]);
const BUSY=new Set(LIVE_TASK_STATES);
const FINISHED=new Set(['answered','failed','cancelled']);
const SESSION_STATES=new Set([
  'not_started','closed','needs_operator_login_or_review',
  'ready_for_next_prompt','launching','opening','typing','submitting',
  'awaiting_operator','dom_error_manual_review','error',
  'editor_unavailable','waiting_for_reply','running','unknown'
]);
const READY_LABELS=Object.freeze({
  not_started:'Not opened',closed:'Not opened',
  needs_operator_login_or_review:'Open · sign-in unverified',
  ready_for_next_prompt:'Last task complete · sign-in unverified',
  launching:'Opening local browser',opening:'Browser opening',
  typing:'Local browser typing',submitting:'Submitting locally',
  awaiting_operator:'Operator attention',
  dom_error_manual_review:'Browser review required',error:'Browser error',
  editor_unavailable:'Editor unavailable',
  waiting_for_reply:'Waiting for response',running:'Local task active',
  unknown:'Unknown session'
});
const safeNumber=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1000000?v:0;
export function providerId(value){
  return PROVIDERS.includes(value)?value:null;
}
export function projectProviders(providerResponse,sessionResponse,taskResponse){
  if(!providerResponse||typeof providerResponse!=='object'||
     !sessionResponse||typeof sessionResponse!=='object'||
     !taskResponse||!Array.isArray(taskResponse.tasks))
    throw new Error('Telemetry snapshots unavailable');
  const sessions=sessionResponse.models||{};
  const observed={};
  for(const id of PROVIDERS){
    const records=taskResponse.tasks.filter(t=>t&&t.provider===id);
    const active=records.filter(t=>BUSY.has(t.state)).length;
    const finished=records.filter(t=>FINISHED.has(t.state)).length;
    const raw=typeof sessions[id]?.status==='string'?
      sessions[id].status:'unknown';
    const state=SESSION_STATES.has(raw)?raw:'unknown';
    const localConnected=providerResponse.ollama?.connected===true;
    observed[id]=Object.freeze({
      id,active,finished,
      session:id==='ollama'
        ?(localConnected?'Local model reachable':'Local model offline / unverified')
        :READY_LABELS[state],
      status:id==='ollama'?(localConnected?'reachable':'unavailable')
        :state==='unknown'?'unknown':
          ['error','dom_error_manual_review','editor_unavailable'].includes(state)
          ?'attention':'observed',
      // Local event stream link is tracked separately. Provider WS is unverified.
      providerWebSocketVerified:false,
      authenticatedProviderVerified:false
    });
  }
  return Object.freeze(observed);
}

/** Bounded real observations only; no seeded/random or fabricated metric points. */
export class ActivityHistory{
  constructor(limit=32){
    if(!Number.isInteger(limit)||limit<2||limit>64)throw RangeError('Invalid history size');
    this.limit=limit;
    this.series=Object.fromEntries(PROVIDERS.map(id=>[id,[]]));
  }
  append(snapshot){
    for(const id of PROVIDERS){
      const value=safeNumber(snapshot?.[id]?.active);
      const series=this.series[id];
      series.push(value);
      if(series.length>this.limit)series.shift();
    }
    return this.all();
  }
  all(){
    return Object.freeze(Object.fromEntries(
      PROVIDERS.map(id=>[id,Object.freeze([...this.series[id]])])
    ));
  }
}
export function sparklinePath(points,width=180,height=52){
  if(!Array.isArray(points)||points.length===0)return '';
  if(!Number.isFinite(width)||width<=0||!Number.isFinite(height)||height<=0)
    throw RangeError('Invalid chart geometry');
  const valid=points.map(v=>safeNumber(v));
  const cap=Math.max(1,...valid);
  const margin=4;
  return valid.map((v,i)=>{
    const x=margin+(valid.length===1?(width-2*margin)/2:
      i*(width-2*margin)/(valid.length-1));
    const y=height-margin-(v/cap)*(height-2*margin);
    return (i===0?'M':'L')+x.toFixed(2)+' '+y.toFixed(2);
  }).join(' ');
}
export function summariseActivity(snapshot,link='disconnected'){
  const transport=['connected','connecting','disconnected'].includes(link)?link:'disconnected';
  return Object.freeze({
    link:transport,
    active:PROVIDERS.reduce((sum,id)=>sum+safeNumber(snapshot?.[id]?.active),0),
    providers:Object.freeze(PROVIDERS.map(id=>Object.freeze({
      id,
      active:safeNumber(snapshot?.[id]?.active),
      session:typeof snapshot?.[id]?.session==='string'?snapshot[id].session:'Unavailable'
    }))),
    transportLabel:transport==='connected'?'LOCAL EVENTS LINKED':
      transport==='connecting'?'LOCAL EVENTS CONNECTING':'LOCAL EVENTS OFFLINE',
    remoteProviderSocketsVerified:false
  });
}
