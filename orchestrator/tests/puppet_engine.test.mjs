import test from 'node:test';
import assert from 'node:assert/strict';
import {PuppetEngine,solveTwoBone,shortestAngle,validateVisualManifest,REQUIRED_LAYERS} from '../frontend/puppet_engine.mjs';
import fs from 'node:fs';
const manifest=JSON.parse(fs.readFileSync(new URL('../frontend/rigs/kiko.json',import.meta.url)));
function canvas(){const c={};for(const name of ['save','restore','clearRect','translate','rotate','scale','drawImage','beginPath','moveTo','lineTo','stroke','arc','fill','ellipse'])c[name]=()=>{};return {width:530,height:625,getContext:()=>c}}
test('IK reaches a valid target with either elbow direction',()=>{
 for(const side of [-1,1]){const r=solveTwoBone({x:0,y:0},{x:30,y:15},25,20,side);
  assert.ok(Math.abs(Math.hypot(r.elbow.x,r.elbow.y)-25)<.0001);
  assert.ok(Math.abs(Math.hypot(r.elbow.x-30,r.elbow.y-15)-20)<.0001)}
});
test('IK bounds unreachable targets and validates lengths',()=>{
 assert.equal(solveTwoBone({x:0,y:0},{x:800,y:0},25,20).reached,false);
 assert.throws(()=>solveTwoBone({x:0,y:0},{x:1,y:1},0,20))
});
test('Shortest turn avoids spinning',()=>{assert.equal(shortestAngle(170,-170),20);assert.equal(shortestAngle(-170,170),-20)});
test('All painted layers required for production registration',()=>{
 const no=validateVisualManifest({layers:{}},manifest.bones);assert.equal(no.complete,false);assert.equal(no.missing.length,REQUIRED_LAYERS.length);
 const layers=Object.fromEntries(REQUIRED_LAYERS.map(b=>[b,{src:b+'.png',origin:[10,10]}]));
 assert.equal(validateVisualManifest({layers},manifest.bones).complete,true);
 assert.equal(validateVisualManifest({layers:{...layers,head:{src:'x',origin:[NaN,0]}}},manifest.bones).complete,false)
});
test('Emotion and activity articulate separate bones',()=>{
 const e=new PuppetEngine(canvas(),manifest);e.setEmotion('thinking');e.setActivity('wave');for(let i=0;i<30;i++)e.step(.016);
 assert.ok(Math.abs(e.pose.upper_arm_right)>40);assert.equal(Object.keys(e.world).length,22);
 assert.notEqual(e.world.hand_left.x,e.world.hand_right.x);
 assert.throws(()=>e.setEmotion('unsupported'));assert.throws(()=>e.setActivity('fly'))
});
test('Reached hand changes world joint positions',()=>{
 const e=new PuppetEngine(canvas(),manifest);e.step(.01);const before={...e.world.hand_right};
 e.reach('right',e.world.upper_arm_right.x+25,e.world.upper_arm_right.y+14);e.step(.016);
 assert.ok(Math.hypot(e.world.hand_right.x-before.x,e.world.hand_right.y-before.y)>1);
 assert.ok(Number.isFinite(e.pose.forearm_right))
});
test('Walk command moves at finite velocity and arrives',()=>{
 const e=new PuppetEngine(canvas(),manifest),x=e.position.x;
 e.moveTo(x+40,e.position.y);e.step(.016);assert.ok(e.position.x>x&&e.position.x<x+40);
 for(let i=0;i<100;i++)e.step(.016);
 assert.ok(Math.abs(e.position.x-x-40)<2);assert.equal(e.activity,'idle')
});
test('Speech viseme sequence terminates',()=>{
 const e=new PuppetEngine(canvas(),manifest);e.speak('hello');assert.equal(e.activity,'talk');
 for(let i=0;i<90;i++)e.step(.02);
 assert.equal(e.activity,'idle');assert.equal(e.viseme,'rest');assert.throws(()=>e.setViseme('INVALID'))
});
test('Reduced motion freezes automatic motion',()=>{
 const e=new PuppetEngine(canvas(),manifest,{reducedMotion:true});e.setEmotion('happy');e.step(.016);assert.equal(e.elapsed,0)
});