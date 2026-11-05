/** Public command-center summary; deliberately excludes private instructions. */
export function taskSummary(task,{selectedAgent='Albedo',selectedProvider='ChatGPT (chronos)',agentName=(id=>id),providerName=(id=>id)}={}){
 const state=task?.state||'idle';
 const labels={idle:'No active task',draft:'Preparing',queued:'Queued',opening:'Opening provider',researching:'Researching',typing:'Typing',submitting:'Submitting',running:'Processing',rendering_media:'Rendering media',waiting_for_reply:'Waiting for reply',awaiting_operator:'Operator action needed',answered:'Answered',failed:'Failed',cancelled:'Cancelled locally',cooldown:'Provider cooldown'};
 const status=labels[state]||`Task · ${state.replaceAll('_',' ')}`;
 const p=task?String(task.prompt||'').replace(/\s+/g,' ').trim():'No task selected';
 const taskText=p.length>56?p.slice(0,55)+'…':p;
 const result=state==='answered'?(task?.answer?'Response ready':'Completed without text'):
   state==='failed'?'Error · inspect task details':state==='cancelled'?'Remote execution may continue':
   state==='idle'?'Awaiting command':'No response yet';
 const latency=task?.metrics?.total_s;
 return Object.freeze({state,status,taskText,
   agent:task?agentName(task.agent_id):selectedAgent,
   provider:task?providerName(task.provider):selectedProvider,
   result,latency:typeof latency==='number'&&Number.isFinite(latency)&&latency>=0?`${latency.toFixed(2)}s`:'—',
   busy:['draft','queued','opening','researching','typing','submitting','running','rendering_media','waiting_for_reply','awaiting_operator','cooldown'].includes(state)});
}
export function buildIdentity(build){
 const version=typeof build?.version==='string'&&/^\d+\.\d+\.\d+$/.test(build.version)?build.version:'unknown';
 const channel=['development','local','release'].includes(build?.channel)?build.channel:'unknown';
 const sha=typeof build?.commit_sha==='string'&&/^[0-9a-f]{40}$/.test(build.commit_sha)?build.commit_sha.slice(0,12):'unknown';
 return Object.freeze({version,channel,sha,verified:sha!=='unknown',label:build?.label||`EXODIA v${version}-${channel} · ${sha}`});
}
export function renderCommandStatus(root,summary){
 if(!root)return;
 const fields={summaryAgent:summary.agent,summaryTask:summary.taskText,summaryProvider:summary.provider,summaryState:summary.status,summaryResult:summary.result,summaryLatency:summary.latency};
 for(const [id,value] of Object.entries(fields)){const el=root.querySelector('#'+id);if(el)el.textContent=value;}
 root.dataset.state=summary.state;
 root.dataset.busy=String(summary.busy);
}
