'use strict';
const $ = (selector)=>document.querySelector(selector);
const $$ = (selector)=>Array.from(document.querySelectorAll(selector));
let busy = false;
const statuses = {idle:['☾','IDLE · DREAMING OF QUESTS','Standing by for your next brilliant idea. Maybe after one tiny nap...'],battle:['⚔','BATTLE · ON THE CASE','Quest underway! My tiny paws are moving at maximum speed.'],rest:['🍱','RESTING · CACHE HIT','Found it in the archives! That was a deliciously quick quest.'],panic:['!','PANIC · RECOVERY','An unexpected obstacle! I have captured the issue and checked the fallback.']};
function setKiko(state){
  const [icon,label,caption] = statuses[state] || statuses.idle;
  $('#kiko').dataset.state = state;
  $('#stateDot').textContent=icon; $('#mascotStatus').textContent=label; $('#mascotCaption').textContent=caption;
  $('#kiko').setAttribute('aria-label', `Kiko the chibi mascot in ${state} mode`);
}
function localizedTime(iso){try{return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Vancouver',hour:'numeric',minute:'2-digit'}).format(new Date(iso))}catch{return '--'}}
function paintEvents(events){
  const container=$('#timeline'); container.replaceChildren();
  if(!events.length){container.textContent='No events yet.';return}
  for(const evt of events.slice(0,7)){
    const item=document.createElement('div');item.className='timeline-item';
    const mark=document.createElement('span');mark.className='timeline-mark '+evt.kind;
    mark.textContent = ({success:'✓',alert:'!',task:'⚔',system:'✦'})[evt.kind]||'✧';
    const content=document.createElement('div');content.className='timeline-content';
    const top=document.createElement('div');top.className='timeline-top';
    const title=document.createElement('strong');title.textContent=evt.message;
    const time=document.createElement('time');time.textContent=localizedTime(evt.at);
    const detail=document.createElement('p');detail.textContent=evt.detail||evt.kind;
    top.append(title,time);content.append(top,detail);item.append(mark,content);container.append(item);
  }
}
async function fetchJSON(url, options={}){
  const res=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});
  if(!res.ok)throw Error('Server returned HTTP '+res.status);
  return res.json();
}
async function loadStats(){
  try{
    const stats=await fetchJSON('/api/stats');
    $('#chunkStat').textContent=stats.indexed_chunks.toLocaleString();
    $('#cacheStat').textContent=stats.cache_entries.toLocaleString();
    $('#routeStat').textContent=stats.last_route==='idle'?'Idle':stats.last_route;
    $('#uptimeStat').textContent=stats.uptime_seconds<3600 ? `${Math.floor(stats.uptime_seconds/60)}m`: `${(stats.uptime_seconds/3600).toFixed(1)}h`;
    const availability=stats.config.integrations||{};
    for(const [name,on] of Object.entries(availability)){
      const el=$(`[data-status="${name}"]`);
      if(el && !el.classList.contains('verified') && !el.classList.contains('failed')){
        el.textContent=on?'KEY SET':'UNCONFIGURED';el.classList.toggle('configured',on);
      }
    }
    const provider=$('#channel option[value="browser"]');
    provider.textContent=stats.config.browser_enabled ? '◉ Browser' : '◉ Browser (off)';
  }catch(e){console.warn('Status unavailable:',e.message)}
}
function showAnswer(result){
  $('#responsePanel').hidden=false;
  const meta = `${(result.route||'unknown').toUpperCase()} · ${result.latency_ms||0} ms ${result.cache_hit?'· CACHE HIT':''}`;
  $('#resultMeta').textContent=meta;
  const duration=Number(result.latency_ms)||0;
  $('#latencyValue').textContent=duration?`${duration} ms`:'—';
  $('#latencyFill').style.width=duration?`${Math.max(2,Math.min(100,(duration/3000)*100))}%`:'0%';
  $('#responseText').textContent=result.answer || 'No content returned.';
  $('#responseData').hidden=!result.data;
  $('#responseData').textContent=result.data?JSON.stringify(result.data,null,2):'';
  $('#responsePanel').scrollIntoView({behavior:'smooth',block:'nearest'});
}
async function runQuest(question,channel='auto'){
  if(busy)return;
  busy=true;setKiko('battle');$('#submitBtn').disabled=true;$('#submitBtn').textContent='On the case…';
  try{
    const res=await fetchJSON('/api/ask',{method:'POST',body:JSON.stringify({question,channel})});
    showAnswer(res);setKiko(res.error || res.data?.browser_error?'panic':res.cache_hit?'rest':'idle');
    await refreshEvents(); await loadStats();
  }catch(e){setKiko('panic');showAnswer({answer:e.message,route:'error',error:true});}
  finally{busy=false;$('#submitBtn').disabled=false;$('#submitBtn').innerHTML='Launch quest <span>↗</span>'}
}
async function refreshSnapshots(){
  try{const result=await fetchJSON('/api/snapshots');
    $('#snapshotRow').hidden=!result.latest;
    if(result.latest){$('#snapshotLink').href='/api/snapshots/'+encodeURIComponent(result.latest)}
  }catch(e){console.warn('Snapshot list unavailable:',e.message)}
}
async function refreshEvents(){try{const data=await fetchJSON('/api/events');paintEvents(data.events)}catch(e){console.warn(e.message)}}
$('#askForm').addEventListener('submit',(e)=>{e.preventDefault();const q=$('#question').value.trim();if(q.length>1)runQuest(q,$('#channel').value)});
$$('[data-prompt]').forEach(btn=>btn.addEventListener('click',()=>{$('#question').value=btn.dataset.prompt;runQuest(btn.dataset.prompt)}));
$$('[data-check]').forEach(btn=>btn.addEventListener('click',async()=>{
  if(busy)return;busy=true;btn.disabled=true;setKiko('battle');
  const name=btn.dataset.check;
  try{
    const res=await fetchJSON(`/api/integrations/${name}/check`,{method:'POST'});
    showAnswer(res);
    const el=$(`[data-status="${name}"]`);
    el.classList.remove('configured','verified','failed');el.classList.add(res.error?'failed':'verified');
    el.textContent=res.error?'NEEDS SETUP':'VERIFIED';setKiko(res.error?'panic':'idle');
    await refreshEvents();await loadStats();
  }catch(err){setKiko('panic');showAnswer({answer:err.message,route:name,error:true})}
  finally{busy=false;btn.disabled=false}
}));
$('#indexBtn').addEventListener('click',async()=>{
  $('#indexBtn').disabled=true;setKiko('battle');$('#indexBtn').textContent='Indexing...';
  try{const r=await fetchJSON('/api/index',{method:'POST'});showAnswer({route:'local archive',answer:`Indexed ${r.files} files into ${r.chunks} chunks. ${r.errors} file errors. Dense search: ${r.dense_enabled?'enabled':'off (FTS5 active)'}.`,data:r});setKiko('idle');}
  catch(e){setKiko('panic');showAnswer({answer:e.message,route:'index',error:true})}
  finally{$('#indexBtn').disabled=false;$('#indexBtn').textContent='✧ Index workspace';await loadStats();await refreshEvents()}
});
$('#clearCache').addEventListener('click',async()=>{
  try{await fetchJSON('/api/cache/clear',{method:'POST'});setKiko('rest');await refreshEvents();await loadStats()}
  catch(e){setKiko('panic')}
});
$$('[data-go]').forEach(link=>link.addEventListener('click',()=>{
  $$('.nav-link').forEach(btn=>btn.classList.toggle('active',btn===link));
  document.getElementById(link.dataset.go)?.scrollIntoView({behavior:'smooth',block:'start'});
}));
const clock=()=>{$('#localDate').textContent=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Vancouver',weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date())};
clock();setInterval(clock,60000);loadStats();refreshEvents();refreshSnapshots();setInterval(loadStats,15000);setInterval(refreshSnapshots,15000);
function connectEvents(){
  const url=(location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/ws/events';
  const sock=new WebSocket(url);
  sock.onmessage=()=>refreshEvents();
  sock.onclose=()=>setTimeout(connectEvents,4000);
}
connectEvents();
