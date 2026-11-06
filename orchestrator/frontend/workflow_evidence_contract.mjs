/* Phase 14: refuse any task evidence with released/published actions. */
const STATUSES=new Set(['ready_for_operator_link','blocked_on_dependencies',
  'linked_task_in_progress','answered_pending_review','linked_task_failed']);
const PROOFS=new Set(['no_linked_task','answered_event_recorded',
  'answered_without_event_proof','terminal_unsuccessful',
  'task_active_or_draft','unknown_task_state']);
const ACTIONS=new Set(['inspect_failed_tasks_and_create_new_plan',
  'link_existing_tasks_manually','await_existing_task_results',
  'confirm_or_inspect_local_review']);
export function safeWorkflowEvidence(report){
  if(!report||report.schema!=='exodia.phase14.workflow-task-evidence/v1'||
     report.read_only!==true || report.production_release_enabled!==false ||
     report.external_dispatch_performed!==false ||
     report.social_publishing_performed!==false ||
     report.authenticated_provider_acceptance!=='not_established' ||
     typeof report.workflow_id!=='string' ||
     !/^[A-Za-z0-9-]{1,128}$/.test(report.workflow_id) ||
     !Number.isInteger(report.revision) || report.revision<1 ||
     !['operator_planning','reviewed_local_only'].includes(report.workflow_status)||
     report.operator_review_confirmed!==(report.workflow_status==='reviewed_local_only')||
     !Array.isArray(report.steps) ||
     !Number.isInteger(report.step_count) || report.step_count!==report.steps.length||
     report.step_count<1 || report.step_count>12||
     !Number.isInteger(report.answered_task_count) ||
     !Number.isInteger(report.answered_event_recorded_count)||
     !Number.isInteger(report.operator_link_ready_count) ||
     !Number.isInteger(report.failed_linked_task_count) ||
     !ACTIONS.has(report.next_operator_action))throw Error('Unsafe workflow evidence');
  let answered=0,confirmed=0,ready=0,failures=0;
  const steps=report.steps.map(s=>{
    if(!s||typeof s.key!=='string'||!/^[a-z][a-z0-9_]{0,31}$/.test(s.key)||
       typeof s.agent_id!=='string'||s.agent_id.length>32||
       !STATUSES.has(s.step_status) || !PROOFS.has(s.audit_evidence) ||
       s.provider_authentication_verified!==false ||
       s.owner_external_action_approval!==false ||
       (s.task_id!==null && (typeof s.task_id!=='string'||
          !/^[A-Za-z0-9-]{1,128}$/.test(s.task_id))) ||
       (s.task_id===null && s.audit_evidence!=='no_linked_task')||
       (s.audit_evidence==='answered_event_recorded' &&
        !['state_change','legacy_snapshot'].includes(s.answer_event_kind))||
       (s.audit_evidence!=='answered_event_recorded'&&s.answer_event_kind!==null))
       throw Error('Unsafe workflow stage evidence');
    if(s.step_status==='answered_pending_review')answered++;
    if(s.audit_evidence==='answered_event_recorded')confirmed++;
    if(s.step_status==='ready_for_operator_link')ready++;
    if(s.step_status==='linked_task_failed')failures++;
    return Object.freeze({key:s.key,agent:s.agent_id,status:s.step_status,
      audit:s.audit_evidence});
  });
  if(answered!==report.answered_task_count||
     confirmed!==report.answered_event_recorded_count||
     ready!==report.operator_link_ready_count||
     failures!==report.failed_linked_task_count||
     report.all_tasks_answered!==(answered===steps.length)||
     report.all_answered_events_corroborated!==(confirmed===steps.length))
     throw Error('Workflow evidence count drift');
  return Object.freeze({workflowId:report.workflow_id,revision:report.revision,
    answered,confirmed,ready,failures,nextAction:report.next_operator_action,
    steps:Object.freeze(steps)});
}
