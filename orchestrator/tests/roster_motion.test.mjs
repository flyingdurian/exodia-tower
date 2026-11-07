import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PuppetEngine} from '../frontend/puppet_engine.mjs';
const dir=fileURLToPath(new URL('../frontend/rigs/',import.meta.url));
function canvas(){const ctx={};for(const n of ['save','restore','clearRect','translate','rotate','scale','drawImage','beginPath','moveTo','lineTo','stroke','arc','fill','ellipse'])ctx[n]=()=>{};return {width:530,height:625,getContext:()=>ctx};}
test('all ten companions expose full 22-bone, 24-emotion rig controls',()=>{
 const paths=fs.readdirSync(dir).filter(n=>n.endsWith('.json'));
 assert.equal(paths.length,10);
 for(const file of paths){
  const rig=JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
  assert.equal(Object.keys(rig.bones).length,22,file);
  assert.equal(Object.keys(rig.poses).length,24,file);
  const actor=new PuppetEngine(canvas(),rig);
  for(const emotion of Object.keys(rig.poses)){actor.setEmotion(emotion);actor.step(.016);}
  actor.setActivity('walk');actor.moveTo(310,350);for(let i=0;i<35;i++)actor.step(.016);
  assert.ok(Number.isFinite(actor.world.foot_left.x),file);
  assert.ok(Number.isFinite(actor.world.foot_right.y),file);
  assert.equal(actor.sprites.size,0,'Production artwork cannot be inferred from flattened portraits');
 }
});