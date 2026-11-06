/* Operator-only bounded health; no media, provider or workflow mutations. */
import {safeWorkflowHealth} from './workflow_health_contract.mjs';

const status = document.getElementById('workflowHealthStatus');
const metrics = document.getElementById('workflowHealthMetrics');
const button = document.getElementById('workflowHealthRefresh');
let lastRefresh = 0;
let currentRequest = 0;

function metric(name, value){
  const tag = document.createElement('span');
  tag.className = 'tag';
  tag.textContent = name + ': ' + String(value);
  return tag;
}

async function refresh(){
  const serial=++currentRequest;
  button.disabled=true;
  status.textContent='Inspecting local SQLite workflow integrity…';
  try{
    const response=await fetch('/api/operations/workflow-health', {
      headers:{'X-Exodia-Client':'exodia-dashboard'}
    });
    if(!response.ok)throw new Error('health unavailable');
    const report=safeWorkflowHealth(await response.json());
    if(serial!==currentRequest)return;
    metrics.replaceChildren(
      metric('Plans',report.total),
      metric('Linked tasks',report.linked),
      metric('Answered',report.counts.answered),
      metric('In progress',report.counts.active),
      metric('Failed',report.counts.failed),
      metric('Not linked',report.counts.unlinked)
    );
    lastRefresh=Date.now();
    if(report.status==='review_required'){
      status.textContent='Local workflow records require review · invalid: '+
        report.invalid+' · unverified links: '+report.counts.unverified;
    }else if(report.status==='no_plans'){
      status.textContent='No operator workflows saved yet · no external tasks sent';
    }else{
      status.textContent='Local workflow health available · sampled '+
        report.sampled+' plans'+(report.partial?' (partial sample)':'')+
        ' · external dispatch disabled';
    }
  }catch(_){
    if(serial!==currentRequest)return;
    metrics.replaceChildren();
    status.textContent='Workflow health unavailable · no readiness claim';
  }finally{
    if(serial===currentRequest)button.disabled=false;
  }
}
button?.addEventListener('click',()=>{void refresh();});
window.addEventListener('focus',()=>{
  if(Date.now()-lastRefresh>30000)void refresh();
});
window.addEventListener('exodia:workflow-change',()=>{
  void refresh();
});
if(button && status && metrics)void refresh();
