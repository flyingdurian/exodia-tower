import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultLayout} from '../frontend/frontshell_layout_contract.mjs';
import {BUILTINS,builtinPreset,PRESET_KEY,readPresets,savePreset,presetFor}
  from '../frontend/frontshell_presets_contract.mjs';
import {ACTIONS,searchActions,actionById,safeOperatorNotice}
  from '../frontend/frontshell_palette_contract.mjs';
const storage=()=>({values:new Map(),
 getItem(k){return this.values.get(k)||null;},
 setItem(k,v){this.values.set(k,v)}});
test('named workspace presets expand only the selected panel',()=>{
  assert.deepEqual(BUILTINS,['command','investigation','operations','triage']);
  assert.equal(builtinPreset('command').expanded,null);
  assert.equal(builtinPreset('investigation').expanded,'output');
  assert.equal(builtinPreset('operations').expanded,'hero');
  assert.equal(builtinPreset('triage').expanded,'control');
  assert.deepEqual(builtinPreset('command').compactOrder,['hero','output','control']);
  assert.throws(()=>builtinPreset('all-providers-authorized'));
});
test('three browser-only slots persist validated layout and discard extraneous data',()=>{
  const mem=storage();
  const preset={...defaultLayout(),expanded:'hero',
    prompt:'SECRET_PROMPT',token:'SECRET_TOKEN'};
  assert.equal(savePreset(mem,'custom1',preset),true);
  assert.equal(mem.values.size,1);
  assert.ok(mem.values.has(PRESET_KEY));
  const output=JSON.stringify(readPresets(mem));
  assert.equal(output.includes('SECRET_PROMPT'),false);
  assert.equal(output.includes('SECRET_TOKEN'),false);
  assert.equal(presetFor(mem,'custom1').expanded,'hero');
  assert.equal(presetFor(mem,'custom3'),null);
  assert.throws(()=>savePreset(mem,'execute-bash',preset));
  mem.setItem(PRESET_KEY,'INVALID_JSON');
  assert.deepEqual(readPresets(mem).slots,{});
  const noStore={setItem(){throw Error('denied')},getItem(){throw Error('denied')}};
  assert.equal(savePreset(noStore,'custom2',defaultLayout()),false);
});
test('palette actions are a closed set with only known paths and local UI actions',()=>{
  assert.ok(ACTIONS.length>=12);
  const ids=new Set(ACTIONS.map(x=>x.id));
  assert.equal(ids.size,ACTIONS.length);
  assert.ok(ACTIONS.filter(x=>x.kind==='navigate').every(x=>
    ['/', '/operations-legacy','/workflow-planner','/companions'].includes(x.path)));
  assert.equal(searchActions('workflow')[0].id,'go-workflows');
  assert.ok(searchActions('preset').length>=4);
  assert.equal(searchActions('<script>alert(1)</script>').length,0);
  assert.equal(actionById('execute provider send'),null);
  assert.equal(actionById('go-workflows').path,'/workflow-planner');
  assert.ok(!JSON.stringify(ACTIONS).includes('POST'));
});
test('operator notice label is bounded and never echoes task prompt or answer',()=>{
  const event={taskId:'task-1',agentId:'liu_bei',state:'failed',
    prompt:'SUPERSECRET',answer:'HIDDEN_ANSWER',cookie:'SENSITIVE_COOKIE'};
  const result=safeOperatorNotice(event);
  assert.deepEqual({label:result.label,requiresAttention:result.requiresAttention},
   {label:'LIU BEI · TASK FAILED',requiresAttention:true});
  for(const str of ['SUPERSECRET','HIDDEN_ANSWER','SENSITIVE_COOKIE'])
    assert.ok(!JSON.stringify(result).includes(str));
  assert.equal(safeOperatorNotice({...event,state:'authenticated'}),null);
  assert.equal(safeOperatorNotice({...event,state:'answered'}).providerAuthenticated,false);
});
