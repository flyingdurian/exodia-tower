import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {startAlbedoChibi} from '../frontend/albedo_chibi_boot.mjs';

const manifest=JSON.parse(readFileSync(fileURLToPath(new URL('../frontend/albedo_chibi_manifest.json',import.meta.url)),'utf8'));

function fakeUI(){
  const callbacks={};const clickCallbacks=new Map();const children=[];
  const actor={hidden:false,style:{setProperty(){}},dataset:{}};
  const heading={textContent:''};
  const marker={hidden:false,querySelector:()=>heading};
  const zoneText={textContent:'',parentElement:{append(node){children.push(node)}}};
  const artStatus={textContent:''},image={hidden:true,src:''};
  const floor={clientWidth:600,clientHeight:240};
  const controls=['terminal','waiting'].map(zone=>({dataset:{chibiGo:zone},addEventListener(_,cb){clickCallbacks.set(zone,cb)}}));
  const nodes={chibiActor:actor,chibiArtStatus:artStatus,chibiMarker:marker,chibiFrame:image,
    chibiZoneState:zoneText,chibiFloor:floor};
  const root={dataset:{},querySelector(selector){return nodes[selector.slice(1)]},querySelectorAll(){return controls}};
  const companion={value:'kiko',addEventListener(event,cb){callbacks['companion:'+event]=cb},removeEventListener(){}};
  const doc={getElementById(id){return {chibiOperations:root,chibiArtStatus:artStatus,companion}[id]},
    createElement(){return {id:'',textContent:'',setAttribute(){}}}};
  const win={addEventListener(event,cb){callbacks[event]=cb},removeEventListener(){},requestAnimationFrame(){return 1},
    cancelAnimationFrame(){},matchMedia(){return {matches:false}}};
  return {doc,win,root,actor,artStatus,children,companion,callbacks,clickCallbacks};
}

test('real module boot uses scoped manifest and binds task updates plus developer path controls',async()=>{
  const h=fakeUI();const runtime=await startAlbedoChibi({doc:h.doc,win:h.win,loadManifest:async()=>manifest});
  assert.ok(runtime,'Boot must not silently fail after successful manifest validation');
  assert.equal(h.root.dataset.ready,'1');assert.equal(h.children[0].id,'chibiBehaviorCue');
  assert.equal(h.artStatus.textContent.includes('40 ART FRAMES PENDING'),true);
  h.callbacks['exodia:command-task']({detail:{taskId:'t1',agentId:'kiko',state:'running',updatedAt:'2026-11-04T10:00:01Z'}});
  assert.equal(runtime.controller.zone,'terminal');assert.equal(h.root.dataset.behavior,'processing');
  assert.equal(h.children[0].textContent,'Working at terminal');
  h.clickCallbacks.get('waiting')();assert.equal(runtime.controller.zone,'waiting');
  h.companion.value='liu_bei';h.callbacks['companion:change']();assert.equal(h.actor.hidden,true);
  h.clickCallbacks.get('terminal')();assert.equal(runtime.controller.zone,'waiting','Offstage test controls must not move Albedo');
  runtime.stop();
});
