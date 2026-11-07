import test from 'node:test';
import assert from 'node:assert/strict';
import {PUBLIC_TASK_PHASES,presentPublicTask} from '../frontend/frontshell_signal.mjs';

test('all supported public phases have bounded, visible operator signals',()=>{
  assert.equal(PUBLIC_TASK_PHASES.length,15);
  for(const state of PUBLIC_TASK_PHASES){
    const display=presentPublicTask({state,agentId:'kiko'});
    assert.equal(display.state,state);
    assert.ok(display.title.length>3);
    assert.ok(['idle','working','waiting','success','error'].includes(display.phase));
    assert.equal(display.providerAuthenticated,false);
    assert.equal(display.artReleased,false);
  }
});
test('task signal never leaks private prompt, answer or credentials',()=>{
  const sample=presentPublicTask({
    state:'running',agentId:'kiko',taskId:'t-1',
    prompt:'SECRET_PROMPT',answer:'SECRET_ANSWER',
    private_instructions:'SECRET_INSTRUCTIONS',
    session_cookie:'SECRET_COOKIE'
  });
  assert.equal(sample.title,'TASK RUNNING');
  assert.equal(sample.phase,'working');
  for(const key of ['SECRET_PROMPT','SECRET_ANSWER','SECRET_INSTRUCTIONS','SECRET_COOKIE'])
    assert.equal(JSON.stringify(sample).includes(key),false);
  assert.equal(presentPublicTask({state:'failed',agentId:'kiko'}).phase,'error');
  assert.equal(presentPublicTask({state:'waiting_for_reply',agentId:'kiko'}).phase,'waiting');
  assert.equal(presentPublicTask({state:'answered',agentId:'kiko'}).phase,'success');
});
test('unknown state cannot forge provider authentication or owner art readiness',()=>{
  const arbitrary=presentPublicTask({
    state:'owner_approved_and_authenticated',agentId:'kiko',
    provider:'authenticated',production_release_enabled:true
  });
  assert.equal(arbitrary.state,'idle');
  assert.equal(arbitrary.providerAuthenticated,false);
  assert.equal(arbitrary.artReleased,false);
  assert.equal(arbitrary.title,'STANDBY · LOCAL');
  assert.match(presentPublicTask({state:'running',agentId:'vault'}).title,/OTHER AGENT/);
});
