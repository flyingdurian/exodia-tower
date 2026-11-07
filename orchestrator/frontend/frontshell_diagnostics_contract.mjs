/** Phase 3: privacy-preserving, bounded local provider task/event diagnostics.
 * All input arrives from the existing GET /api/command/tasks and single /ws/events.
 * No prompts, answers, error bodies, URLs, tokens or browser sessions are retained.
 */
import {PROVIDERS,LIVE_TASK_STATES} from './frontshell_telemetry_contract.mjs';
export const TASK_STATES=Object.freeze([
  'draft',...LIVE_TASK_STATES,'answered','failed','cancelled'
]);
const MAX_TASKS=60, MAX_EVENTS=80, MAX_HISTORY=24;
const ID=/^[a-zA-Z0-9_-]{1,128}$/;
export function sanitizeTasks(payload){
  if(!payload||!Array.isArray(payload.tasks))throw Error('Task list unavailable');
  const output=[],seen=new Set();
  for(const task of payload.tasks.slice(0,MAX_TASKS)){
    if(!task||!PROVIDERS.includes(task.provider)||
       !TASK_STATES.includes(task.state)||
       typeof task.id!=='string'||!ID.test(task.id)||seen.has(task.id))continue;
    seen.add(task.id);
    output.push(Object.freeze({
      key:task.id,provider:task.provider,state:task.state,
      agent:typeof task.agent_id==='string'&&/^[a-z][a-z0-9_]{0,31}$/.test(task.agent_id)
        ?task.agent_id:'unverified',
      // Owner identifiers are private; never send user text or task titles.
      label:'Task '+String(output.length+1).padStart(2,'0')
    }));
  }
  return Object.freeze(output);
}
export function classifyHealth({lastSuccessAt=0,now=0,transport='disconnected'}={}){
  if(!Number.isFinite(now)||now<0||!Number.isFinite(lastSuccessAt)||
     !['connected','connecting','disconnected'].includes(transport))
    throw Error('Invalid observation clock');
  const age=lastSuccessAt>0?Math.max(0,now-lastSuccessAt):null;
  return Object.freeze({
    ageMs:age,
    freshness:age===null?'unavailable':age>30000?'stale':age>15000?'aging':'fresh',
    transport,
    authenticatedProviderVerified:false,
    remoteProviderSocketsVerified:false
  });
}
export class OperationalTimeline{
  constructor(limit=MAX_EVENTS){
    if(!Number.isInteger(limit)||limit<2||limit>MAX_EVENTS)throw RangeError('Bad timeline capacity');
    this.limit=limit;this.sequence=0;
    this.last=new Map();this.items=[];this.latest=[];
  }
  accept(tasks,clock){
    if(!Array.isArray(tasks)||!Number.isFinite(clock)||clock<0)
      throw Error('Invalid task snapshot');
    const current=new Map();
    const next=[];
    for(const task of tasks.slice(0,MAX_TASKS)){
      if(!task||!PROVIDERS.includes(task.provider)||!TASK_STATES.includes(task.state)||
         typeof task.key!=='string'||!ID.test(task.key))continue;
      current.set(task.key,task);
      const old=this.last.get(task.key);
      if(!old||old.state!==task.state||old.provider!==task.provider){
        const event=Object.freeze({
          sequence:++this.sequence,at:clock,provider:task.provider,
          state:task.state,agent:task.agent,
          change:old?'state_changed':'observed',
          label:task.label
        });
        this.items.unshift(event);next.push(event);
      }
    }
    this.last=current;
    this.latest=tasks.slice(0,MAX_TASKS);
    if(this.items.length>this.limit)this.items.length=this.limit;
    return Object.freeze(next);
  }
  byProvider(id){
    if(!PROVIDERS.includes(id))throw Error('Unknown provider');
    return Object.freeze({
      events:Object.freeze(this.items.filter(e=>e.provider===id).slice(0,MAX_HISTORY)),
      tasks:Object.freeze(this.latest.filter(t=>t.provider===id).slice(0,12))
    });
  }
  get events(){return Object.freeze([...this.items]);}
  clear(){this.last.clear();this.latest=[];this.items=[];}
}
