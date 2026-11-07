import test from 'node:test';
import assert from 'node:assert/strict';
import {safeWorkflowIntegrity,CODES} from '../frontend/workflow_integrity_contract.mjs';
function good(){
  return {schema:'exodia.phase17.workflow-integrity/v1',read_only:true,
    status:'sample_consistent',total_plans:3,total_task_links:2,
    total_recovery_forks:1,sampled_plans:3,sampled_links:2,
    sampled_recovery_forks:1,sampling_incomplete:false,
    failure_counts:Object.fromEntries(CODES.map(code=>[code,0])),
    total_failures:0,owner_review_required:false,
    provider_authentication_verified:false,native_art_approved:false,
    external_dispatch_performed:false,social_publishing_performed:false,
    production_release_enabled:false};
}
test('valid complete integrity sample does not authorize production',()=>{
  const x=safeWorkflowIntegrity(good());
  assert.equal(x.inspectedPlans,3);
  assert.equal(x.releaseAuthorized,false);
  assert.ok(Object.isFrozen(x.failures));
  assert.equal(JSON.stringify(x).includes('task_id'),false);
});
test('partial sampling must not pretend full integrity',()=>{
  const x=good();x.total_plans=101;x.sampled_plans=100;
  x.sampling_incomplete=true;x.owner_review_required=true;
  x.status='partial_sample';
  assert.equal(safeWorkflowIntegrity(x).partial,true);
  const forged=good();forged.total_plans=101;forged.sampled_plans=100;
  assert.throws(()=>safeWorkflowIntegrity(forged));
});
test('corrupted task-link counts must visibly trigger operator review',()=>{
  const x=good();
  x.failure_counts.owner_mismatch=1;x.total_failures=1;
  x.status='requires_operator_review';x.owner_review_required=true;
  assert.equal(safeWorkflowIntegrity(x).problems,1);
  x.total_failures=0;
  assert.throws(()=>safeWorkflowIntegrity(x));
});
test('forged credentials, artwork, publication or approval fail closed',()=>{
  for(const field of ['provider_authentication_verified','native_art_approved',
    'external_dispatch_performed','social_publishing_performed',
    'production_release_enabled']){
    const x=good();x[field]=true;
    assert.throws(()=>safeWorkflowIntegrity(x));
  }
  const x=good();x.failure_counts.private_source='SECRET';
  assert.throws(()=>safeWorkflowIntegrity(x));
});
