/* Phase 16: approve only local, unlinked recovery-plan projections. */
import {safeWorkflow} from './operator_workflow_contract.mjs';

export function safeRecoveryFork(data, expectedId, expectedRevision) {
  if (!data || data.schema !== 'exodia.phase16.local-workflow-recovery/v1'
      || !data.lineage || !data.workflow
      || typeof expectedId !== 'string'
      || !Number.isInteger(expectedRevision) || expectedRevision < 1)
    throw Error('Unverified EXODIA recovery response');
  const proof=data.lineage;
  if (proof.schema !== 'exodia.phase16.local-workflow-recovery/v1'
      || proof.source_workflow_id !== expectedId
      || proof.source_revision !== expectedRevision
      || !['linked_task_failed','reviewed_plan_revision'].includes(proof.reason_code)
      || proof.source_unmodified !== true
      || proof.copied_task_id_count !== 0
      || proof.remote_dispatch_performed !== false
      || proof.production_release_enabled !== false
      || proof.social_publishing_performed !== false
      || proof.artwork_registration_performed !== false) {
    throw Error('Recovery source and permission drift');
  }
  const fresh=safeWorkflow(data.workflow);
  if (fresh.id!==proof.recovery_workflow_id
      || fresh.status!=='operator_planning'
      || fresh.revision !== 1
      || fresh.completed !== 0
      || fresh.steps.some(step=>step.linkedTaskId!==null)) {
    throw Error('Recovery fork inherited unsafe task state');
  }
  return Object.freeze({fresh,reason:proof.reason_code});
}
