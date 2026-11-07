/** Four provider observation cards from existing read-only API snapshots.
 * A SINGLE local event WebSocket triggers refresh; provider-site WS is not claimed.
 */
import {PROVIDERS,ActivityHistory,projectProviders,
        sparklinePath,summariseActivity} from './frontshell_telemetry_contract.mjs';
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
  fetcher=fetch,win=window,WebSocketType=win.WebSocket
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
  let retryDelay=1800;
  function paint(){
    const compact=summariseActivity(snapshot,link);
    root.dataset.link=link;
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
      el.active.textContent=record?String(record.active):'—';
      const points=history.series[id];
      el.trace.setAttribute('d',sparklinePath(points));
      el.chartKey.textContent=points.length
        ?'OBSERVED TASKS · '+points.length+' SAMPLE'+(points.length===1?'':'S')
        :'OBSERVED TASKS · NO SAMPLES';
    }
  }
  async function read(url){
    const response=await fetcher(url,{method:'GET',cache:'no-store'});
    if(!response.ok)throw Error('Local telemetry snapshot unavailable');
    return response.json();
  }
  async function refresh(){
    if(disposed)return;
    if(pending)return pending;
    pending=(async()=>{
      try{
        const [providers,sessions,tasks]=await Promise.all([
          read('/api/command/providers'),read('/api/web/sessions'),
          read('/api/command/tasks')
        ]);
        const next=projectProviders(providers,sessions,tasks);
        if(disposed)return;
        snapshot=next;
        history.append(snapshot);
        root.dataset.ready='1';
        if(updated)updated.textContent='Snapshot: '+new Date().toLocaleTimeString()+
          ' · Local service observations, not vendor authentication';
        paint();
      }catch(_){
        if(disposed)return;
        root.dataset.ready=snapshot?'stale':'error';
        if(updated)updated.textContent='Telemetry unavailable · last snapshot may be stale';
        paint();
      }finally{pending=null;}
    })();
    return pending;
  }
  function invalidate(){
    if(disposed||throttle!==null)return;
    throttle=win.setTimeout(()=>{
      throttle=null;
      void refresh();
    },700);
  }
  function connect(){
    if(disposed||!WebSocketType){
      link='disconnected';paint();return;
    }
    link='connecting';paint();
    try{
      const scheme=win.location?.protocol==='https:'?'wss:':'ws:';
      const host=win.location?.host||'';
      socket=new WebSocketType(scheme+'//'+host+'/ws/events');
      socket.onopen=()=>{
        if(disposed)return;
        link='connected';retryDelay=1800;paint();invalidate();
      };
      socket.onmessage=event=>{
        // Payload is never rendered or stored. Kind only invalidates GETs.
        try{
          const message=JSON.parse(event.data);
          if(['task','companion','status','alert'].includes(message?.kind))
            invalidate();
        }catch(_){/* ignore malformed/injected event frames */}
      };
      socket.onerror=()=>{if(!disposed)socket?.close();};
      socket.onclose=()=>{
        if(disposed)return;
        link='disconnected';paint();
        retry=win.setTimeout(connect,retryDelay);
        retryDelay=Math.min(15000,retryDelay*2);
      };
    }catch(_){
      link='disconnected';paint();
      retry=win.setTimeout(connect,retryDelay);
      retryDelay=Math.min(15000,retryDelay*2);
    }
  }
  refreshButton?.addEventListener('click',()=>{void refresh();});
  paint();
  connect();
  void refresh();
  interval=win.setInterval(()=>{void refresh();},9000);
  const runtime={
    refresh,
    summary:()=>summariseActivity(snapshot,link),
    get history(){return history.all();},
    get snapshot(){return snapshot;},
    stop(){
      disposed=true;
      win.clearInterval(interval);
      if(retry!==null)win.clearTimeout(retry);
      if(throttle!==null)win.clearTimeout(throttle);
      if(socket){socket.onclose=null;socket.onmessage=null;socket.close();}
    }
  };
  win.__exodiaPhase2Telemetry=runtime;
  return runtime;
}
if(typeof document!=='undefined')startFrontshellTelemetry();
