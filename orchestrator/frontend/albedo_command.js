import {taskSummary,renderCommandStatus,buildIdentity} from './command_status.mjs';
/* Production-mode expression transitions; no active cutout rig. */
/* Exodia Tower — Albedo live command stage.
 * Stage uses existing multi-frame video, real task events and independent scene VFX.
 * Production-quality articulated character art is NOT claimed.
 * Output DOM is constructed without injecting model-provided HTML.
 */
const $=s=>document.querySelector(s);
const UI={
  hero:$('#hero'),label:$('#moodLabel'),description:$('#moodDescription'),
  overlay:$('#heroOverlay'),prompt:$('#prompt'),model:$('#model'),
  companion:$('#companion'),research:$('#liveResearch'),answer:$('#answerFrame'),
  promptBubble:$('#responsePrompt'),provider:$('#answerProvider'),timing:$('#answerTiming'),
  image:$('#responseImage'),attachment:$('#attachment'),sources:$('#sourceList'),
  taskList:$('#taskList'),feedback:$('#feedback'),diagnostic:$('#diagnosticText'),
  terminalStatus:$('#terminalStatus'),cancelTask:$('#cancelActiveTask'),playback:$('#playbackInfo'),toggle:$('#motionToggle')
};
const HEADER={'X-Exodia-Client':'exodia-dashboard'};
const MOODS=[
 ['idle','Idle','Ready for your command','✧'],['sleeping','Sleeping','Resting between missions','☾'],
 ['processing','Processing','Connecting the task systems','⚙'],['waiting','Waiting','Awaiting the model response','◌'],
 ['thinking','Thinking','Considering the next move','◇'],['failed','Failed result','A mission could not complete','×'],
 ['frustration','Frustration','Reassessing the failed route','!'],['happy','Happy success','The answer is ready','✦'],
 ['excited','Excited success','A wonderful result!','✶'],['proud','Proud','Mission successfully delivered','♔']
];
const ACTIVE=new Set(['researching','opening','queued','cooldown','typing','submitting','running','waiting_for_reply','rendering_media']);
let state='idle',roster=[],tasks=[],activeTaskId=null,chosenTask=null,explicitPreview=false;
let stateTimer=null,lastInteraction=Date.now(),lastCompleted=null,requestInFlight=false,videoOk=false;
let handoffTaskId=null;
const modelLabels=new Map();
const moodDesc=Object.fromEntries(MOODS.map(m=>[m[0],m[2]]));
const prettyName=s=>(s||'').replaceAll('_',' ').toUpperCase();
function refreshCommandSummary(task=chosenTask){
 const agentName=id=>roster.find(a=>a.id===id)?.name||id||'Unknown companion';
 const providerName=id=>modelLabels.get(id)||id||'Unknown provider';
 const selectedAgent=agentName(UI.companion?.value||'kiko');
 const selectedProvider=UI.model?.selectedOptions[0]?.textContent.replace(' — Not configured','')||'Not selected';
 renderCommandStatus(document.getElementById('commandStatusStrip'),taskSummary(task,{selectedAgent,selectedProvider,agentName,providerName}));
 $('#summarySelectedCompanion').textContent=selectedAgent;
 const activeCount=tasks.filter(t=>ACTIVE.has(t.state)||t.state==='awaiting_operator').length;
 $('#summaryBackground').textContent=activeCount?activeCount+' task'+(activeCount===1?'':'s')+' running / waiting':'No tasks running';
 // Only minimal public task routing information enters the movement runtime.
 const publicDetail={state:task?.state||'idle',agentId:task?.agent_id||UI.companion?.value||'kiko',provider:task?.provider||''};
 window.__exodiaLastPublicTaskState=publicDetail;
 window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:publicDetail}));
}
function moodForTask(task){
 if(!task)return Date.now()-lastInteraction>90000?'sleeping':'idle';
 if(task.state==='researching'||task.state==='typing'||task.state==='opening'||task.state==='submitting'||task.state==='rendering_media')return 'processing';
 if(task.state==='running')return 'thinking';
 if(task.state==='waiting_for_reply'||task.state==='awaiting_operator')return 'waiting';
 if(task.state==='failed')return 'failed';
 if(task.state==='cancelled')return 'idle';
 if(task.state==='answered')return 'happy';
 return 'idle';
}
function setMood(next,{preview=false}={}){
 if(!moodDesc[next])next='idle';
 if(stateTimer){clearTimeout(stateTimer);stateTimer=null}
 state=next;UI.hero.dataset.state=next;UI.label.textContent=prettyName(next);
 // The still expression controller observes moodLabel and updates the approved portrait.
 UI.description.textContent=moodDesc[next];
 UI.overlay.textContent=next==='sleeping'?'Z  z  z':next==='thinking'?'✧ ANALYZING ✧':
 next==='processing'?'✧ COMPUTING ✧':next==='waiting'?'◌ AWAITING RESPONSE ◌':
 next==='failed'?'MISSION INTERRUPTED':next==='frustration'?'REASSESSING…':
 next==='happy'?'✦ MISSION COMPLETE ✦':next==='excited'?'✧ BRILLIANT ✧':
 next==='proud'?'✦ WELL DONE ✦':'';
 // Expression selection is automatic; no developer previews.
 explicitPreview=preview;
 if(!preview){
   if(next==='happy')stateTimer=setTimeout(()=>setMood('excited'),2000);
   if(next==='excited')stateTimer=setTimeout(()=>setMood('proud'),2200);
   if(next==='failed')stateTimer=setTimeout(()=>setMood('frustration'),2500);
 }
}
function element(tag,cls,text){
 const e=document.createElement(tag);
 if(cls)e.className=cls;
 if(text!==undefined)e.textContent=String(text);
 return e;
}
function inform(message,isError=false){UI.feedback.textContent=message;UI.feedback.style.color=isError?'#ffb3c7':'#a6f5d6';}
async function api(path,opts={}){
 const response=await fetch(path,{...opts,headers:{...HEADER,...(opts.headers||{})}});
 if(!response.ok){let detail;try{detail=(await response.json()).detail}catch{}
  throw Error(typeof detail==='string'?detail:'Request failed ('+response.status+')')}
 return response.json();
}
function post(path,data){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
const cleanLines=source=>String(source||'').replace(/\r\n?/g,'\n')
 .replace(/(^|\n)\s*(?:1D|5D|1M|6M|YTD|1Y|5Y|MAX)(?:\s*\n\s*(?:1D|5D|1M|6M|YTD|1Y|5Y|MAX)){2,}/g,m=>m.replace(/\n\s*/g,'  '))
 .split('\n');
function inline(parent,value){
 // Safe inline formatting: bold and Markdown links are parsed into DOM nodes.
 const text=String(value||'');
 const pattern=/\[([^\]\n]{1,100})\]\((https:\/\/[^\s)]+)\)|\*\*([^*\n]+)\*\*|`([^`\n]+)`/g;
 let cursor=0,match;
 while((match=pattern.exec(text))){
  if(match.index>cursor)parent.append(document.createTextNode(text.slice(cursor,match.index)));
  if(match[1]&&match[2]){
   const a=element('a','',match[1]);a.href=match[2];a.target='_blank';a.rel='noopener noreferrer';parent.append(a);
  }else if(match[3])parent.append(element('strong','',match[3]));
  else if(match[4])parent.append(element('code','',match[4]));
  cursor=match.index+match[0].length;
 }
 if(cursor<text.length)parent.append(document.createTextNode(text.slice(cursor)));
}
const TIMEFRAME=new Set(['1D','5D','1M','6M','YTD','1Y','5Y','MAX']);
function isTimeframes(text){
 const parts=text.trim().split(/\s+/);
 return parts.length>=3 && parts.length<=10 && parts.every(x=>TIMEFRAME.has(x));
}
function renderMarkdown(container,source){
 const lines=cleanLines(source);let list=null,para=[],code=null;let rowTable=null;
 const flush=()=>{if(para.length){const p=element('p','');inline(p,para.join(' '));container.append(p);para=[];}list=null;rowTable=null;};
 for(const line of lines){
  const t=line.trim();
  if(t.startsWith('```')){flush();if(code){container.append(code);code=null;}else code=element('pre','');continue;}
  if(code){code.textContent+=line+'\n';continue;}
  if(!t){flush();continue;}
  if(isTimeframes(t)){flush();const chips=element('div','timeframe-chips');for(const tag of t.split(/\s+/))chips.append(element('span','',tag));container.append(chips);continue;}
  if(/^#{1,4}\s+/.test(t)){flush();const title=element('h3','');inline(title,t.replace(/^#{1,4}\s+/,''));container.append(title);continue;}
  if(/^[-*•]\s+/.test(t)||/^\d+[.)]\s+/.test(t)){if(para.length)flush();if(!list){list=element('ul','');container.append(list)}const li=element('li','');inline(li,t.replace(/^(?:[-*•]|\d+[.)])\s+/,''));list.append(li);continue;}
  if(t.startsWith('|')&&t.endsWith('|')&&t.includes('|',1)){
   if(para.length)flush();list=null;
   if(/^\|?\s*[:\-| ]+\|/.test(t))continue;
   if(!rowTable){rowTable=element('table','markdown-table');container.append(rowTable)}
   const tr=element('tr','');t.split('|').slice(1,-1).forEach(value=>tr.append(element('td','',value.trim())));
   rowTable.append(tr);continue;
  }
  para.push(t);
 }
 flush();if(code)container.append(code);
}
function getWeather(answer,question){
 if(!/weather|temperature|forecast|conditions/i.test(question))return null;
 if(/cannot (access|verify|provide).*?(weather|live|real.time)|no real.time (access|data)/i.test(answer))return null;
 const result=answer.match(/(-?\d+(?:\.\d+)?)\s*°\s*([CF])\b/);
 if(!result)return null;
 const loc=question.match(/\bin\s+([a-z][a-z .,'-]{2,36})(?:\s+today|\s+right now|[?!]|$)/i);
 const condition=(answer.match(/\b(partly cloudy|mostly cloudy|sunny|cloudy|clear skies|clear|overcast|light rain|rainy|rain|snowy|snow|showers|windy)\b/i)||[])[0]||'';
 return {title:loc?loc[1].trim():'Weather',number:result[1]+'°'+result[2],detail:condition};
}
function getStock(answer,question){
 if(!/\bTSLA\b|\btesla\b.*\b(?:stock|shares|price)\b|\bstock (?:price|quote)\b/i.test(question))return null;
 if(/(?:cannot|can't|unable to|not able to|don't have).{0,70}(?:real.time|live|current|verify|access)/i.test(answer))return null;
 const match=answer.match(/\b(?:TSLA|Tesla|stock price|share price|trading at|price|currently|last)\b[^\n\$]{0,85}\$\s*(\d[\d,]*(?:\.\d{1,4})?)/i)||answer.match(/\$\s*(\d[\d,]*(?:\.\d{1,4})?)/);
 if(!match)return null;
 const ticker=(question.match(/\b[A-Z]{2,5}\b/)||[])[0]||'TSLA';
 return {title:ticker+' · Model-reported quote',number:'$'+match[1],detail:'Market data requires independent verification'};
}
function renderAnswer(task){
 UI.answer.replaceChildren();
 UI.promptBubble.hidden=!task;UI.promptBubble.textContent=task?.prompt||'';
 const supervised=task?.provider==='chatgpt'&&task?.state==='awaiting_operator';
 const handoff=$('#chatgptHandoff');
 if(handoff){
   handoff.hidden=!supervised;
   if(supervised&&handoffTaskId!==task.id){
     handoffTaskId=task.id;
     $('#chatgptResultText').value='';
     $('#chatgptHandoffStatus').textContent='ChatGPT prompt submitted. Import the response when it is ready.';
   }
 }
 // All media is rendered once by the dedicated media-gallery module.
 UI.sources.replaceChildren();
 const state=task?.state||'idle';
 if(UI.cancelTask)UI.cancelTask.hidden=!(task&&(ACTIVE.has(state)||state==='awaiting_operator'||state==='draft'));
 UI.terminalStatus.textContent=state==='cancelled'?'CANCELLED LOCALLY':state==='answered'?'RESPONSE READY':ACTIVE.has(state)?'LIVE · '+prettyName(state):state==='failed'?'TASK FAILED':'STANDBY';
 UI.provider.textContent=task?((modelLabels.get(task.provider)||task.provider)+' · '+task.agent_id+' / '+prettyName(task.state)):'NO MODEL RESULT';
 const m=task?.metrics||{};
  UI.timing.textContent=Number.isFinite(m.total_s)?('Time '+m.total_s+'s'+(Number.isFinite(m.first_text_s)?' · first text '+m.first_text_s+'s':'')):'';
 if(!task){
  const wrap=element('div','welcome');wrap.append(element('div','welcome-glyph','✦'),element('b','','Awaiting your first command'),element('p','','Choose a model and send a task. Albedo will display the result here.'));UI.answer.append(wrap);return;
 }
 if(task.state==='cancelled'){const w=element('div','stat-card');w.append(element('div','stat-name','TASK CANCELLED'),element('p','',task.error||'Cancelled locally; a remote request may still complete outside Exodia.'));UI.answer.append(w);return;}
 if(task.state==='failed'){const w=element('div','stat-card');w.append(element('div','stat-name','MISSION FAILED'),element('p','',task.error||'The provider did not finish the task. Review the diagnostics.'));UI.answer.append(w);UI.diagnostic.textContent=task.error||'Task failed';return;}
 if(task.state!=='answered'||!task.answer){
  const w=element('div','welcome');
  const waiting=task.provider==='chatgpt'&&task.state==='awaiting_operator';
  w.append(element('div','welcome-glyph',waiting?'◉':'✧'),
    element('b','',waiting?'ChatGPT prompt submitted':prettyName(task.state)),
    element('p','',waiting?
      'This task needs operator review despite the automatic ChatGPT bridge. Deliver the response using the manual handoff panel below.':
      'Your companion is '+(moodDesc[moodForTask(task)]||'working')+'.'));
  UI.answer.append(w);return;
 }
 const answer=String(task.answer);
 const data=getStock(answer,task.prompt)||getWeather(answer,task.prompt);
 if(data){
  const card=element('div','stat-card');
  card.append(element('div','stat-name',data.title),element('div','stat-number',data.number));
  if(data.detail)card.append(element('div','stat-meta',data.detail));
  card.append(element('div','data-caveat','Extracted from model text, not independently verified live market or weather data.'));
  UI.answer.append(card);
  const details=element('details','answer-text'),summary=element('summary','','Full model response');
  details.append(summary);const body=element('div','');renderMarkdown(body,answer);details.append(body);UI.answer.append(details);
 }else{
  const box=element('div','answer-text');renderMarkdown(box,answer);UI.answer.append(box);
 }
 for(const source of task.sources||[]){
  if(!source.url?.startsWith('https://'))continue;
  const a=element('a','',source.title||source.url);a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';UI.sources.append(a);
 }
}
function updateMoodForTask(task,previous){
 if(explicitPreview&&task&&ACTIVE.has(task.state))explicitPreview=false;
 if(explicitPreview)return;
 const next=moodForTask(task);
 if(task?.state==='answered'){
  if(lastCompleted!==task.id){lastCompleted=task.id;setMood('happy');}
  return;
 }
 if(task?.state==='failed'&&previous!=='failed')setMood('failed');
 else if(!['frustration','happy','excited','proud'].includes(state)||ACTIVE.has(task?.state))setMood(next);
}
function selectTask(id){
 const previous=chosenTask?.state;
 const task=tasks.find(x=>x.id===id);
 if(!task)return;
 activeTaskId=task.id;chosenTask=task;lastInteraction=Date.now();
 document.querySelectorAll('.task-item').forEach(b=>b.classList.toggle('active',b.dataset.id===id));
 renderAnswer(task);updateMoodForTask(task,previous);refreshCommandSummary(task);
}
function renderTasks(){
 UI.taskList.replaceChildren();
 for(const task of tasks.slice(0,18)){
  const btn=element('button','task-item');btn.type='button';btn.dataset.id=task.id;
  btn.append(element('b','',task.prompt||'Untitled task'),element('span','',(modelLabels.get(task.provider)||task.provider)+' · '+task.agent_id+' · '+prettyName(task.state)));
  btn.addEventListener('click',()=>selectTask(task.id));
  UI.taskList.append(btn);
 }
 if(!tasks.length)UI.taskList.append(element('div','muted','No tasks yet.'));
}
async function loadTasks({initial=false}={}){
 const d=await api('/api/command/tasks');tasks=d.tasks||[];renderTasks();
 let current=tasks.find(t=>t.id===activeTaskId);
 if(!current&&initial)current=tasks[0];
 if(current)selectTask(current.id);
 else if(!explicitPreview){activeTaskId=null;chosenTask=null;setMood(moodForTask(null));renderAnswer(null);refreshCommandSummary(null);}
}
function browserStateLabel(snapshot){
 const state=snapshot?.status||'not_started';
 if(state==='not_started'||state==='closed')return 'Not opened';
 if(state==='needs_operator_login_or_review')return 'Open · sign-in unverified';
 if(state==='ready_for_next_prompt')return 'Last task completed';
 if(state==='launching'||state==='opening'||state==='typing'||state==='submitting')return 'Opening / working';
 if(state==='dom_error_manual_review'||state==='error'||state==='editor_unavailable')return 'Browser needs attention';
 if(state==='awaiting_operator')return 'Operator action pending';
 return prettyName(state);
}
async function refreshProviderHealth(){
 // This reports observed local session state; it does not claim authenticated
 // external-provider E2E, valid credentials or guaranteed network availability.
 const [providerStatus,sessionStatus]=await Promise.all([
  api('/api/command/providers'),api('/api/web/sessions')
 ]);
 const sessions=sessionStatus.models||{};
 const entries=[
  ['ChatGPT (chronos)',browserStateLabel(sessions.chatgpt)],
  ['Gemini (chronos)',browserStateLabel(sessions.gemini)],
  ['DeepSeek (chronos)',browserStateLabel(sessions.deepseek)],
  ['Ollama (automatic local)',providerStatus.ollama?.connected?'Local service connected':'Local service offline'],
  ['Official APIs','Not configured · no requests sent'],
  ['Advanced browser slots',Object.values(providerStatus.configured_slots||{}).filter(x=>x.configured).length+' configured']
 ];
 const container=$('#providerStatus');if(!container)return;
 container.replaceChildren();
 for(const [name,value] of entries){const row=element('div','');row.append(element('span','',name),element('strong','',value));container.append(row);}
 const checked=$('#engineChecked');if(checked)checked.textContent='Local session status · '+new Date().toLocaleTimeString();
}
async function refreshModels(){
 try{
  // Build identity must not wait on provider catalogs, browser sessions or logins.
  const build=await api('/api/build-info');
  const marker=$('#buildBadge');if(marker){marker.textContent=build.label;marker.title=build.commit_sha||'Commit unavailable; using safe fallback';}
  const identity=buildIdentity(build);$('#buildChannel').textContent=identity.channel;$('#buildShortSha').textContent=identity.sha;
  const modelData=await api('/api/command/model-options');
  const preserved=UI.model.value;
  modelLabels.clear();
  UI.model.replaceChildren();
  for(const m of modelData.options){
    modelLabels.set(m.value,m.label);
    const option=element('option','',m.label+(m.available?'':' — Not configured'));
    option.value=m.value;option.disabled=!m.available;option.dataset.transport=m.transport;
    UI.model.append(option);
  }
  const advanced=element('optgroup');advanced.label='Advanced browser slots';
  for(const m of modelData.advanced){modelLabels.set(m.value,m.label);const option=element('option','',m.label);option.value=m.value;option.dataset.transport=m.transport;advanced.append(option);}
  UI.model.append(advanced);
  UI.model.value=Array.from(UI.model.options).some(o=>o.value===preserved&&!o.disabled)?preserved:modelData.default;
  const d=await api('/api/companions');
  roster=d.agents||[];
  UI.companion.replaceChildren();
  for(const a of roster){const op=element('option','',a.name);op.value=a.id;UI.companion.append(op);}
  UI.companion.value='kiko';
  await refreshProviderHealth();
  refreshCommandSummary();
 }catch(e){UI.diagnostic.textContent='Provider status unavailable: '+e.message;}
}
$('#dispatch').addEventListener('submit',async event=>{
 event.preventDefault();if(requestInFlight)return;
 requestInFlight=true;const send=$('#sendTask');send.disabled=true;
 const payload={model_choice:UI.model.value,transport:UI.model.selectedOptions[0]?.dataset.transport||'browser',agent_id:UI.companion.value,
   prompt:UI.prompt.value.trim(),web_research:UI.research.checked,custom_instructions:$('#taskInstructions').value.trim()};
 if(!payload.prompt){inform('Enter a task first.',true);requestInFlight=false;send.disabled=false;return;}
 try{
  refreshCommandSummary({state:'submitting',agent_id:payload.agent_id,provider:payload.model_choice,prompt:payload.prompt});
  const task=await post('/api/command/tasks',payload);
  explicitPreview=false;lastCompleted=null;lastInteraction=Date.now();
  inform('Task dispatched to '+(roster.find(a=>a.id===payload.agent_id)?.name||payload.agent_id)+'.');
  await loadTasks();selectTask(task.id);
  if(task.provider==='chatgpt')inform('ChatGPT (chronos) is submitting and retrieving the response automatically; browser sign-in may require your attention.');
  else if(task.provider==='deepseek')inform('DeepSeek (chronos) is submitting and retrieving the response automatically; browser sign-in may require your attention.');
 }catch(e){inform(e.message,true);UI.diagnostic.textContent=e.message;refreshCommandSummary(chosenTask);}
 finally{requestInFlight=false;send.disabled=false;}
});
document.querySelectorAll('[data-prompt]').forEach(b=>b.addEventListener('click',()=>{UI.prompt.value=b.dataset.prompt;UI.prompt.focus();lastInteraction=Date.now();}));
$('#refreshTasks').addEventListener('click',()=>loadTasks().catch(e=>inform(e.message,true)));
UI.companion.addEventListener('change',()=>refreshCommandSummary(null));
UI.model.addEventListener('change',()=>refreshCommandSummary(chosenTask));
UI.cancelTask?.addEventListener('click',async()=>{
 const task=tasks.find(t=>t.id===activeTaskId);
 if(!task||!(ACTIVE.has(task.state)||task.state==='awaiting_operator'||task.state==='draft'))return;
 UI.cancelTask.disabled=true;
 try{
  await api('/api/command/tasks/'+encodeURIComponent(task.id)+'/cancel',{method:'POST'});
  inform('Local task cancelled; previously submitted remote requests may still complete outside Exodia.');
  await loadTasks();
 }catch(e){inform(e.message,true)}finally{UI.cancelTask.disabled=false}
});

let savedModelInstructions={};
async function showModelInstructions(provider){
 const field=$('#modelInstructions');
 if(field)field.value=savedModelInstructions[provider]||'';
}
async function loadModelInstructions(){
 try{
  const data=await api('/api/command/model-instructions');
  savedModelInstructions={};
  for(const item of data.models||[])savedModelInstructions[item.provider]=item.text||'';
  showModelInstructions($('#instructionModel').value);
 }catch(e){const status=$('#instructionStatus');if(status)status.textContent=e.message;}
}
$('#instructionModel')?.addEventListener('change',()=>showModelInstructions($('#instructionModel').value));
$('#instructionForm')?.addEventListener('submit',async event=>{
 event.preventDefault();
 const provider=$('#instructionModel').value;
 const text=$('#modelInstructions').value;
 try{
  const data=await api('/api/command/model-instructions',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider,text})});
  savedModelInstructions={};
  for(const item of data.models||[])savedModelInstructions[item.provider]=item.text||'';
  $('#instructionStatus').textContent='Saved for '+provider+'. Task responses will not include this text.';
 }catch(e){$('#instructionStatus').textContent=e.message;}
});
loadModelInstructions();
$('#openChatgptSession').addEventListener('click',async()=>{
 try{
   await api('/api/web/sessions/chatgpt/start',{method:'POST'});
   inform('ChatGPT browser is open. Complete sign-in manually if prompted.');
 }catch(e){inform(e.message,true);}
});
$('#openDeepseekSession').addEventListener('click',async()=>{
 try{
   await api('/api/web/sessions/deepseek/start',{method:'POST'});
   inform('DeepSeek browser is open. Complete sign-in manually if prompted.');
 }catch(e){inform(e.message,true);}
});
$('#chatgptImport').addEventListener('click',async()=>{
 const task=tasks.find(x=>x.id===activeTaskId);
 if(!task||task.provider!=='chatgpt'||task.state!=='awaiting_operator')return;
 const file=$('#chatgptArtifact').files?.[0];
 const answer=$('#chatgptResultText').value.trim()||(file?'Generated image attached by operator.':'');
 if(!answer){$('#chatgptHandoffStatus').textContent='Enter a ChatGPT response or choose a downloaded image.';return;}
 if(file&&(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>8*1024*1024)){
   $('#chatgptHandoffStatus').textContent='Use PNG, JPEG or WebP under 8 MiB.';return;
 }
 const btn=$('#chatgptImport');btn.disabled=true;
 try{
   await post('/api/command/tasks/'+encodeURIComponent(task.id)+'/response',{answer});
   let attachmentError=null;
   if(file){
     try{
       await api('/api/command/tasks/'+encodeURIComponent(task.id)+'/artifact',{
          method:'POST',headers:{'Content-Type':file.type},body:file});
     }catch(error){attachmentError=error.message;}
   }
   inform(attachmentError?'ChatGPT text delivered; image upload failed: '+attachmentError:
     'ChatGPT response delivered through the assigned companion.',Boolean(attachmentError));
   handoffTaskId=null;
   $('#chatgptArtifact').value='';
   await loadTasks();selectTask(task.id);
 }catch(e){$('#chatgptHandoffStatus').textContent=e.message;}
 finally{btn.disabled=false;}
});
$('#chatgptCancel').addEventListener('click',async()=>{
 const task=tasks.find(x=>x.id===activeTaskId);
 if(!task||task.provider!=='chatgpt'||task.state!=='awaiting_operator')return;
 try{
   await api('/api/command/tasks/'+encodeURIComponent(task.id)+'/cancel',{method:'POST'});
   inform('ChatGPT task cancelled; its temporary tab has been closed.');
   await loadTasks();selectTask(task.id);
 }catch(e){$('#chatgptHandoffStatus').textContent=e.message;}
});
$('#openWebSessions').addEventListener('click',async()=>{
 try{await api('/api/web/sessions/start',{method:'POST'});inform('Browser workspaces opened; sign in if the provider requires it.');}
 catch(e){inform(e.message,true);}
});
let paused=false;
setMood('idle');renderAnswer(null);refreshCommandSummary(null);
// Rejected cutout/rig stage is intentionally inactive in the public dashboard.
await refreshModels();
try{await loadTasks({initial:true})}catch(e){inform('Cannot load tasks: '+e.message,true);}
setInterval(async()=>{
 if(requestInFlight)return;
 const previous=tasks.find(t=>t.id===activeTaskId);
 if(tasks.some(t=>ACTIVE.has(t.state))){
   try{await loadTasks()}catch(e){UI.diagnostic.textContent=e.message;}
 }
 else if(!explicitPreview&&!previous&&Date.now()-lastInteraction>90000&&state!=='sleeping')setMood('sleeping');
},650);

setInterval(()=>refreshProviderHealth().catch(error=>{UI.diagnostic.textContent='Local engine status refresh failed: '+error.message;}),15000);
