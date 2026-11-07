import test from 'node:test';
import assert from 'node:assert/strict';
import {sanitizeTasks,classifyHealth,OperationalTimeline}
  from '../frontend/frontshell_diagnostics_contract.mjs';

const tasks=()=>({tasks:[
  {id:'task-1',provider:'chatgpt',state:'running',agent_id:'kiko',
   prompt:'PRIVATE_OPS_PROMPT',answer:'PRIVATE_ANSWER',error:'SECRET_ERROR'},
  {id:'task-2',provider:'gemini',state:'waiting_for_reply',agent_id:'liu_bei'},
  {id:'task-3',provider:'ollama',state:'answered',agent_id:'vault'},
  {id:'unsafe<script>',provider:'deepseek',state:'running',
   private_instructions:'SECRET'}
]});
test('all visible task records are privacy-projected and bounded',()=>{
  const result=sanitizeTasks(tasks());
  assert.equal(result.length,3);
  assert.deepEqual(result[0],{
    key:'task-1',provider:'chatgpt',state:'running',agent:'kiko',label:'Task 01'
  });
  for(const secret of ['PRIVATE_OPS_PROMPT','PRIVATE_ANSWER','SECRET_ERROR','SECRET'])
    assert.ok(!JSON.stringify(result).includes(secret));
  assert.throws(()=>sanitizeTasks({tasks:null}));
  assert.equal(sanitizeTasks({tasks:[...tasks().tasks,...tasks().tasks]}).length,3);
  assert.ok(Object.isFrozen(result));
});
test('timeline records state transitions only, never repeated polling traffic',()=>{
  const t=new OperationalTimeline(5);
  const initial=sanitizeTasks(tasks());
  assert.equal(t.accept(initial,1000).length,3);
  assert.equal(t.accept(initial,2000).length,0);
  assert.equal(t.events.length,3);
  const updated=initial.map(x=>x.key==='task-1'?{...x,state:'failed'}:x);
  assert.equal(t.accept(updated,3000).length,1);
  assert.equal(t.byProvider('chatgpt').events[0].state,'failed');
  assert.equal(t.byProvider('gemini').tasks.length,1);
  assert.ok(t.events.every(x=>!('prompt' in x)&&!('answer' in x)));
  assert.throws(()=>t.byProvider('hacker'));
  t.clear();
  assert.equal(t.events.length,0);
});
test('freshness reflects last successful observation, not socket link alone',()=>{
  assert.deepEqual(classifyHealth({lastSuccessAt:0,now:31000,transport:'connected'}).freshness,'unavailable');
  assert.equal(classifyHealth({lastSuccessAt:1000,now:5000,transport:'disconnected'}).freshness,'fresh');
  assert.equal(classifyHealth({lastSuccessAt:1000,now:17000,transport:'connected'}).freshness,'aging');
  assert.equal(classifyHealth({lastSuccessAt:1000,now:39000,transport:'connected'}).freshness,'stale');
  assert.equal(classifyHealth({lastSuccessAt:1000,now:4000}).authenticatedProviderVerified,false);
  assert.throws(()=>classifyHealth({lastSuccessAt:100,now:-10}));
});
