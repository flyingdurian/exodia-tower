import test from 'node:test';
import assert from 'node:assert/strict';
import {STATE_KEYS, publicTaskSignal, reviewRequestKey, safeReviewProjection}
  from '../frontend/liu_bei_review_contract.mjs';

function record() {
  return {
    schema: 'exodia.phase7.liu_bei-five-state-review/v1',
    character_id: 'liu_bei',
    selected_state: 'working',
    production_release_enabled: false,
    owner_identity_approval: 'pending',
    independent_original_authorship_verified: false,
    review_preview: false,
    native_a0_intake: {technical_source_pass: true, image_bound_annotation_consistency: false},
    display: {mode: 'review_only_fallback', asset_url: null},
    states: STATE_KEYS.map(key => ({
      key, asset_url: null, art_status: 'awaiting_exact_sha_owner_approval'
    }))
  };
}

test('live transitions invalidate identical task IDs while stable events are deduplicated', () => {
  const opening = publicTaskSignal({agentId: 'liu_bei', taskId: 'task-42', state: 'opening'});
  const finished = publicTaskSignal({agentId: 'liu_bei', taskId: 'task-42', state: 'answered'});
  assert.notEqual(reviewRequestKey(opening), reviewRequestKey(finished));
  assert.equal(reviewRequestKey(opening), reviewRequestKey({...opening}));
  assert.notEqual(
    reviewRequestKey({...finished, updatedAt: '2026-11-06T01:00:00Z'}),
    reviewRequestKey({...finished, updatedAt: '2026-11-06T01:01:00Z'})
  );
});

test('cross-agent selection never binds someone else task ID and previews remain explicit', () => {
  const kiko = {agentId: 'kiko', taskId: 'private-id', state: 'answered'};
  const none = {agentId: 'kiko', taskId: '', state: 'answered'};
  assert.equal(reviewRequestKey(kiko), reviewRequestKey(none));
  assert.notEqual(reviewRequestKey(kiko), reviewRequestKey(kiko, 'pointing'));
  assert.throws(() => reviewRequestKey(kiko, 'unlisted'), /Invalid Liu Bei/);
});

test('publicTaskSignal drops task contents and refuses non-string metadata', () => {
  const task = publicTaskSignal({agentId: 'liu_bei', taskId: 12,
    private_instructions: 'secret', answer: 'secret', state: 'working'});
  assert.deepEqual(Object.keys(task), ['agentId','taskId','state','updatedAt']);
  assert.equal(task.taskId, '');
  assert.equal(task.state, 'working');
  assert.equal(JSON.stringify(task).includes('secret'), false);
});

test('review projection is image-free and independent of original A0 technical success', () => {
  const value = safeReviewProjection(record());
  assert.equal(value.state, 'working');
  assert.equal(value.technicalSourcePass, true);
  assert.equal(value.geometryConsistent, false);
  assert.equal('asset_url' in value, false);
  assert.equal(value.behavior, 'Active route planning');
});

test('display artwork, state artwork or changed review approval fail closed', () => {
  const display = record();
  display.display.asset_url = '/artifacts/forbidden.png';
  assert.throws(() => safeReviewProjection(display));
  const state = record();
  state.states[1].asset_url = '/assets/unreviewed.png';
  assert.throws(() => safeReviewProjection(state));
  const approval = record();
  approval.owner_identity_approval = 'approved';
  assert.throws(() => safeReviewProjection(approval));
  const release = record();
  release.production_release_enabled = true;
  assert.throws(() => safeReviewProjection(release));
});

test('schema/order drifts or missing original authorship lock fail closed', () => {
  const wrong = record();
  wrong.states.reverse();
  assert.throws(() => safeReviewProjection(wrong));
  const malformed = record();
  malformed.states[0] = null;
  assert.throws(() => safeReviewProjection(malformed));
  const auth = record();
  auth.independent_original_authorship_verified = true;
  assert.throws(() => safeReviewProjection(auth));
});
