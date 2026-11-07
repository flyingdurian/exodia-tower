/* Phase 9: review-only Liu Bei native-source readiness.

 * Strictly data about candidate inspection, not image acquisition, approval,
 * authoring, animation or release. No path, hash or private task text is
 * rendered to the companion stage. */
import {STATE_KEYS} from './liu_bei_review_contract.mjs';

const ORIGINAL_SHA = '46e0a125a31586994f11e6660a55617ba50c5f073f6d882c671177ca8042a352';
const VARIANTS = STATE_KEYS.slice(1);
const STATUSES = new Set([
  'awaiting_independent_state_source', 'awaiting_image_bound_annotations',
  'technical_geometry_ready_for_human_review', 'rejected_native_dimensions',
  'rejected_source_file', 'rejected_annotations', 'source_or_annotations_unavailable',
  'orphaned_annotations', 'candidate_copy_unstable', 'unsafe_candidate_or_sidecar'
]);

function validSha(value) {
  return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
}

export function safeVariantReadiness(record) {
  if (!record || record.schema !== 'exodia.phase7.liu-bei-variant-preflight/v1' ||
      record.character_id !== 'liu_bei' ||
      record.parent_identity_state !== 'neutral' ||
      record.approved_a0_original_visual_sha256 !== ORIGINAL_SHA ||
      record.production_release_enabled !== false ||
      record.five_state_staging_authorized !== false ||
      record.automatic_registration_enabled !== false ||
      typeof record.a0_native_technical_pass !== 'boolean' ||
      typeof record.a0_image_bound_geometry_pass !== 'boolean' ||
      (record.a0_image_bound_geometry_pass && !record.a0_native_technical_pass) ||
      (record.a0_native_technical_pass &&
       !validSha(record.formatted_a0_native_sha256)) ||
      (!record.a0_native_technical_pass &&
       record.formatted_a0_native_sha256 !== null) ||
      !Array.isArray(record.states) || record.states.length !== VARIANTS.length)
    throw new Error('Liu Bei variant review schema or release lock drift');

  const states = Object.create(null);
  states.neutral = Object.freeze({
    ready: record.a0_image_bound_geometry_pass,
    label: record.a0_image_bound_geometry_pass
      ? 'A0 technical geometry verified · human identity review pending'
      : record.a0_native_technical_pass
        ? 'A0 PNG accepted · actual landmark review pending'
        : 'A0 native PNG technical validation pending'
  });

  for (const [index, name] of VARIANTS.entries()) {
    const state = record.states[index];
    if (!state || state.key !== name ||
        state.category !== (name === 'working' || name === 'pointing'
          ? 'action' : 'expression') ||
        !STATUSES.has(state.status) ||
        state.production_release_enabled !== false ||
        state.owner_state_approval !== 'pending' ||
        state.source_authenticity_verified !== false ||
        state.asset_url !== null ||
        typeof state.technical_source_pass !== 'boolean' ||
        typeof state.image_bound_annotation_consistency !== 'boolean' ||
        typeof state.geometry_ready_for_owner_review !== 'boolean' ||
        (state.technical_source_pass && !validSha(state.candidate_sha256)) ||
        (!state.technical_source_pass && state.candidate_sha256 !== null) ||
        (state.geometry_ready_for_owner_review &&
          (!state.technical_source_pass ||
           !state.image_bound_annotation_consistency ||
           state.status !== 'technical_geometry_ready_for_human_review')) ||
        (state.image_bound_annotation_consistency &&
         !state.geometry_ready_for_owner_review))
      throw new Error('Liu Bei variant evidence or art approval lock drift');
    const label = state.geometry_ready_for_owner_review
      ? 'Source geometry checked · human visual approval pending'
      : state.technical_source_pass
        ? 'Native candidate installed · actual landmark evidence pending'
        : state.status === 'awaiting_independent_state_source'
          ? 'Independent state PNG not installed'
          : 'Source or annotations failed preflight';
    states[name] = Object.freeze({
      ready: state.geometry_ready_for_owner_review,
      label
    });
  }
  return Object.freeze(states);
}

export function reviewReadinessLabel(safeStates, selectedState) {
  if (!STATE_KEYS.includes(selectedState) || !safeStates)
    return 'State source preflight unavailable · display remains locked';
  return safeStates[selectedState]?.label ||
    'State source preflight unavailable · display remains locked';
}
