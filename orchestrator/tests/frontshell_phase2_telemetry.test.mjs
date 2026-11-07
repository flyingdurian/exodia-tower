import test from 'node:test';
import assert from 'node:assert/strict';
import {PROVIDERS,ActivityHistory,projectProviders,
        sparklinePath,summariseActivity} from '../frontend/frontshell_telemetry_contract.mjs';

function sample(){
  return {
    provider:{ollama:{connected:true}},
    sessions:{models:{chatgpt:{status:'needs_operator_login_or_review'},
      gemini:{status:'ready_for_next_prompt'},deepseek:{status:'closed'}}},
    tasks:{tasks:[
      {provider:'chatgpt',state:'running',prompt:'SECRET'},
      {provider:'chatgpt',state:'answered',answer:'PRIVATE'},
      {provider:'gemini',state:'waiting_for_reply',private_instructions:'HIDDEN'},
      {provider:'ollama',state:'failed'},
      {provider:'ollama',state:'rendering_media'},
      {provider:'untrusted',state:'running'}
    ]}
  };
}
test('four provider summaries are bounded and never authenticate vendor sockets',()=>{
  const v=sample();
  const projection=projectProviders(v.provider,v.sessions,v.tasks);
  assert.deepEqual(Object.keys(projection),PROVIDERS);
  assert.equal(projection.chatgpt.active,1);
  assert.equal(projection.chatgpt.finished,1);
  assert.equal(projection.gemini.active,1);
  assert.equal(projection.ollama.active,1);
  assert.equal(projection.ollama.status,'reachable');
  assert.match(projection.chatgpt.session,/sign-in unverified/);
  assert.equal(projection.gemini.authenticatedProviderVerified,false);
  assert.equal(projection.deepseek.providerWebSocketVerified,false);
  const compact=summariseActivity(projection,'connected');
  assert.equal(compact.active,3);
  assert.equal(compact.transportLabel,'LOCAL EVENTS LINKED');
  assert.equal(compact.remoteProviderSocketsVerified,false);
  const repr=JSON.stringify({projection,compact});
  for(const value of ['SECRET','PRIVATE','HIDDEN'])
    assert.equal(repr.includes(value),false);
});
test('provider snapshots fail closed on missing data and unknown session states',()=>{
  const v=sample();
  assert.throws(()=>projectProviders(null,v.sessions,v.tasks));
  assert.throws(()=>projectProviders(v.provider,v.sessions,{tasks:null}));
  v.sessions.models.gemini.status='<script>CONNECTED</script>';
  const result=projectProviders(v.provider,v.sessions,v.tasks);
  assert.equal(result.gemini.status,'unknown');
  assert.equal(result.gemini.session,'Unknown session');
  assert.equal(summariseActivity(result,'vendor-ws-verified').link,'disconnected');
  assert.equal(projectProviders({},v.sessions,v.tasks).ollama.status,'unavailable');
});
test('sparkline displays only observed task points, caps history and has finite geometry',()=>{
  const data=new ActivityHistory(5);
  assert.equal(sparklinePath(data.all().chatgpt),'');
  for(let i=0;i<10;i++)data.append({
    chatgpt:{active:i%3},ollama:{active:2},
    gemini:{active:0},deepseek:{active:1}
  });
  assert.deepEqual(data.all().chatgpt,[2,0,1,2,0]);
  assert.deepEqual(data.all().ollama,[2,2,2,2,2]);
  assert.match(sparklinePath(data.all().chatgpt),/^M/);
  assert.ok(sparklinePath(data.all().chatgpt).includes('L'));
  assert.ok(!sparklinePath([Infinity,-1,NaN]).includes('NaN'));
  assert.throws(()=>sparklinePath([1,2],0,20));
  assert.throws(()=>new ActivityHistory(1000));
});
