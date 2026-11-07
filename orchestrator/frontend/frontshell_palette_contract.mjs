/** Phase 4 local-only operator command palette.
 * IDs/paths are hardcoded and reviewed: no user-supplied shell, URL or HTTP write.
 */
export const ACTIONS=Object.freeze([
  {id:'go-command',label:'Open Command Room',group:'Navigation',kind:'navigate',path:'/'},
  {id:'go-operations',label:'Open Advanced Operations',group:'Navigation',
    kind:'navigate',path:'/operations-legacy'},
  {id:'go-workflows',label:'Open Workflow Planner',group:'Navigation',
    kind:'navigate',path:'/workflow-planner'},
  {id:'go-companions',label:'Open Companion Roster',group:'Navigation',
    kind:'navigate',path:'/companions'},
  {id:'focus-telemetry',label:'Focus Provider Telemetry',group:'Workspace',kind:'focus',target:'fsTelemetry'},
  {id:'focus-terminal',label:'Open Safe Operator Terminal',group:'Workspace',kind:'focus',target:'fsOperatorTerminal'},
  {id:'preset-command',label:'Preset · Command Overview',group:'Presets',kind:'preset',preset:'command'},
  {id:'preset-investigation',label:'Preset · Investigation',group:'Presets',kind:'preset',preset:'investigation'},
  {id:'preset-operations',label:'Preset · Operations',group:'Presets',kind:'preset',preset:'operations'},
  {id:'preset-triage',label:'Preset · Task Triage',group:'Presets',kind:'preset',preset:'triage'},
  {id:'slot-save-1',label:'Save Current Workspace · Slot 1',group:'Presets',
    kind:'save-slot',slot:'custom1'},
  {id:'slot-save-2',label:'Save Current Workspace · Slot 2',group:'Presets',
    kind:'save-slot',slot:'custom2'},
  {id:'slot-load-1',label:'Load Workspace · Slot 1',group:'Presets',
    kind:'load-slot',slot:'custom1'},
  {id:'slot-load-2',label:'Load Workspace · Slot 2',group:'Presets',
    kind:'load-slot',slot:'custom2'}
].map(x=>Object.freeze(x)));
const IDs=new Set(ACTIONS.map(a=>a.id));
export function searchActions(query=''){
  if(typeof query!=='string'||query.length>100)return Object.freeze([]);
  const words=query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return Object.freeze(ACTIONS.filter(item=>
    words.every(word=>(item.label+' '+item.group+' '+item.id)
      .toLowerCase().includes(word))
  ).slice(0,14));
}
export function actionById(id){
  return typeof id==='string'&&IDs.has(id)?ACTIONS.find(a=>a.id===id):null;
}
export function safeOperatorNotice(detail){
  const valid=['queued','researching','running','waiting_for_reply',
    'awaiting_operator','answered','failed','cancelled'];
  if(!detail||!valid.includes(detail.state))return null;
  const states={queued:'QUEUED',researching:'RESEARCH ACTIVE',running:'IN PROGRESS',
    waiting_for_reply:'WAITING FOR RESPONSE',awaiting_operator:'OPERATOR REVIEW',
    answered:'ANSWER RECEIVED',failed:'TASK FAILED',cancelled:'LOCALLY CANCELLED'};
  const agent=typeof detail.agentId==='string'&&
    /^[a-z][a-z0-9_]{0,31}$/.test(detail.agentId)?
    detail.agentId.replaceAll('_',' ').toUpperCase():'COMPANION';
  return Object.freeze({
    key:(typeof detail.taskId==='string'&&/^[a-zA-Z0-9-]{1,128}$/.test(detail.taskId)?
      detail.taskId:'unspecified')+':'+detail.state,
    label:agent+' · '+states[detail.state],
    requiresAttention:['failed','awaiting_operator'].includes(detail.state),
    // No task text, answer contents, credentials, URLs, or browser auth.
    providerAuthenticated:false
  });
}
