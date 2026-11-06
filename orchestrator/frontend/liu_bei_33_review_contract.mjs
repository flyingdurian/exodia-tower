/* Phase 10 locked 33-state review schema: text only, no unreviewed images. */
export function safeThirtyThreeReview(record) {
  if (!record || record.schema !== 'exodia.phase10.liu-bei-33-review/v1' ||
      record.character_id !== 'liu_bei' ||
      record.canonical_source !== 'existing_albedo_state_keys_not_albedo_artwork' ||
      record.planned_states !== 33 || record.planned_expressions !== 20 ||
      record.planned_actions !== 13 ||
      record.source_count !== 0 || record.approved_native_state_count !== 0 ||
      record.artwork_status !== 'pending_distinct_standalone_sources' ||
      record.automatic_native_registration !== false ||
      record.production_release_enabled !== false ||
      record.independent_original_authorship_verified !== false ||
      record.owner_identity_approval !== 'pending' ||
      !record.display || record.display.mode !== 'review_only_typographic_33_state' ||
      record.display.asset_url !== null ||
      !Array.isArray(record.states) || record.states.length !== 33 ||
      typeof record.selected_state !== 'string') {
    throw new Error('Unverified Liu Bei 33-state review response');
  }
  const keys = new Set();
  let expressionCount = 0;
  let actionCount = 0;
  const list = [];
  for (const item of record.states) {
    if (!item || typeof item.key !== 'string' ||
        !/^[a-z][a-z0-9_]*$/.test(item.key) ||
        typeof item.label !== 'string' || item.label.length > 48 ||
        item.label.length === 0 || keys.has(item.key) ||
        item.asset_url !== null || item.source_verified !== false ||
        item.owner_approved !== false ||
        item.art_status !== 'awaiting_independent_native_art') {
      throw new Error('Unverified Liu Bei review state');
    }
    if (item.category === 'expression') expressionCount += 1;
    else if (item.category === 'action') actionCount += 1;
    else throw new Error('Unrecognized state category');
    keys.add(item.key);
    list.push(Object.freeze({
      key: item.key, label: item.label, category: item.category
    }));
  }
  if (expressionCount !== 20 || actionCount !== 13 ||
      !keys.has(record.selected_state))
    throw new Error('Canonical state counts or selection drift');
  return Object.freeze({
    selectedState: record.selected_state,
    reviewPreview: record.review_preview === true,
    states: Object.freeze(list),
    status: '33 planned · no approved native source states'
  });
}
