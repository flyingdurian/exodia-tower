import test from 'node:test';import assert from 'node:assert/strict';
import {reachAngles,ART_JOINTS} from '../frontend/kiko_art_engine.mjs';
test('neutral hand targets retain unshifted rig',()=>{
 for(const [side,xy] of [['left',[303,608]],['right',[862,658]]]){
 const v=reachAngles(side,{x:xy[0],y:xy[1]});
 assert.ok(Math.abs(v.arm)<.001);assert.ok(Math.abs(v.fore)<.001);
 }
});
test('IK targets remain numerically bounded',()=>{
 for(const side of ['left','right']){let v=reachAngles(side,{x:5000,y:-2000});
 assert.ok(Math.abs(v.arm)<=36);assert.ok(Math.abs(v.fore)<=55);}
});
test('required artwork pivots exist',()=>{
 for(const part of ['head','hair_front','torso','arm_left_upper','arm_left_fore','hand_left','arm_right_upper','arm_right_fore','hand_right','leg_front'])
 assert.equal(ART_JOINTS[part].at.length,2);
});