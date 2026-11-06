import test from 'node:test';
import assert from 'node:assert/strict';
import {safeWorkflowHealth} from '../frontend/workflow_health_contract.mjs';

function evidence(){
  return {schema:'exodia.phase15.operator-workflow-health/v1',
    read_only:true,status:'operational',
    total_workflow_plans:4,total_persisted_task_links:8,
    sampled_workflow_plans:4,sample_limit:100,
    sample_may_be_incomplete:false,
    invalid_workflow_documents:0,sampled_reviewed_plans:1,
    sampled_step_counts:{unlinked:3,answered:2,failed:1,active:2,unverified:0},
    production_release_enabled:false,remote_dispatch_performed:false,
    social_publishing_performed:false,
    authenticated_provider_acceptance:'not_established'
  };
}
test('safe fleet health is bounded read-only and excludes task secrets',()=>{
  const report=safeWorkflowHealth(evidence());
  assert.equal(report.total,4);
  assert.equal(report.counts.answered,2);
  assert.equal(report.counts.unverified,0);
  assert.ok(Object.isFrozen(report.counts));
  assert.equal(JSON.stringify(report).includes('authenticated_provider'),false);
});
test('unsafe externally empowered reports fail closed',()=>{
  for(const field of ['production_release_enabled','remote_dispatch_performed',
                      'social_publishing_performed']){
    const copy=evidence();
    copy[field]=true;
    assert.throws(()=>safeWorkflowHealth(copy));
  }
  const bad=evidence();
  bad.authenticated_provider_acceptance='yes';
  assert.throws(()=>safeWorkflowHealth(bad));
});
test('inconsistent evidence counts or sampling are rejected',()=>{
  const variants=[
    x=>x.total_workflow_plans=1,
    x=>x.sample_limit=1000,
    x=>x.sample_may_be_incomplete=true,
    x=>x.sampled_step_counts.unverified=-1,
    x=>x.sampled_step_counts.private_prompt='SECRET',
    x=>x.invalid_workflow_documents=-1,
    x=>x.sampled_reviewed_plans=5,
    x=>x.status='unknown'
  ];
  for(const change of variants){
    const copy=evidence();change(copy);
    assert.throws(()=>safeWorkflowHealth(copy));
  }
});
test('corruption and missing plans are honestly distinguished',()=>{
  const none=evidence();
  none.status='no_plans';none.total_workflow_plans=0;
  none.total_persisted_task_links=0;none.sampled_workflow_plans=0;
  none.sampled_reviewed_plans=0;
  none.sampled_step_counts={unlinked:0,answered:0,failed:0,active:0,unverified:0};
  assert.equal(safeWorkflowHealth(none).status,'no_plans');
  const report=evidence();
  report.status='review_required';
  report.invalid_workflow_documents=1;
  assert.equal(safeWorkflowHealth(report).invalid,1);
});
