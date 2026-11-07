/** Four provider observation cards from existing read-only API snapshots.
 * A SINGLE local event WebSocket triggers refresh; provider-site WS is not claimed.
 */
import {sanitizeTasks} from './frontshell_diagnostics_contract.mjs';
import {PROVIDERS,ActivityHistory,projectProviders,
        sparklinePath,summariseActivity} from './frontshell_telemetry_contract.mjs';
import {boundedRetryDelay,canRefresh,observeResilience}
  from './frontshell_resilience_contract.mjs';
const NAMES=Object.freeze({chatgpt:'ChatGPT',gemini:'Gemini',deepseek:'DeepSeek',ollama:'Ollama'});
const SVG_NS='http://www.w3.org/2000/svg';
function elt(tag,cls,text){
  const node=document.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=text;
  return node;
}
function cardFor(id){
  const card=elt('article','fs-provider-card');
  card.dataset.provider=id;
  card.tabIndex=0;
  card.setAttribute('role','button');
  card.setAttribute('aria-label',NAMES[id]+' task and local session details');
  card.setAttribute('aria-controls','fsProviderDrilldown');
  const top=elt('div','fs-provider-top');
  const label=elt('div','fs-provider-label');
  const symbol=elt('span','fs-provider-emblem',id==='ollama'?'◎':'✧');
  symbol.setAttribute('aria-hidden','true');
  label.append(symbol,elt('strong','',NAMES[id]));
  const badge=elt('span','fs-socket-badge','LOCAL EVENTS OFFLINE');
  badge.dataset.link='disconnected';
  badge.title='Single EXODIA local WebSocket; NOT a verified provider socket';
  top.append(label,badge);
  const status=elt('div','fs-provider-session','Checking local state…');
  const band=elt('div','fs-provider-metrics');
  const active=elt('strong','fs-active-count','—');
  band.append(active,elt('span','','active tasks'));
  const chart=elt('div','fs-chart');
  const svg=document.createElementNS(SVG_NS,'svg');
  svg.setAttribute('viewBox','0 0 180 52');
  svg.setAttribute('preserveAspectRatio','none');
  svg.setAttribute('aria-label',NAMES[id]+' active task history, real local observations');
  svg.setAttribute('role','img');
  const baseline=document.createElementNS(SVG_NS,'path');
  baseline.setAttribute('d','M4 48 L176 48');
  baseline.setAttribute('class','fs-chart-baseline');
  const trace=document.createElementNS(SVG_NS,'path');
  trace.setAttribute('class','fs-chart-trace');
  trace.setAttribute('d','');
  svg.append(baseline,trace);
  chart.append(svg,elt('small','fs-chart-key','OBSERVED ACTIVITY · NO SAMPLES'));
  card.append(top,status,band,chart);
  return {card,badge,status,active,trace,chartKey:chart.querySelector('small')};
}

export function startFrontshellTelemetry({
  root=document.getElementById('fsTelemetry'),
  fetcher=fetch,win=window,doc=document,WebSocketType=win.WebSocket
}={}){
  if(!root)return null;
  const history=new ActivityHistory(32);
  const cards=Object.fromEntries(PROVIDERS.map(id=>[id,cardFor(id)]));
  const host=root.querySelector('#fsTelemetryCards');
  host.replaceChildren(...PROVIDERS.map(id=>cards[id].card));
  const health=root.querySelector('#fsTelemetryLink');
  const updated=root.querySelector('#fsTelemetryUpdated');
  const refreshButton=root.querySelector('#fsTelemetryRefresh');
  let link='connecting',socket=null,disposed=false;
  let snapshot=null,interval=null,retry=null,throttle=null,pending=null;
  let attempt=0,lastSuccessAt=0,failures=0,activeRequest=null,requestTimer=null;
  const browserVisible=()=>doc?.visibilityState!=='hidden';
  const browserOnline=()=>win.navigator?.onLine!==false;
  const eligible=()=>canRefresh({visible:browserVisible(),online:browserOnline()});
  const sampleHealth=()=>observeResilience({
    now:Date.now(),lastSnapshotAt:lastSuccessAt,link,
    online:browserOnline(),visible:browserVisible(),failures
  });
  function paint(){
    const compact=summariseActivity(snapshot,link);
    root.dataset.link=link;
    const readiness=sampleHealth();
    root.dataset.freshness=readiness.freshness;
    root.dataset.network=readiness.online?'online':'offline';
    try{win.dispatchEvent(new CustomEvent('exodia:frontshell-link',{detail:{link}}));}catch(_){}
    if(health){
      health.textContent=compact.transportLabel;
      health.dataset.link=link;
    }
    for(const id of PROVIDERS){
      const el=cards[id],record=snapshot?.[id];
      el.badge.textContent=link==='connected'?'EVENTS LIVE':
        link==='connecting'?'EVENTS LINKING':'EVENTS OFFLINE';
      el.badge.dataset.link=link;
      el.status.textContent=record?.session||'Snapshot pending · no authentication claim';
      el.status.dataset.health=record?.status||'unknown';
      el.card.dataset.stale=String(readiness.freshness!=='fresh');
      el.active.textContent=record?String(record.active):'—';
      const points=history.series[id];
      el.trace.setAttribute('d',sparklinePath(points));
      el.chartKey.textContent=points.length
        ?'OBSERVED TASKS · '+points.length+' SAMPLE'+(points.length===1?'':'S')
        :'OBSERVED TASKS · NO SAMPLES';
    }
  }
  async function read(url,signal){
    const response=await fetcher(url,{method:'GET',cache:'no-store',signal});
    if(!response.ok)throw Error('Local telemetry snapshot unavailable');
    return response.json();
  }
  async function refresh({force=false}={}){
    if(disposed||(!force&&!eligible()))return;
    if(pending)return pending;
    pending=(async()=>{
      const controller=new AbortController();
      activeRequest=controller;
      requestTimer=win.setTimeout(()=>controller.abort(),7000);
      try{
        const [providers,sessions,tasks]=await Promise.all([
          read('/api/command/providers',controller.signal),
          read('/api/web/sessions',controller.signal),
          read('/api/command/tasks',controller.signal)
        ]);
        const next=projectProviders(providers,sessions,tasks);
        if(disposed)return;
        snapshot=next;
        history.append(snapshot);
        root.dataset.ready='1';
        failures=0;
        lastSuccessAt=Date.now();
        try{
          // Only allowlisted task keys/states/agents; never publish prompt/results.
          const observation={tasks:sanitizeTasks(tasks),observedAt:lastSuccessAt,link};
          win.__exodiaLastTelemetryObservation=observation;
          win.dispatchEvent(new CustomEvent('exodia:frontshell-observation',{
            detail:observation
          }));
        }catch(_){/* Local diagnostics must not break provider telemetry. */}
        if(updated)updated.textContent='Snapshot: '+new Date(lastSuccessAt).toLocaleTimeString()+
          ' · Local service observations, not vendor authentication';
        paint();
      }catch(_){
        if(disposed)return;
        failures++;
        root.dataset.ready=snapshot?'stale':'error';
        if(updated)updated.textContent='Telemetry unavailable · last snapshot may be stale';
        try{win.dispatchEvent(new CustomEvent('exodia:frontshell-snapshot-error',{detail:{failed:true}}));}catch(_){}
        paint();
      }finally{
        if(requestTimer!==null)win.clearTimeout(requestTimer);
        requestTimer=null;activeRequest=null;pending=null;
      }
    })();
    return pending;
  }
  function invalidate(){
    if(disposed||!eligible()||throttle!==null)return;
    throttle=win.setTimeout(()=>{
      throttle=null;
      void refresh();
    },700);
  }
  function connect(){
    if(retry!==null){win.clearTimeout(retry);retry=null;}
    if(disposed||!WebSocketType||!eligible()){
      link='disconnected';paint();return;
    }
    if(socket&&socket.readyState===1)return;
    link='connecting';paint();
    try{
      const scheme=win.location?.protocol==='https:'?'wss:':'ws:';
      const host=win.location?.host||'';
      socket=new WebSocketType(scheme+'//'+host+'/ws/events');
      const candidate=socket;
      socket.onopen=()=>{
        if(disposed||socket!==candidate)return;
        link='connected';attempt=0;paint();invalidate();
      };
      socket.onmessage=event=>{
        // Payload is never rendered or stored. Kind only invalidates GETs.
        try{
          const message=JSON.parse(event.data);
          if(['task','companion','status','alert'].includes(message?.kind))
            invalidate();
        }catch(_){/* ignore malformed/injected event frames */}
      };
      socket.onerror=()=>{if(!disposed&&socket===candidate)candidate.close();};
      socket.onclose=()=>{
        if(disposed||socket!==candidate)return;
        socket=null;link='disconnected';paint();
        if(eligible())retry=win.setTimeout(connect,boundedRetryDelay(attempt++));
      };
    }catch(_){
      socket=null;link='disconnected';paint();
      if(eligible())retry=win.setTimeout(connect,boundedRetryDelay(attempt++));
    }
  }
  function closeLocalSocket(){
    if(retry!==null){win.clearTimeout(retry);retry=null;}
    if(throttle!==null){win.clearTimeout(throttle);throttle=null;}
    if(socket){
      const closing=socket;socket=null;
      closing.onclose=null;closing.onmessage=null;
      try{closing.close();}catch(_){}
    }
    if(activeRequest)activeRequest.abort();
    link='disconnected';paint();
  }
  const onConnectivity=()=>{
    if(disposed)return;
    if(!eligible())closeLocalSocket();
    else{attempt=0;connect();void refresh();}
  };
  const onVisibility=()=>onConnectivity();
  refreshButton?.addEventListener('click',()=>{void refresh({force:true});});
  win.addEventListener('online',onConnectivity);
  win.addEventListener('offline',onConnectivity);
  doc?.addEventListener?.('visibilitychange',onVisibility);
  paint();
  connect();
  void refresh();
  interval=win.setInterval(()=>{if(eligible())void refresh();},9000);
  const runtime={
    refresh,
    summary:()=>summariseActivity(snapshot,link),
    get history(){return history.all();},
    get snapshot(){return snapshot;},
    get readiness(){return sampleHealth();},
    stop(){
      if(disposed)return;
      disposed=true;
      win.clearInterval(interval);
      win.removeEventListener('online',onConnectivity);
      win.removeEventListener('offline',onConnectivity);
      doc?.removeEventListener?.('visibilitychange',onVisibility);
      closeLocalSocket();
      if(requestTimer!==null)win.clearTimeout(requestTimer);
    }
  };
  win.__exodiaPhase2Telemetry=runtime;
  return runtime;
}
if(typeof document!=='undefined')startFrontshellTelemetry();
