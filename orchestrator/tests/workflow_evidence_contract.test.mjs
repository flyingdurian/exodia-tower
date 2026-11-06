import test from 'node:test';
import assert from 'node:assert/strict';
import {safeWorkflowEvidence} from '../frontend/workflow_evidence_contract.mjs';

function evidence(){
  return {
    schema:'exodia.phase14.workflow-task-evidence/v1',
    workflow_id:'workflow-123',revision:2,
    workflow_status:'operator_planning',
    step_count:2,answered_task_count:1,answered_event_recorded_count:1,
    operator_link_ready_count:1,failed_linked_task_count:0,
    operator_review_confirmed:false,
    all_tasks_answered:false,
    all_answered_events_corroborated:false,
    next_operator_action:'link_existing_tasks_manually',
    authenticated_provider_acceptance:'not_established',
    external_dispatch_performed:false,social_publishing_performed:false,
    production_release_enabled:false,read_only:true,
    steps:[
      {key:'first',agent_id:'vault',task_id:'id-1',
       step_status:'answered_pending_review',task_lifecycle:'answered',
       audit_evidence:'answered_event_recorded',answer_event_kind:'state_change',
       provider_authentication_verified:false,owner_external_action_approval:false},
      {key:'next',agent_id:'nova',task_id:null,
       step_status:'ready_for_operator_link',task_lifecycle:'unlinked',
       audit_evidence:'no_linked_task',answer_event_kind:null,
       provider_authentication_verified:false,owner_external_action_approval:false},
    ]
  };
}
test('two safe task states never expose source text or owner approval',()=>{
  const result=safeWorkflowEvidence(evidence());
  assert.equal(result.answered,1);
  assert.equal(result.ready,1);
  assert.equal(result.confirmed,1);
  assert.equal(JSON.stringify(result).includes('task_id'),false);
  assert.ok(Object.isFrozen(result.steps));
});
test('missing task event provenance may not become a confirmed success',()=>{
  const v=evidence();
  v.answered_event_recorded_count=0;
  v.steps[0].audit_evidence='answered_without_event_proof';
  v.steps[0].answer_event_kind=null;
  assert.equal(safeWorkflowEvidence(v).confirmed,0);
  const forbidden=evidence();
  forbidden.answered_event_recorded_count=0;
  assert.throws(()=>safeWorkflowEvidence(forbidden));
});
test('external-action, art and fake-auth statuses fail closed',()=>{
  for(const [field,value] of [
    ['external_dispatch_performed',true],
    ['production_release_enabled',true],
    ['social_publishing_performed',true],
    ['authenticated_provider_acceptance','authenticated'],
  ]){
    const copy=evidence();
    copy[field]=value;
    assert.throws(()=>safeWorkflowEvidence(copy));
  }
});
test('forged per-step permission, wrong counted readiness, or missing task rejected',()=>{
  const changes=[
    x=>x.steps[0].provider_authentication_verified=true,
    x=>x.steps[0].answer_event_kind='owner_confirmed',
    x=>x.steps[0].task_id=null,
    x=>x.steps[1].audit_evidence='answered_event_recorded',
    x=>x.operator_link_ready_count=0,
    x=>x.all_tasks_answered=true,
    x=>x.steps[0].owner_external_action_approval=true,
  ];
  for(const change of changes){const v=evidence();change(v);
    assert.throws(()=>safeWorkflowEvidence(v));}
});
