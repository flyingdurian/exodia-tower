import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {AlbedoChibiController,DIRECTIONS,headingFromVector,validateChibiManifest,zoneForTaskState} from '../frontend/albedo_chibi_controller.mjs';
import {taskSummary,buildIdentity,renderCommandStatus} from '../frontend/command_status.mjs';
const p=fileURLToPath(new URL('../frontend/albedo_chibi_manifest.json',import.meta.url));
const manifest=JSON.parse(readFileSync(p,'utf8'));
const copy=()=>structuredClone(manifest);

test('8-direction heading contract covers all cardinal and diagonals (screen Y down)',()=>{
 assert.deepEqual(DIRECTIONS,['n','ne','e','se','s','sw','w','nw']);
 const v=[[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1],[-1,0],[-1,-1]];
 assert.deepEqual(v.map(([x,y])=>headingFromVector(x,y)),DIRECTIONS);
 assert.equal(headingFromVector(0,0,'sw'),'sw');
});
test('all 40 independently keyed frames are pending, not sliced or fabricated artwork',()=>{
 assert.equal(validateChibiManifest(manifest),true);
 assert.equal(manifest.motion.speed_normalized_per_second/manifest.motion.stride_frame_distance_normalized,manifest.states.walk.fps);
 assert.equal(Object.keys(manifest.frames).length,40);
 assert.ok(manifest.source_policy.independent_frames_required);
 assert.equal(manifest.production_release_enabled,false);
 for(const [id,frame] of Object.entries(manifest.frames)){
   assert.match(id,/^(idle_(n|ne|e|se|s|sw|w|nw)|walk_(n|ne|e|se|s|sw|w|nw)_0[0-3])$/);
   assert.equal(frame.src,null);assert.equal(frame.sha256,null);
 }
});
test('incomplete or falsified art provenance fails closed',()=>{
 let bad=copy();delete bad.frames.walk_sw_01;
 assert.throws(()=>validateChibiManifest(bad),/40/);
 bad=copy();bad.frames.idle_n.src='/assets/albedo_chibi/frames/crop.png';
 assert.throws(()=>validateChibiManifest(bad),/partially promoted/);
 bad=copy();bad.production_release_enabled=true;
 assert.throws(()=>validateChibiManifest(bad),/release gate/);
 bad=copy();bad.anchors.foot=[.1,.1];
 assert.throws(()=>validateChibiManifest(bad),/Foot registration/);
 bad=copy();bad.asset_status='approved_40_frame_set';
 assert.throws(()=>validateChibiManifest(bad),/Approved frames/);
});
test('all named floor zones are reachable and stop on exact foot anchors',()=>{
 for(const zone of Object.keys(manifest.zones)){
  const c=new AlbedoChibiController(manifest);
  c.goToZone(zone);
  for(let i=0;i<500&&!c.arrived;i++)c.tick(.05);
  assert.equal(c.arrived,true,'Failed to reach '+zone);
  assert.equal(c.mode,'idle');assert.equal(c.frame,0);
  assert.equal(c.position.x,manifest.zones[zone].x);assert.equal(c.position.y,manifest.zones[zone].y);
 }
});
test('walk frames track DISTANCE, not wall time, and duplicate polling cannot restart stride',()=>{
 const c=new AlbedoChibiController(manifest);
 c.goToZone('terminal');const before=c.snapshot();
 c.tick(.05);const a=c.snapshot();assert.equal(a.mode,'walk');assert.notDeepEqual({x:a.x,y:a.y},{x:before.x,y:before.y});
 c.dispatchTaskState('running');assert.equal(c.distanceInWalk,.015);
 c.tick(0);assert.equal(c.snapshot().frame,a.frame);
 c.tick(20);assert.ok(Math.hypot(c.position.x-a.x,c.position.y-a.y)<.016,'Tab sleep must not teleport');
 const snapshot=c.snapshot();assert.equal(snapshot.frame_key,`walk_${snapshot.heading}_${String(snapshot.frame).padStart(2,'0')}`);
});
test('provider task phases map to zones without invoking any provider adapter',()=>{
 assert.equal(zoneForTaskState('running',manifest),'terminal');
 assert.equal(zoneForTaskState('waiting_for_reply',manifest),'waiting');
 assert.equal(zoneForTaskState('answered',manifest),'result');
 assert.equal(zoneForTaskState('failed',manifest),'recovery');
 assert.equal(zoneForTaskState('cancelled',manifest),'home');
 const c=new AlbedoChibiController(manifest);
 c.dispatchTaskState('running','kiko');assert.equal(c.zone,'terminal');
 c.dispatchTaskState('answered','router');assert.equal(c.enabled,false);
 c.dispatchTaskState('answered','kiko');assert.equal(c.enabled,true);assert.equal(c.zone,'result');
});
test('header summaries are explicit and never print model custom instructions',()=>{
 const t={agent_id:'kiko',provider:'chatgpt',state:'waiting_for_reply',prompt:'Answer briefly',private_instructions:'my secret',metrics:{total_s:1.24}};
 const s=taskSummary(t,{agentName:()=> 'Albedo',providerName:()=> 'ChatGPT (chronos)'});
 assert.equal(s.agent,'Albedo');assert.equal(s.status,'Waiting for reply');assert.equal(s.provider,'ChatGPT (chronos)');assert.equal(s.latency,'1.24s');
 assert.ok(!JSON.stringify(s).includes('my secret'));
 assert.equal(taskSummary({...t,state:'cancelled'}).result,'Remote execution may continue');
 assert.equal(taskSummary(null,{selectedAgent:'Albedo',selectedProvider:'ChatGPT (chronos)'}).status,'No active task');
});
test('build channel/SHA are sourced from metadata, not invented',()=>{
 const actual=buildIdentity({version:'0.3.0',channel:'development',commit_sha:'a'.repeat(40),label:'EXODIA v0.3.0-dev · '+ 'a'.repeat(12)});
 assert.equal(actual.sha,'aaaaaaaaaaaa');assert.equal(actual.channel,'development');assert.equal(actual.verified,true);
 assert.equal(buildIdentity({version:'0.3.0',channel:'development',commit_sha:null}).sha,'unknown');
});
test('DOM status renderer uses textContent, never provider HTML',()=>{
 const nodes=Object.fromEntries(['summaryAgent','summaryTask','summaryProvider','summaryState','summaryResult','summaryLatency'].map(k=>[k,{textContent:''}]));
 const root={dataset:{},querySelector:s=>nodes[s.slice(1)]};
 renderCommandStatus(root,taskSummary({state:'answered',prompt:'<img onerror=alert(1)>',agent_id:'kiko',provider:'gemini',answer:'hi'}));
 assert.equal(nodes.summaryTask.textContent,'<img onerror=alert(1)>');
 assert.equal(root.dataset.state,'answered');assert.equal(root.dataset.busy,'false');
});
