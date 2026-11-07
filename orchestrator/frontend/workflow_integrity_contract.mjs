/* Phase 17: only safe numeric audit evidence reaches the operator UI. */
export const CODES=Object.freeze([
  'invalid_document','link_index_mismatch','orphan_link',
  'missing_task','owner_mismatch','review_drift','invalid_lineage'
]);
export function safeWorkflowIntegrity(item){
  if(!item||item.schema!=='exodia.phase17.workflow-integrity/v1'||
     item.read_only!==true||
     !['requires_operator_review','partial_sample','sample_consistent'].includes(item.status)||
     !Number.isInteger(item.total_plans)||item.total_plans<0||
     !Number.isInteger(item.total_task_links)||item.total_task_links<0||
     !Number.isInteger(item.total_recovery_forks)||item.total_recovery_forks<0||
     !Number.isInteger(item.sampled_plans)||item.sampled_plans<0||
     !Number.isInteger(item.sampled_links)||item.sampled_links<0||
     !Number.isInteger(item.sampled_recovery_forks)||item.sampled_recovery_forks<0||
     item.sampled_plans>100||item.sampled_links>500||item.sampled_recovery_forks>200||
     item.sampled_plans>item.total_plans||item.sampled_links>item.total_task_links||
     item.sampled_recovery_forks>item.total_recovery_forks||
     item.sampling_incomplete!==(item.total_plans>item.sampled_plans||
       item.total_task_links>item.sampled_links||
       item.total_recovery_forks>item.sampled_recovery_forks)||
     !item.failure_counts||Object.keys(item.failure_counts).length!==CODES.length||
     CODES.some(k=>!Number.isInteger(item.failure_counts[k])||item.failure_counts[k]<0)||
     item.total_failures!==CODES.reduce((n,k)=>n+item.failure_counts[k],0)||
     item.owner_review_required!==(item.total_failures>0||item.sampling_incomplete)||
     item.status!==(item.total_failures>0?'requires_operator_review':
       item.sampling_incomplete?'partial_sample':'sample_consistent')||
     item.provider_authentication_verified!==false||
     item.native_art_approved!==false||
     item.external_dispatch_performed!==false||
     item.social_publishing_performed!==false||
     item.production_release_enabled!==false)
    throw new Error('EXODIA integrity evidence invalid or release drift');
  const failures={};
  for(const key of CODES)failures[key]=item.failure_counts[key];
  return Object.freeze({
    status:item.status,
    inspectedPlans:item.sampled_plans,
    inspectedLinks:item.sampled_links,
    inspectedForks:item.sampled_recovery_forks,
    partial:item.sampling_incomplete,
    problems:item.total_failures,
    failures:Object.freeze(failures),
    releaseAuthorized:false
  });
}
