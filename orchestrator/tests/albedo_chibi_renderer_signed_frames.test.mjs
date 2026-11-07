import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash,webcrypto} from 'node:crypto';
import {AlbedoChibiController,validateChibiManifest} from '../frontend/albedo_chibi_controller.mjs';
import {AlbedoChibiRenderer} from '../frontend/albedo_chibi_renderer.mjs';

const pending=JSON.parse(readFileSync(
  new URL('../frontend/albedo_chibi_manifest.json',import.meta.url),'utf8'));
function signedFixture(){
  const manifest=structuredClone(pending);
  manifest.asset_status='approved_40_frame_set';
  const bytes=new Map();
  let index=1;
  for(const key of Object.keys(manifest.frames)){
    const data=new Uint8Array([index++,19,44,192]);
    bytes.set(key,data);
    const hash=createHash('sha256').update(data).digest('hex');
    manifest.frames[key]={
      status:'owner_approved',
      src:'/assets/albedo_chibi/frames/'+key+'.png',
      sha256:hash,approval_sha256:hash,
      source_provenance:{source_kind:'independent_standalone'}
    };
  }
  assert.equal(validateChibiManifest(manifest),true);
  return {manifest,bytes};
}
function ui(){
  const marker={hidden:false,querySelector:()=>({textContent:''})};
  const actor={style:{setProperty(){}},dataset:{},hidden:false};
  const image={src:'',hidden:true};
  const status={textContent:''};
  const nodes={chibiActor:actor,chibiMarker:marker,chibiFrame:image,
    chibiArtStatus:status,chibiZoneState:{textContent:''}};
  return {root:{querySelector:key=>nodes[key.slice(1)]},
    marker,actor,image,status};
}
test('approved independent frames are fetched ahead per heading and SHA-verified',async()=>{
  const {manifest,bytes}=signedFixture();
  const harness=ui();
  const requested=[];
  const old=globalThis.createImageBitmap;
  globalThis.createImageBitmap=async()=>({width:192,height:256,close(){}});
  const renderer=new AlbedoChibiRenderer(harness.root,manifest,{
    cryptoProvider:webcrypto,
    fetcher:async url=>{
      requested.push(url);
      const key=url.slice(url.lastIndexOf('/')+1,-4);
      return {ok:true,blob:async()=>new Blob([bytes.get(key)],{type:'image/png'})};
    }
  });
  try{
    const controller=new AlbedoChibiController(manifest);
    renderer.draw(controller.snapshot()); // idle south warms all five south frames
    assert.equal(renderer.prefetchedHeadings.has('s'),true);
    await Promise.all([...renderer.pendingFrames.values()]);
    renderer.draw(controller.snapshot());
    assert.equal(requested.length,5);
    assert.equal(harness.image.hidden,false);
    assert.equal(harness.marker.hidden,true);
    assert.match(harness.image.src,/^blob:/);
    renderer.draw(controller.snapshot()); // no redundant heading fetch
    assert.equal(requested.length,5);
    controller.goToPoint(.17,.24);controller.tick(.05);
    renderer.draw(controller.snapshot());
    assert.equal(controller.heading,'n');
    assert.equal(renderer.prefetchedHeadings.has('n'),true);
    await Promise.all([...renderer.pendingFrames.values()]);
    assert.equal(requested.length,10);
    assert.equal(manifest.production_release_enabled,false);
  }finally{
    renderer.destroy();
    globalThis.createImageBitmap=old;
  }
});
test('SHA mismatch never displays unverified signed asset',async()=>{
  const {manifest,bytes}=signedFixture();
  manifest.frames.idle_s.sha256='f'.repeat(64);
  manifest.frames.idle_s.approval_sha256='f'.repeat(64);
  validateChibiManifest(manifest);
  const harness=ui();
  const old=globalThis.createImageBitmap;
  globalThis.createImageBitmap=async()=>({width:192,height:256,close(){}});
  const renderer=new AlbedoChibiRenderer(harness.root,manifest,{
    cryptoProvider:webcrypto,
    fetcher:async url=>{
      const key=url.slice(url.lastIndexOf('/')+1,-4);
      return {ok:true,blob:async()=>new Blob([bytes.get(key)],{type:'image/png'})};
    }
  });
  try{
    const controller=new AlbedoChibiController(manifest);
    renderer.draw(controller.snapshot());
    await Promise.all([...renderer.pendingFrames.values()]);
    renderer.draw(controller.snapshot());
    assert.equal(harness.image.hidden,true);
    assert.equal(harness.marker.hidden,false);
    assert.equal(renderer.readyFrames.has('idle_s'),false);
  }finally{
    renderer.destroy();
    globalThis.createImageBitmap=old;
  }
});
test('all 40 pending production frames never trigger any asset fetch',async()=>{
  const harness=ui();
  let count=0;
  const renderer=new AlbedoChibiRenderer(harness.root,pending,{
    fetcher:async()=>{count++;throw Error('No pending frame is permitted to fetch');}
  });
  renderer.draw(new AlbedoChibiController(pending).snapshot());
  assert.equal(count,0);
  assert.equal(harness.image.hidden,true);
  assert.equal(harness.marker.hidden,false);
  renderer.destroy();
});
