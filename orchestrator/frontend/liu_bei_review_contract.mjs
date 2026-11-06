/* Read-only Liu Bei five-state contract. No art URL, credentials, task text or
 * provider instructions may enter the review UI. */
export const STATE_KEYS = Object.freeze(['neutral', 'confident', 'angered', 'working', 'pointing']);

const BEHAVIORS = Object.freeze({
  neutral: 'Idle readiness',
  confident: 'Decisive gaze',
  angered: 'Blocked-route frustration',
  working: 'Active route planning',
  pointing: 'Connected directional gesture'
});

export function publicTaskSignal(input) {
  const source = input && typeof input === 'object' ? input : {};
  const value = (key, fallback = '') =>
    typeof source[key] === 'string' ? source[key] : fallback;
  return Object.freeze({
    agentId: value('agentId', 'kiko'),
    taskId: value('taskId'),
    state: value('state', 'idle'),
    updatedAt: value('updatedAt')
  });
}

export function reviewRequestKey(task, manual = null) {
  if (manual !== null && !STATE_KEYS.includes(manual))
    throw new Error('Invalid Liu Bei preview state');
  const signal = publicTaskSignal(task);
  const taskId = signal.agentId === 'liu_bei' ? signal.taskId : '';
  // The HTTP query is task_id / preview_state only. State and updatedAt
  // invalidate local response de-duplication when a live task advances.
  return JSON.stringify([taskId, signal.state, signal.updatedAt, manual]);
}

export function safeReviewProjection(record) {
  if (!record || record.schema !== 'exodia.phase7.liu_bei-five-state-review/v1' ||
      record.character_id !== 'liu_bei' ||
      record.production_release_enabled !== false ||
      record.owner_identity_approval !== 'pending' ||
      record.independent_original_authorship_verified !== false ||
      !STATE_KEYS.includes(record.selected_state) ||
      !Array.isArray(record.states) || record.states.length !== STATE_KEYS.length ||
      record.states.some((item, index) =>
        !item || item.key !== STATE_KEYS[index] ||
        item.asset_url !== null ||
        item.art_status !== 'awaiting_exact_sha_owner_approval') ||
      !record.display || record.display.mode !== 'review_only_fallback' ||
      record.display.asset_url !== null)
    throw new Error('Liu Bei review lock or schema changed');

  return Object.freeze({
    state: record.selected_state,
    behavior: BEHAVIORS[record.selected_state],
    preview: record.review_preview === true,
    technicalSourcePass: record.native_a0_intake?.technical_source_pass === true,
    geometryConsistent: record.native_a0_intake?.image_bound_annotation_consistency === true
  });
}
