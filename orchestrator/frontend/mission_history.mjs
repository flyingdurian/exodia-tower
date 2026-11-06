/** Local UI-only mission history filtering. No storage, credentials or private instructions. */
export const ACTIVE=new Set(['draft','queued','cooldown','opening','researching','typing','submitting','running','rendering_media','waiting_for_reply','awaiting_operator']);
export const STATES=['all','active','answered','failed','cancelled'];
export const PROVIDERS=['all','chatgpt','gemini','deepseek','ollama'];
export function filterMissionHistory(tasks,{query='',state='all',provider='all'}={}){
 const q=String(query).trim().toLocaleLowerCase();
 return (Array.isArray(tasks)?tasks:[]).filter(task=>{
  if(state==='active'&&!ACTIVE.has(task.state))return false;
  if(state!=='all'&&state!=='active'&&task.state!==state)return false;
  if(provider!=='all'&&task.provider!==provider)return false;
  // Never search private_instructions, credential fields or response bodies.
  const haystack=[task.prompt,task.id,task.agent_id,task.provider].filter(v=>typeof v==='string').join(' ').toLocaleLowerCase();
  return !q||haystack.includes(q);
 });
}
export function describeTask(task){
 const state=String(task?.state||'draft');
 const elapsed=task?.metrics?.total_s;
 const timing=typeof elapsed==='number'&&Number.isFinite(elapsed)&&elapsed>=0?`${elapsed.toFixed(2)}s`:'time unreported';
 const lifecycle=state==='cancelled'?'Cancelled locally · remote request may continue':
 state==='failed'?'Failed · provider details below':state==='answered'?'Answered':
 ACTIVE.has(state)?'In progress · '+state.replaceAll('_',' '):state.replaceAll('_',' ');
 return Object.freeze({lifecycle,timing});
}
export function publicApiRows(catalog){
 const opts=catalog?.options;
 if(!Array.isArray(opts))return [];
 return opts.filter(o=>o?.transport==='api').map(o=>({
  value:o.value,label:o.label,
  configured:o.available===true&&o.status!=='not_configured',
  description:o.available===true&&o.status!=='not_configured'?'Configured in catalog · verify credentialed transport separately':'Not configured · no requests sent',
 }));
}
