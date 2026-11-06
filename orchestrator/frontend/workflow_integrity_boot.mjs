/* Operator-initiated audit only; never schedules repair or external actions. */
import {safeWorkflowIntegrity} from './workflow_integrity_contract.mjs';
const trigger=document.getElementById('workflowIntegrityRun');
const status=document.getElementById('workflowIntegrityStatus');
let revision=0;
async function inspect(){
  if(!trigger||!status)return;
  const serial=++revision;
  trigger.disabled=true;
  status.textContent='Verifying local workflow documents, indices and task ownership…';
  try{
    const response=await fetch('/api/operations/workflow-integrity',{
      headers:{'X-Exodia-Client':'exodia-dashboard'}
    });
    if(!response.ok)throw new Error('Integrity audit unavailable');
    const safe=safeWorkflowIntegrity(await response.json());
    if(serial!==revision)return;
    const count=safe.inspectedPlans+' plans / '+safe.inspectedLinks+
      ' links / '+safe.inspectedForks+' recovery forks inspected';
    status.textContent=safe.status==='requires_operator_review'
      ? 'Operator review required: '+safe.problems+' violations · '+count
      : safe.status==='partial_sample'
      ? 'Partial sample only · '+count+' · no full integrity claim'
      : 'Sample consistent · '+count+' · no production release authorized';
  }catch(_){
    if(serial===revision)status.textContent=
      'Integrity check unavailable · no success or release claim';
  }finally{
    if(serial===revision)trigger.disabled=false;
  }
}
trigger?.addEventListener('click',()=>{void inspect();});
