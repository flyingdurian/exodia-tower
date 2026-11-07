/** Phase 6 read-only release cockpit. Cannot unlock artwork or provider sessions. */
import {observeResilience} from './frontshell_resilience_contract.mjs';
export function startFrontshellResilience({doc=document,win=window,clock=()=>Date.now()}={}){
  const telemetry=doc.getElementById('fsTelemetry');
  if(!telemetry)return null;
  const section=doc.createElement('section');
  section.id='fsReliability';
  section.className='fs-reliability';
  section.setAttribute('aria-label','Technical release candidate connection and readiness');
  const headline=doc.createElement('div');headline.className='fs-release-heading';
  const title=doc.createElement('strong');
  title.textContent='RELEASE CANDIDATE · TECHNICAL READINESS';
  const approval=doc.createElement('span');
  approval.textContent='ART & WINDOWS ACCEPTANCE PENDING';
  headline.append(title,approval);
  const indicators=doc.createElement('div');indicators.className='fs-release-indicators';
  const items={};
  for(const [key,name] of [
    ['stream','LOCAL EVENTS'],['freshness','TASK SNAPSHOT'],
    ['art','CHIBI ART'],['operator','WINDOWS QA']
  ]){
    const pill=doc.createElement('div');pill.className='fs-release-item';
    pill.dataset.check=key;
    const label=doc.createElement('small');label.textContent=name;
    const status=doc.createElement('strong');status.textContent='UNVERIFIED';
    pill.append(label,status);indicators.append(pill);items[key]=status;
  }
  const foot=doc.createElement('p');foot.className='fs-release-note';
  foot.textContent='Local-only reliability signals. A linked event socket does not verify a third-party provider login. Production art and Windows acceptance remain separate gates.';
  section.append(headline,indicators,foot);
  telemetry.insertAdjacentElement('afterend',section);
  let stamp=0,failures=0,link='disconnected';
  const getOnline=()=>win.navigator?.onLine!==false;
  const visible=()=>doc.visibilityState!=='hidden';
  function paint(){
    const runtime=win.__exodiaPhase2Telemetry;
    if(runtime?.summary)link=runtime.summary().link;
    const last=win.__exodiaLastTelemetryObservation?.observedAt;
    if(Number.isFinite(last)&&last>stamp)stamp=last;
    const health=observeResilience({
      now:clock(),lastSnapshotAt:stamp,link,online:getOnline(),
      visible:visible(),failures
    });
    section.dataset.freshness=health.freshness;
    section.dataset.link=health.link;
    items.stream.textContent=health.state;
    items.freshness.textContent=health.snapshotLabel+
      ' · '+health.freshness.toUpperCase();
    items.art.textContent='40 NATIVE FRAMES · NOT RELEASED';
    items.operator.textContent='LOCAL WINDOWS SIGN-OFF PENDING';
    return health;
  }
  const onObservation=event=>{
    const time=event?.detail?.observedAt;
    if(Number.isFinite(time)&&time>0)stamp=Math.max(stamp,time);
    failures=0;paint();
  };
  const onLink=event=>{
    if(['connected','connecting','disconnected'].includes(event?.detail?.link)){
      link=event.detail.link;paint();
    }
  };
  const onError=()=>{failures++;paint();};
  win.addEventListener('exodia:frontshell-observation',onObservation);
  win.addEventListener('exodia:frontshell-link',onLink);
  win.addEventListener('exodia:frontshell-snapshot-error',onError);
  win.addEventListener('online',paint);
  win.addEventListener('offline',paint);
  doc.addEventListener('visibilitychange',paint);
  const timer=win.setInterval(paint,5000);
  paint();
  const api={get health(){return paint();},refresh:paint,stop(){
    win.clearInterval(timer);
    win.removeEventListener('exodia:frontshell-observation',onObservation);
    win.removeEventListener('exodia:frontshell-link',onLink);
    win.removeEventListener('exodia:frontshell-snapshot-error',onError);
    win.removeEventListener('online',paint);
    win.removeEventListener('offline',paint);
    doc.removeEventListener('visibilitychange',paint);
    section.remove();
  }};
  win.__exodiaPhase6Readiness=api;
  return api;
}
if(typeof document!=='undefined')startFrontshellResilience();
