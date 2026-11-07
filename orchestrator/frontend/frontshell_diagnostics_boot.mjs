/** Phase 3 local operational drilldown. Never executes or changes provider tasks. */
import {PROVIDERS} from './frontshell_telemetry_contract.mjs';
import {OperationalTimeline,classifyHealth} from './frontshell_diagnostics_contract.mjs';

function el(tag,cls,text){
  const node=document.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=text;
  return node;
}
const NAMES={chatgpt:'ChatGPT',gemini:'Gemini',deepseek:'DeepSeek',ollama:'Ollama'};
export function startFrontshellDiagnostics({doc=document,win=window,clock=()=>Date.now()}={}){
  const container=doc.getElementById('fsTelemetry');
  const cards=doc.getElementById('fsTelemetryCards');
  if(!container||!cards)return null;
  const timeline=new OperationalTimeline(80);
  let selected='chatgpt',lastSuccessAt=0,link='connecting';
  const panel=el('section','fs-drilldown');
  panel.id='fsProviderDrilldown';
  panel.setAttribute('aria-label','Read-only provider operational diagnostics');
  const header=el('div','fs-drilldown-head');
  const heading=el('h3','',NAMES[selected]+' · observed activity');
  const freshness=el('span','fs-diagnostic-freshness','NO SNAPSHOT');
  freshness.setAttribute('role','status');
  const close=el('button','fs-drilldown-close','Collapse');
  close.type='button';
  close.setAttribute('aria-expanded','true');
  header.append(heading,freshness,close);
  const details=el('div','fs-drilldown-grid');
  const tasksArea=el('div','fs-drilldown-list');
  const eventsArea=el('div','fs-drilldown-list');
  details.append(tasksArea,eventsArea);
  const help=el('p','fs-drilldown-disclaimer',
    'Local observations only · no provider authentication, reply contents or remote socket verification.');
  panel.append(header,details,help);
  container.append(panel);
  let collapsed=false;
  function paint(){
    const health=classifyHealth({lastSuccessAt,now:clock(),transport:link});
    panel.dataset.freshness=health.freshness;
    heading.textContent=NAMES[selected]+' · observed activity';
    freshness.textContent=health.freshness.toUpperCase()+
      ' · '+(health.ageMs===null?'NO SAMPLE':Math.round(health.ageMs/1000)+'s old')+
      ' · '+health.transport.toUpperCase();
    const data=timeline.byProvider(selected);
    const tasksTitle=el('h4','','Latest task states');
    const eventsTitle=el('h4','','Recent state transitions');
    const rows=data.tasks.length?data.tasks.map(task=>
      el('p','fs-diagnostic-item',task.label+' · '+task.agent+' · '+task.state.toUpperCase()))
      :[el('p','fs-diagnostic-empty','No observed tasks for this provider')];
    const events=data.events.length?data.events.map(event=>
      el('p','fs-diagnostic-item',
        new Date(event.at).toLocaleTimeString()+' · '+event.change.replace('_',' ') +
        ' · '+event.state.toUpperCase()))
      :[el('p','fs-diagnostic-empty','No observed state transitions')];
    tasksArea.replaceChildren(tasksTitle,...rows);
    eventsArea.replaceChildren(eventsTitle,...events);
    details.hidden=collapsed;help.hidden=collapsed;
    close.textContent=collapsed?'Expand':'Collapse';
    close.setAttribute('aria-expanded',String(!collapsed));
    for(const card of cards.querySelectorAll('.fs-provider-card')){
      card.dataset.selected=String(card.dataset.provider===selected&&!collapsed);
      card.setAttribute('aria-expanded',String(card.dataset.provider===selected&&!collapsed));
    }
  }
  const open=id=>{
    if(!PROVIDERS.includes(id))return false;
    selected=id;collapsed=false;paint();return true;
  };
  const onClick=event=>{
    const card=event.target?.closest?.('.fs-provider-card');
    if(card&&cards.contains(card))open(card.dataset.provider);
  };
  const onKey=event=>{
    const card=event.target?.closest?.('.fs-provider-card');
    if(card&&(event.key==='Enter'||event.key===' ')){
      event.preventDefault();open(card.dataset.provider);
    }
  };
  const onObservation=event=>{
    const data=event?.detail;
    if(!Array.isArray(data?.tasks)||!Number.isFinite(data.observedAt))return;
    try{
      timeline.accept(data.tasks,data.observedAt);
      lastSuccessAt=data.observedAt;
      if(['connected','connecting','disconnected'].includes(data.link))link=data.link;
      paint();
    }catch(_){/* no success claim for malformed observations */}
  };
  const onLink=event=>{
    if(['connected','connecting','disconnected'].includes(event?.detail?.link)){
      link=event.detail.link;paint();
    }
  };
  const onClose=()=>{collapsed=!collapsed;paint();};
  cards.addEventListener('click',onClick);
  cards.addEventListener('keydown',onKey);
  close.addEventListener('click',onClose);
  win.addEventListener('exodia:frontshell-observation',onObservation);
  win.addEventListener('exodia:frontshell-link',onLink);
  const timer=win.setInterval(paint,5000);
  if(win.__exodiaLastTelemetryObservation)
    onObservation({detail:win.__exodiaLastTelemetryObservation});
  paint();
  const runtime={
    open,refresh:paint,
    get selected(){return selected;},
    get health(){return classifyHealth({lastSuccessAt,now:clock(),transport:link});},
    get events(){return timeline.events;},
    stop(){
      win.clearInterval(timer);
      win.removeEventListener('exodia:frontshell-observation',onObservation);
      win.removeEventListener('exodia:frontshell-link',onLink);
      cards.removeEventListener('click',onClick);
      cards.removeEventListener('keydown',onKey);
      close.removeEventListener('click',onClose);
      panel.remove();
      timeline.clear();
    }
  };
  win.__exodiaPhase3Diagnostics=runtime;
  return runtime;
}
if(typeof document!=='undefined')startFrontshellDiagnostics();
