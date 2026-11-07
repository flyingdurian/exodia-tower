import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {AlbedoChibiController,validateChibiManifest,DIRECTIONS}
  from '../frontend/albedo_chibi_controller.mjs';
import {CHIBI_BEHAVIORS,choreographyBeat,IdleChoreography,routeCoordinates}
  from '../frontend/albedo_chibi_choreography.mjs';
const manifest=JSON.parse(readFileSync(new URL('../frontend/albedo_chibi_manifest.json',import.meta.url),'utf8'));
test('idle choreography is deterministic and uses only registered native heading keys',()=>{
  assert.equal(validateChibiManifest(manifest),true);
  for(const behavior of CHIBI_BEHAVIORS){
    const sequence=new IdleChoreography(behavior),first=sequence.snapshot();
    assert.ok(DIRECTIONS.includes(first.heading));
    for(let i=0;i<2300;i++)sequence.tick(.10);
    assert.ok(DIRECTIONS.includes(sequence.snapshot().heading));
    assert.equal(sequence.snapshot().source,'technical_headings_only');
    assert.equal(sequence.snapshot().artReleased,false);
  }
  assert.throws(()=>choreographyBeat('fake-celebration',0));
});
test('time clamps, pause, behavior transitions and reduced-motion disable idle steps',()=>{
  const anim=new IdleChoreography('success');
  const start=anim.snapshot();
  anim.pause(true);anim.tick(5000);
  assert.equal(anim.snapshot().steps,start.steps);
  anim.pause(false);
  anim.tick(5000);
  assert.equal(anim.snapshot().elapsed,.125);
  const frozen=anim.snapshot().elapsed;
  anim.tick(1,{idle:true,motion:false});
  assert.equal(anim.snapshot().elapsed,frozen);
  anim.setBehavior('failure');
  assert.equal(anim.snapshot().behavior,'failure');
  assert.equal(anim.snapshot().beat,0);
  assert.throws(()=>anim.tick(Infinity));
  assert.throws(()=>anim.tick(-1));
});
test('gaze cannot move foot, resume walk, or substitute unapproved art',()=>{
  const c=new AlbedoChibiController(manifest);
  const home={...c.position};
  c.faceIdle('ne');
  assert.equal(c.snapshot().heading,'ne');
  assert.deepEqual(c.position,home);
  assert.equal(c.snapshot().frame_key,'idle_ne');
  c.goToZone('terminal');c.tick(.05);
  const walking=c.snapshot();
  c.faceIdle('w');
  assert.equal(c.snapshot().heading,walking.heading,'Gaze must not override walk');
  assert.equal(c.snapshot().frame,walking.frame);
  assert.throws(()=>c.faceIdle('invalid'));
  assert.equal(manifest.production_release_enabled,false);
});
test('route overlay uses finite registered floor points only',()=>{
  const c=new AlbedoChibiController(manifest);
  c.goToZone('terminal');
  const route=routeCoordinates(c.snapshot(),c.waypoints);
  assert.ok(route.count>0);
  assert.match(route.path,/^M/);
  assert.ok(route.path.includes('L'));
  assert.deepEqual(route.target,c.waypoints.at(-1));
  assert.throws(()=>routeCoordinates(c.snapshot(),[{x:Infinity,y:0}]));
  assert.throws(()=>routeCoordinates(c.snapshot(),new Array(51).fill({x:.5,y:.5})));
  const arrived=routeCoordinates(c.snapshot(),[]);
  assert.equal(arrived.path,'');
  assert.equal(arrived.count,0);
});
