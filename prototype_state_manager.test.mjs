import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';
import {PrototypePortraitStateManager,validPrototypeRegistry,PROTOTYPE_STATES} from './orchestrator/frontend/prototype_state_manager.mjs';

const assetRoot=new URL('./orchestrator/frontend/prototype_assets/albedo/',import.meta.url);
const registry=JSON.parse(await readFile(new URL('prototype_registry.json',assetRoot),'utf8'));
class FakeImage {
  constructor(){this.style={};this.attrs={};this.naturalWidth=1536;this.naturalHeight=1920;this.offsetWidth=300;}
  setAttribute(k,v){this.attrs[k]=v;}
  async decode(){return true;}
  remove(){}
}
class FakeContainer{
  constructor(){this.classes=[];this.images=[];this.attrs={};this.classList={add:(x)=>this.classes.push(x)};}
  appendChild(img){this.images.push(img);}
  setAttribute(k,v){this.attrs[k]=v;}
  dispatchEvent(ev){this.lastEvent=ev;}
}
globalThis.window={matchMedia:()=>({matches:false})};
globalThis.document={createElement:()=>new FakeImage()};
globalThis.Image=FakeImage;
globalThis.location={href:'https://exodia.local/workbench.html'};

async function fromFixture(url){
 const name=new URL(url,location.href).pathname.split('/').at(-1);
 const asset=name==='prototype_registry.json' ? new URL('prototype_registry.json',assetRoot):new URL(name,assetRoot);
 try{return new Response(await readFile(asset),{status:200,headers:{'content-type':name.endsWith('.png')?'image/png':'application/json'}});}
 catch{return new Response('Not found',{status:404});}
}

test('valid 5-state preview registry cannot impersonate the 33-state production release',()=>{
 assert.equal(validPrototypeRegistry(registry),true);
 assert.equal(registry.production_release_enabled,false);
 assert.deepEqual(Object.keys(registry.states),PROTOTYPE_STATES);
 const bad=structuredClone(registry);bad.production_release_enabled=true;
 assert.equal(validPrototypeRegistry(bad),false);
 assert.equal(registry.states.pointing.path,null);
 assert.equal(registry.states.pointing.availability,'pending_master');
});

test('all 5 images have a separate hashed path and can transition in place',async()=>{
 const target=new FakeContainer();
 const manager=new PrototypePortraitStateManager({manifestUrl:'https://exodia.local/prototype_assets/albedo/prototype_registry.json',fetcher:fromFixture,container:target});
 await manager.initialize();
 assert.equal(target.images.length,2);
 for(const state of PROTOTYPE_STATES.filter(s=>s!=='pointing')){
  assert.equal(await manager.setState(state),true);
  assert.equal(manager.current,state);
  assert.equal(target.lastEvent.detail.state,state);
  assert.equal(target.images.filter(x=>x.style.opacity==='1').length,1);
 }
 assert.equal(manager.cache.size,4);
 assert.equal(manager.events.length,4);
 await assert.rejects(()=>manager.setState('pointing'),/pending real pointing-hand source/);
 manager.clear();
 assert.equal(manager.cache.size,0);
});

test('mismatched hash is rejected before image display',async()=>{
 const bad=structuredClone(registry);bad.states.idle.sha256='0'.repeat(64);
 const manager=new PrototypePortraitStateManager({manifestUrl:'https://exodia.local/prototype_assets/albedo/prototype_registry.json',fetcher:async url=> {
  if(String(url).includes('prototype_registry.json'))return new Response(JSON.stringify(bad),{status:200});
  return fromFixture(url);
 },container:new FakeContainer()});
 await manager.initialize();
 await assert.rejects(()=>manager.setState('idle'),/SHA-256 mismatch/);
});
