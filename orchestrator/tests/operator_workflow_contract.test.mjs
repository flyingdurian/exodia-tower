import test from 'node:test';
import assert from 'node:assert/strict';
import {safeWorkflow, AGENTS} from '../frontend/operator_workflow_contract.mjs';

function plan() {
  return {
    schema:'exodia.phase13.operator-workflow/v1',id:'id-111',
    title:'Test Operator Plan',revision:2,status:'operator_planning',
    step_count:3,completed_task_count:1,
    operator_review_confirmed:false,
    external_dispatch_performed:false,
    social_publishing_performed:false,
    production_release_enabled:false,
    steps:[
      {key:'research',label:'Gather provenance',agent_id:'archives',
       depends_on:[],linked_task_id:'task-abc',status:'answered_pending_review'},
      {key:'assess',label:'Assess reliability',agent_id:'strategy',
       depends_on:['research'],linked_task_id:'task-def',status:'linked_task_in_progress'},
      {key:'draft',label:'Prepare proposal',agent_id:'nova',
       depends_on:['assess'],linked_task_id:null,status:'blocked_on_dependencies'},
    ],
  };
}
test('strict workflow projection contains 3 genuine stages, no external actions',()=>{
  const safe=safeWorkflow(plan());
  assert.equal(safe.completed,1);
  assert.equal(safe.stepCount,3);
  assert.equal(safe.steps[0].agentId,'archives');
  assert.equal(safe.steps[2].status,'blocked_on_dependencies');
  assert.equal(AGENTS.length,10);
  assert.equal(JSON.stringify(safe).includes('external_dispatch_performed'),false);
  assert.ok(Object.isFrozen(safe.steps));
});
test('review status requires all tasks answered',()=>{
  const x=plan();
  x.status='reviewed_local_only';
  x.operator_review_confirmed=true;
  assert.throws(()=>safeWorkflow(x),/evidence/);
  x.completed_task_count=3;
  x.steps[1].status='answered_pending_review';
  x.steps[2].status='answered_pending_review';
  x.steps[2].linked_task_id='task-ghi';
  const safe=safeWorkflow(x);
  assert.equal(safe.status,'reviewed_local_only');
  assert.equal(safe.completed,3);
});
test('forged dispatch, release, publishing and completion count are rejected',()=>{
  for(const [field,value] of [
    ['production_release_enabled',true],
    ['social_publishing_performed',true],
    ['external_dispatch_performed',true],
    ['completed_task_count',3],
    ['step_count',4],
    ['revision',0],
  ]){
    const x=plan();
    x[field]=value;
    assert.throws(()=>safeWorkflow(x));
  }
});
test('invalid dependency order, re-used taskless answered state or agent drift fails',()=>{
  const fns=[
    p=>{p.steps[0].depends_on=['draft'];},
    p=>{p.steps[1].agent_id='router';},
    p=>{p.steps[0].linked_task_id=null;},
    p=>{p.steps[2].linked_task_id='task-illegal';},
    p=>{p.steps[2].key='research';},
    p=>{p.steps[1].depends_on=['research','research'];},
    p=>{p.steps[2].status='approved_for_publish';},
  ];
  for(const change of fns){
    const x=plan();
    change(x);
    assert.throws(()=>safeWorkflow(x));
  }
});
