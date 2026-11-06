import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {safeThirtyThreeReview} from '../frontend/liu_bei_33_review_contract.mjs';

const manifest = JSON.parse(readFileSync(new URL(
  '../../assets/review/liu_bei_pilot/phase10_33_state_registry.json',
  import.meta.url), 'utf8'));
function result() {
  return {
    schema: 'exodia.phase10.liu-bei-33-review/v1',
    character_id: 'liu_bei',
    canonical_source: 'existing_albedo_state_keys_not_albedo_artwork',
    planned_states: 33, planned_expressions: 20, planned_actions: 13,
    source_count: 0, approved_native_state_count: 0,
    artwork_status: 'pending_distinct_standalone_sources',
    automatic_native_registration: false,
    production_release_enabled: false,
    independent_original_authorship_verified: false,
    owner_identity_approval: 'pending',
    selected_state: 'working', review_preview: false,
    display: {mode:'review_only_typographic_33_state', asset_url:null},
    states:manifest.states.map(s=>({
      key:s.key, label:s.label, category:s.category,
      asset_url:null, source_verified:false, owner_approved:false,
      art_status:'awaiting_independent_native_art'
    }))
  };
}
test('33 canonical state labels remain text-only, ordered and immutable',()=>{
  const safe=safeThirtyThreeReview(result());
  assert.equal(safe.states.length,33);
  assert.equal(safe.states.filter(x=>x.category==='expression').length,20);
  assert.equal(safe.states.filter(x=>x.category==='action').length,13);
  assert.equal(safe.selectedState,'working');
  assert.equal(JSON.stringify(safe).includes('asset_url'),false);
  assert.ok(Object.isFrozen(safe.states));
});
test('real state previews are labels, never source images',()=>{
  const r=result();
  for(const state of r.states){
    r.selected_state=state.key;
    assert.equal(safeThirtyThreeReview(r).selectedState,state.key);
  }
});
test('rejected release, art URLs and forged owner approvals fail closed',()=>{
  const fields = [
    ['production_release_enabled',true],
    ['automatic_native_registration',true],
    ['approved_native_state_count',1],
  ];
  for(const [key,val] of fields){
    const r=result();r[key]=val;
    assert.throws(()=>safeThirtyThreeReview(r));
  }
  const s=result();s.states[0].asset_url='/fake.png';
  assert.throws(()=>safeThirtyThreeReview(s));
  const t=result();t.states[0].owner_approved=true;
  assert.throws(()=>safeThirtyThreeReview(t));
});
test('duplicates, ordering loss and category drift fail closed',()=>{
  const r=result();r.states[1].key=r.states[0].key;
  assert.throws(()=>safeThirtyThreeReview(r));
  const s=result();s.states[0].category='action';
  assert.throws(()=>safeThirtyThreeReview(s));
  const t=result();t.states[0].label='';
  assert.throws(()=>safeThirtyThreeReview(t));
  const u=result();u.selected_state='unknown';
  assert.throws(()=>safeThirtyThreeReview(u));
});
