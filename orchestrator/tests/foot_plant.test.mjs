import test from 'node:test';
import assert from 'node:assert/strict';
import {FootPlantPlanner} from '../frontend/foot_plant.mjs';
test('a planted foot remains fixed while the root advances',()=>{
 const g=new FootPlantPlanner();const root={x:220,y:350};g.reset(root);
 const first=g.update(.01,root,true,{x:1,y:0}).left;assert.equal(first.planted,true);
 for(let n=0;n<13;n++){root.x+=2;const x=g.update(.01,root,true,{x:1,y:0}).left;
  assert.equal(x.planted,true);assert.equal(x.x,first.x);}
});
test('swing foot lifts and lands while returning finite positions',()=>{
 const g=new FootPlantPlanner();const root={x:220,y:350};let lifted=false,swung=false,planted=false;
 for(let n=0;n<120;n++){root.x+=.5;const a=g.update(.01,root,true,{x:1,y:0});
  for(const f of Object.values(a)){assert.ok(Number.isFinite(f.x)&&Number.isFinite(f.y));
   lifted ||= !f.planted&&f.y<root.y+51;swung ||= !f.planted;planted ||=f.planted;}}
 assert.ok(lifted&&swung&&planted);
});
test('reset stops gait without displacement and bad settings reject',()=>{
 const g=new FootPlantPlanner();g.update(.04,{x:200,y:300});const rest=g.update(.01,{x:200,y:300},false);
 assert.equal(rest.left.planted,true);assert.equal(rest.right.planted,true);
 assert.throws(()=>new FootPlantPlanner({period:0}));
});