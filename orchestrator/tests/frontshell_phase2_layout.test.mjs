import test from 'node:test';
import assert from 'node:assert/strict';
import {SCHEMA,LAYOUT_KEY,defaultLayout,validateLayout,
        readLayout,saveLayout,reduceLayout} from '../frontend/frontshell_layout_contract.mjs';
const memory=()=>({data:new Map(),
  getItem(k){return this.data.get(k)||null;},
  setItem(k,v){this.data.set(k,v);}});
test('default layout keeps the accepted response / centered hero / controls order',()=>{
  const initial=defaultLayout();
  assert.equal(initial.schema,SCHEMA);
  assert.deepEqual(initial.order,['output','hero','control']);
  assert.deepEqual(initial.compactOrder,['hero','output','control']);
  assert.equal(initial.expanded,null);
  assert.ok(Object.isFrozen(initial.order));
});
test('keyboard-equivalent moves persist exact validated roles and dimensions',()=>{
  const store=memory();
  let current=defaultLayout();
  current=reduceLayout(current,{type:'move',role:'hero',direction:-1});
  assert.deepEqual(current.order,['hero','output','control']);
  current=reduceLayout(current,{type:'move',role:'hero',direction:1,compact:true});
  assert.deepEqual(current.compactOrder,['output','hero','control']);
  current=reduceLayout(current,{type:'minimize',role:'control'});
  assert.equal(current.minimized.control,true);
  current=reduceLayout(current,{type:'expand',role:'control'});
  assert.equal(current.expanded,'control');
  assert.equal(current.minimized.control,false);
  assert.equal(saveLayout(store,current),true);
  assert.deepEqual(readLayout(store),current);
  assert.equal(store.data.size,1);
  assert.ok(store.data.has(LAYOUT_KEY));
  assert.equal(JSON.stringify(store.data).includes('prompt'),false);
  const reset=reduceLayout(current,{type:'reset'});
  assert.deepEqual(reset.order,['output','hero','control']);
  assert.deepEqual(reset.compactOrder,['hero','output','control']);
  assert.equal(reset.expanded,null);
});
test('layout fails closed on forged role, corrupted storage or bad action',()=>{
  const original=defaultLayout();
  assert.throws(()=>reduceLayout(original,{type:'move',role:'hero',direction:20}));
  assert.throws(()=>reduceLayout(original,{type:'shell',role:'hero'}));
  assert.throws(()=>reduceLayout(original,{type:'expand',role:'provider_keys'}));
  const store=memory();
  store.setItem(LAYOUT_KEY,'{"role":"invalid"}');
  assert.deepEqual(readLayout(store),defaultLayout());
  store.setItem(LAYOUT_KEY,JSON.stringify({...original,order:['hero','hero','control']}));
  assert.deepEqual(readLayout(store),defaultLayout());
  assert.throws(()=>validateLayout({...original,minimized:{output:0,hero:false,control:false}}));
  const blocked={getItem(){throw Error('disabled')},setItem(){throw Error('disabled')}};
  assert.deepEqual(readLayout(blocked),defaultLayout());
  assert.equal(saveLayout(blocked,original),false);
  assert.equal(saveLayout(null,original),false);
});
