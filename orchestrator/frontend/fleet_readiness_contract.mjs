/* Phase 11: client boundary for all ten companions' art-free review metrics. */
export const AGENT_IDS = Object.freeze([
  'kiko','liu_bei','memory','archives','inventory',
  'vault','ninja','cache','strategy','nova'
]);
const LIFECYCLE = Object.freeze({
  idle:'neutral', active:'working', waiting:'awaiting_command',
  completed:'confident', interrupted:'concerned', cancelled:'neutral'
});
const STATE = Object.freeze({
  kiko:'existing_albedo_pipeline_preserved_native_33_release_locked',
  liu_bei:'a0_intake_unverified_native_33_art_pending'
});
const allowedStatus = id => STATE[id] || 'frozen_existing_companion_art_untouched';

export function safeFleetReview(payload) {
  if (!payload || payload.schema !== 'exodia.phase11.fleet-state-readiness/v1' ||
      payload.read_only !== true ||
      payload.scope !== 'ten_companions_review_contract_not_art_release' ||
      !AGENT_IDS.includes(payload.selected_agent) ||
      !(payload.task_lifecycle in LIFECYCLE) ||
      payload.canonical_review_state !== LIFECYCLE[payload.task_lifecycle] ||
      payload.fleet_count !== 10 ||
      payload.states_per_companion !== 33 ||
      payload.planned_contract_slots !== 330 ||
      payload.native_33_production_released_count !== 0 ||
      payload.automatic_art_registration !== false ||
      payload.remote_task_dispatch_performed !== false ||
      payload.automatic_social_publishing !== false ||
      payload.production_release_enabled !== false ||
      !Array.isArray(payload.companions) ||
      payload.companions.length !== 10) {
    throw new Error('EXODIA fleet review contract unavailable');
  }
  const companions = payload.companions.map((entry,index)=>{
    const id = AGENT_IDS[index];
    if (!entry || entry.agent_id !== id ||
        typeof entry.name !== 'string' || entry.name.length < 1 ||
        entry.name.length > 64 ||
        entry.planned_states !== 33 ||
        entry.planned_expressions !== 20 ||
        entry.planned_actions !== 13 ||
        entry.native_33_production_released !== false ||
        entry.review_asset_url !== null ||
        entry.existing_portrait_workflow_unchanged !== true ||
        entry.art_rollout_status !== allowedStatus(id))
      throw new Error('EXODIA companion review lock changed');
    return Object.freeze({id, name:entry.name, state:'33 planned · native release locked'});
  });
  return Object.freeze({
    selectedAgent:payload.selected_agent,
    lifecycle:payload.task_lifecycle,
    stage:LIFECYCLE[payload.task_lifecycle],
    fleetCount:10,
    plannedSlots:330,
    companions:Object.freeze(companions),
  });
}
