/* Read-only projection boundary for the operator workflow console. */
export const AGENTS = Object.freeze([
  ['kiko','Albedo'], ['liu_bei','Liu Bei'], ['memory','Mira'],
  ['archives','Lyra'], ['inventory','Pip'], ['vault','Aurelia'],
  ['ninja','Nyx'], ['cache','Mochi'], ['strategy','Orion'], ['nova','Nova']
]);
const IDS = new Set(AGENTS.map(([id])=>id));
const STATUSES = new Set([
  'ready_for_operator_link', 'blocked_on_dependencies',
  'linked_task_in_progress', 'answered_pending_review', 'linked_task_failed'
]);
export function safeWorkflow(record) {
  if (!record || record.schema !== 'exodia.phase13.operator-workflow/v1' ||
      typeof record.id !== 'string' || !/^[a-zA-Z0-9-]{1,128}$/.test(record.id) ||
      typeof record.title !== 'string' || !record.title.trim() ||
      record.title.length > 120 ||
      !Number.isInteger(record.revision) || record.revision < 1 ||
      !['operator_planning','reviewed_local_only'].includes(record.status) ||
      !Array.isArray(record.steps) || record.steps.length < 1 || record.steps.length > 12 ||
      record.step_count !== record.steps.length ||
      !Number.isInteger(record.completed_task_count) ||
      record.completed_task_count < 0 ||
      record.completed_task_count > record.step_count ||
      record.operator_review_confirmed !== (record.status === 'reviewed_local_only') ||
      record.external_dispatch_performed !== false ||
      record.social_publishing_performed !== false ||
      record.production_release_enabled !== false)
    throw new Error('Unverified EXODIA operator plan contract');
  const seen = new Set();
  let completed = 0;
  const steps = record.steps.map(item=>{
    if (!item || typeof item.key !== 'string' ||
        !/^[a-z][a-z0-9_]{0,31}$/.test(item.key) ||
        seen.has(item.key) ||
        typeof item.label !== 'string' || item.label.length < 1 || item.label.length > 80 ||
        !IDS.has(item.agent_id) || !STATUSES.has(item.status) ||
        !Array.isArray(item.depends_on) || item.depends_on.length > 11 ||
        new Set(item.depends_on).size !== item.depends_on.length ||
        item.depends_on.some(d=>typeof d!=='string' || !seen.has(d)) ||
        (item.linked_task_id !== null &&
         (typeof item.linked_task_id !== 'string' ||
          !/^[a-zA-Z0-9-]{1,128}$/.test(item.linked_task_id))) ||
        ((item.status==='ready_for_operator_link' ||
          item.status==='blocked_on_dependencies') && item.linked_task_id!==null) ||
        ((item.status==='answered_pending_review' ||
          item.status==='linked_task_in_progress' ||
          item.status==='linked_task_failed') && item.linked_task_id===null))
      throw new Error('Unverified workflow stage or ownership');
    seen.add(item.key);
    if (item.status === 'answered_pending_review') completed++;
    return Object.freeze({
      key:item.key,label:item.label,agentId:item.agent_id,
      dependencies:Object.freeze([...item.depends_on]),
      linkedTaskId:item.linked_task_id,status:item.status
    });
  });
  if (completed !== record.completed_task_count ||
      (record.status==='reviewed_local_only' && completed!==record.step_count))
    throw new Error('Workflow completion evidence mismatch');
  return Object.freeze({
    id:record.id,title:record.title,revision:record.revision,
    status:record.status,completed,stepCount:steps.length,
    steps:Object.freeze(steps)
  });
}
