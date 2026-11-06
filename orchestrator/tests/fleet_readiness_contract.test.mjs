import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {AGENT_IDS, safeFleetReview} from '../frontend/fleet_readiness_contract.mjs';

const policy=JSON.parse(readFileSync(
  new URL('../../assets/review/fleet/phase11_rollout_policy.json',import.meta.url),
  'utf8'));
function payload() {
  return {
    schema:'exodia.phase11.fleet-state-readiness/v1',
    read_only:true,
    scope:'ten_companions_review_contract_not_art_release',
    selected_agent:'liu_bei',
    task_lifecycle:'active',
    canonical_review_state:'working',
    fleet_count:10,states_per_companion:33,planned_contract_slots:330,
    native_33_production_released_count:0,
    automatic_art_registration:false,
    remote_task_dispatch_performed:false,
    automatic_social_publishing:false,
    production_release_enabled:false,
    task_id:'safe-id',
    companions:policy.companions.map(x=>({
      agent_id:x.agent_id,name:x.name,
      planned_states:33,planned_expressions:20,planned_actions:13,
      native_33_production_released:false,
      existing_portrait_workflow_unchanged:true,
      art_rollout_status:x.art_rollout_status,review_asset_url:null,
    })),
  };
}
test('exactly ten stable companions, 330 states and no art URLs in review response',()=>{
  const r=safeFleetReview(payload());
  assert.deepEqual(r.companions.map(x=>x.id),AGENT_IDS);
  assert.equal(r.plannedSlots,330);
  assert.equal(r.stage,'working');
  assert.equal(JSON.stringify(r).includes('review_asset_url'),false);
  assert.ok(Object.isFrozen(r.companions));
});
test('lifecycle always maps without parsing provider task contents',()=>{
  for(const [lifecycle,state] of [
    ['idle','neutral'],['active','working'],
    ['waiting','awaiting_command'],['completed','confident'],
    ['interrupted','concerned'],['cancelled','neutral']
  ]){
    const sample=payload();
    sample.task_lifecycle=lifecycle;
    sample.canonical_review_state=state;
    assert.equal(safeFleetReview(sample).stage,state);
  }
});
test('art approvals, remote dispatch and publication locks reject changes',()=>{
  for(const [field,value] of [
    ['automatic_art_registration',true],
    ['remote_task_dispatch_performed',true],
    ['automatic_social_publishing',true],
    ['production_release_enabled',true],
    ['native_33_production_released_count',1],
  ]){
    const x=payload();x[field]=value;
    assert.throws(()=>safeFleetReview(x));
  }
  const image=payload();
  image.companions[0].review_asset_url='/fake/portrait.png';
  assert.throws(()=>safeFleetReview(image));
});
test('roster drift, forged native release and malformed 33 counts fail closed',()=>{
  const x=payload();x.companions[1].agent_id='some-other-agent';
  assert.throws(()=>safeFleetReview(x));
  const a=payload();a.companions[2].native_33_production_released=true;
  assert.throws(()=>safeFleetReview(a));
  const b=payload();b.companions[5].planned_expressions=19;
  assert.throws(()=>safeFleetReview(b));
  const c=payload();c.companions[1].art_rollout_status='owner_approved';
  assert.throws(()=>safeFleetReview(c));
  const d=payload();d.selected_agent='unknown';
  assert.throws(()=>safeFleetReview(d));
});
