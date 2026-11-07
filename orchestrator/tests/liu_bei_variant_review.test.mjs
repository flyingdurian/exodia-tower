import test from 'node:test';
import assert from 'node:assert/strict';
import {safeVariantReadiness, reviewReadinessLabel}
  from '../frontend/liu_bei_variant_review.mjs';

const names = ['confident','angered','working','pointing'];
function evidence() {
  return {
    schema:'exodia.phase7.liu-bei-variant-preflight/v1',
    character_id:'liu_bei', parent_identity_state:'neutral',
    approved_a0_original_visual_sha256:
      '46e0a125a31586994f11e6660a55617ba50c5f073f6d882c671177ca8042a352',
    formatted_a0_native_sha256:'b'.repeat(64),
    a0_native_technical_pass:true,
    a0_image_bound_geometry_pass:false,
    production_release_enabled:false,
    five_state_staging_authorized:false,
    automatic_registration_enabled:false,
    states:names.map(key=>({
      key, category:['working','pointing'].includes(key)?'action':'expression',
      status:'awaiting_independent_state_source',
      candidate_sha256:null, technical_source_pass:false,
      image_bound_annotation_consistency:false,
      geometry_ready_for_owner_review:false,
      owner_state_approval:'pending', source_authenticity_verified:false,
      production_release_enabled:false, asset_url:null
    }))
  };
}

test('native A0 technical installation is visible as pending landmarks, not released art',()=>{
  const safe=safeVariantReadiness(evidence());
  assert.match(reviewReadinessLabel(safe,'neutral'), /landmark review pending/);
  assert.equal(safe.neutral.ready,false);
  assert.match(reviewReadinessLabel(safe,'confident'), /not installed/);
  assert.equal('asset_url' in safe.confident,false);
  assert.equal(JSON.stringify(safe).includes('b'.repeat(64)),false);
});

test('individual variant source geometry is review ready but requires visual approval',()=>{
  const r=evidence();const item=r.states[2];
  item.status='technical_geometry_ready_for_human_review';
  item.technical_source_pass=true;
  item.image_bound_annotation_consistency=true;
  item.geometry_ready_for_owner_review=true;
  item.candidate_sha256='a'.repeat(64);
  const safe=safeVariantReadiness(r);
  assert.equal(safe.working.ready,true);
  assert.match(reviewReadinessLabel(safe,'working'), /human visual approval pending/);
  assert.equal(safe.confident.ready,false);
});

test('release and owner approval bypasses fail closed',()=>{
  for(const key of ['production_release_enabled','automatic_registration_enabled','five_state_staging_authorized']){
    const r=evidence();r[key]=true;assert.throws(()=>safeVariantReadiness(r), /review schema/);
  }
  const r=evidence();r.states[0].owner_state_approval='approved';
  assert.throws(()=>safeVariantReadiness(r), /variant evidence/);
});

test('art URLs and unexplained approval states fail closed',()=>{
  const r=evidence();r.states[3].asset_url='/private/fake.png';
  assert.throws(()=>safeVariantReadiness(r));
  const s=evidence();s.states[2].source_authenticity_verified=true;
  assert.throws(()=>safeVariantReadiness(s));
  const t=evidence();t.a0_native_technical_pass=false;
  assert.throws(()=>safeVariantReadiness(t));
});

test('malformed status, wrong order, and inconsistent landmarks fail closed',()=>{
  const r=evidence();r.states.reverse();
  assert.throws(()=>safeVariantReadiness(r));
  const s=evidence();s.states[1].status='we_are_approved';
  assert.throws(()=>safeVariantReadiness(s));
  const t=evidence();t.states[0].geometry_ready_for_owner_review=true;
  assert.throws(()=>safeVariantReadiness(t));
  const u=evidence();u.states[0].technical_source_pass=true;
  assert.throws(()=>safeVariantReadiness(u));
});

test('unavailable or cross-companion state returns a locked neutral message',()=>{
  assert.match(reviewReadinessLabel(null,'neutral'), /unavailable/);
  assert.match(reviewReadinessLabel(Object.freeze({}),'kiko'), /unavailable/);
  const r=evidence();
  r.a0_image_bound_geometry_pass=true;
  const safe=safeVariantReadiness(r);
  assert.equal(safe.neutral.ready,true);
  assert.match(reviewReadinessLabel(safe,'neutral'), /human identity review pending/);
});
