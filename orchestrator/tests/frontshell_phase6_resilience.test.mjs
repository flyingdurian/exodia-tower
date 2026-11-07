import test from 'node:test';
import assert from 'node:assert/strict';
import {observeResilience,canRefresh,boundedRetryDelay,FRESHNESS}
  from '../frontend/frontshell_resilience_contract.mjs';
test('local socket is never evidence of third-party authentication',()=>{
  const ready=observeResilience({now:10000,lastSnapshotAt:9000,link:'connected'});
  assert.equal(ready.freshness,'fresh');
  assert.equal(ready.state,'LOCAL EVENT STREAM LIVE');
  for(const flag of ['providerAuthenticationVerified','providerWebSocketsVerified',
      'productionArtworkReleased','windowsOperatorAcceptanceVerified'])
    assert.equal(ready[flag],false);
  assert.deepEqual(FRESHNESS,['fresh','aging','stale','unavailable','offline']);
});
test('freshness ages while WS stays open and marks offline as unverified',()=>{
  assert.equal(observeResilience({now:37000,lastSnapshotAt:1000,link:'connected'}).freshness,'stale');
  const offline=observeResilience({now:2000,lastSnapshotAt:1000,
    link:'connected',online:false});
  assert.equal(offline.freshness,'offline');
  assert.equal(offline.link,'disconnected');
  assert.equal(observeResilience({now:1000}).freshness,'unavailable');
  assert.equal(observeResilience({now:22000,lastSnapshotAt:1000}).freshness,'aging');
  assert.equal(canRefresh({visible:false,online:true}),false);
  assert.equal(canRefresh({visible:true,online:false}),false);
  assert.equal(canRefresh({visible:true,online:true}),true);
});
test('bounded reconnection never storms, bad telemetry fails closed',()=>{
  assert.deepEqual([0,1,2,3,4,5,90].map(boundedRetryDelay),
    [1500,3000,6000,12000,15000,15000,15000]);
  assert.throws(()=>boundedRetryDelay(-1));
  assert.throws(()=>boundedRetryDelay(NaN));
  assert.throws(()=>observeResilience({now:-1}));
  assert.throws(()=>observeResilience({now:1000,link:'vendor_authenticated'}));
  assert.throws(()=>observeResilience({now:1000,lastSnapshotAt:NaN}));
});
