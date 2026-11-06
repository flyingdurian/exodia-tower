/* Phase 15: strict, bounded, text-only workflow health projection. */
const CODES = Object.freeze(['unlinked','answered','failed','active','unverified']);
export function safeWorkflowHealth(record) {
  if (!record ||
      record.schema !== 'exodia.phase15.operator-workflow-health/v1' ||
      record.read_only !== true ||
      !['operational','no_plans','review_required'].includes(record.status) ||
      !Number.isInteger(record.total_workflow_plans) ||
      record.total_workflow_plans < 0 ||
      !Number.isInteger(record.total_persisted_task_links) ||
      record.total_persisted_task_links < 0 ||
      !Number.isInteger(record.sampled_workflow_plans) ||
      record.sampled_workflow_plans < 0 ||
      record.sample_limit !== 100 ||
      record.sampled_workflow_plans > record.sample_limit ||
      record.sampled_workflow_plans > record.total_workflow_plans ||
      record.sample_may_be_incomplete !==
        (record.total_workflow_plans > record.sampled_workflow_plans) ||
      !Number.isInteger(record.invalid_workflow_documents) ||
      record.invalid_workflow_documents < 0 ||
      !Number.isInteger(record.sampled_reviewed_plans) ||
      record.sampled_reviewed_plans < 0 ||
      record.sampled_reviewed_plans > record.sampled_workflow_plans ||
      !record.sampled_step_counts ||
      Object.keys(record.sampled_step_counts).length !== CODES.length ||
      CODES.some(key=>
        !Number.isInteger(record.sampled_step_counts[key]) ||
        record.sampled_step_counts[key] < 0) ||
      record.production_release_enabled !== false ||
      record.remote_dispatch_performed !== false ||
      record.social_publishing_performed !== false ||
      record.authenticated_provider_acceptance !== 'not_established') {
    throw new Error('Unsafe EXODIA workflow operations report');
  }
  const counts={};
  for (const key of CODES) counts[key]=record.sampled_step_counts[key];
  if ((record.status==='no_plans' && record.total_workflow_plans!==0) ||
      (record.status==='operational' &&
       (record.total_workflow_plans===0 ||
        record.invalid_workflow_documents > 0 ||
        counts.unverified > 0)) ||
      (record.status==='review_required' &&
       !(record.invalid_workflow_documents > 0 || counts.unverified > 0))) {
    throw new Error('Workflow health report contradicts local evidence');
  }
  return Object.freeze({
    status:record.status,
    total:record.total_workflow_plans,
    linked:record.total_persisted_task_links,
    sampled:record.sampled_workflow_plans,
    partial:record.sample_may_be_incomplete,
    invalid:record.invalid_workflow_documents,
    reviewed:record.sampled_reviewed_plans,
    counts:Object.freeze(counts)
  });
}
