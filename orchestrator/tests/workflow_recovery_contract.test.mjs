import test from 'node:test';
import assert from 'node:assert/strict';
import {safeRecoveryFork} from '../frontend/workflow_recovery_contract.mjs';
function sample(){
  const newId='new-plan-123', source='old-plan-111';
  return {schema:'exodia.phase16.local-workflow-recovery/v1',
    lineage:{schema:'exodia.phase16.local-workflow-recovery/v1',
      source_workflow_id:source,source_revision:2,
      recovery_workflow_id:newId,reason_code:'linked_task_failed',
      source_unmodified:true,copied_task_id_count:0,
      remote_dispatch_performed:false,production_release_enabled:false,
      social_publishing_performed:false,artwork_registration_performed:false},
    workflow:{schema:'exodia.phase13.operator-workflow/v1',
      id:newId,title:'Recovery: Old plan',revision:1,
      status:'operator_planning',step_count:2,completed_task_count:0,
      operator_review_confirmed:false,external_dispatch_performed:false,
      social_publishing_performed:false,production_release_enabled:false,
      steps:[
        {key:'research',label:'Research',agent_id:'archives',
         depends_on:[],linked_task_id:null,status:'ready_for_operator_link'},
        {key:'draft',label:'Draft',agent_id:'nova',
         depends_on:['research'],linked_task_id:null,status:'blocked_on_dependencies'}
      ]}
  };
}
test('fork accepts unlinked fresh DAG with explicit lineage',()=>{
  const safe=safeRecoveryFork(sample(),'old-plan-111',2);
  assert.equal(safe.fresh.revision,1);
  assert.equal(safe.fresh.steps.length,2);
  assert.equal(safe.reason,'linked_task_failed');
});
test('refuse task carry-over, release permissions and fake provenance',()=>{
  const transforms=[
    s=>s.lineage.copied_task_id_count=1,
    s=>s.lineage.source_unmodified=false,
    s=>s.lineage.remote_dispatch_performed=true,
    s=>s.lineage.social_publishing_performed=true,
    s=>s.lineage.artwork_registration_performed=true,
    s=>s.lineage.production_release_enabled=true,
    s=>s.lineage.source_revision=1,
    s=>s.lineage.source_workflow_id='another',
    s=>s.lineage.reason_code='owner_published',
    s=>s.workflow.steps[0].linked_task_id='old-task',
    s=>s.workflow.status='reviewed_local_only',
    s=>s.workflow.revision=3,
    s=>s.workflow.completed_task_count=1,
  ];
  for(const mutate of transforms){
    const data=sample();mutate(data);
    assert.throws(()=>safeRecoveryFork(data,'old-plan-111',2));
  }
});
test('unexpected identity, malformed record and invalid revision fail closed',()=>{
  assert.throws(()=>safeRecoveryFork(null,'old-plan-111',2));
  assert.throws(()=>safeRecoveryFork(sample(),'old-plan-111',true));
  assert.throws(()=>safeRecoveryFork(sample(),'old-plan-222',2));
  const bad=sample();bad.lineage.recovery_workflow_id='wrong';
  assert.throws(()=>safeRecoveryFork(bad,'old-plan-111',2));
});
