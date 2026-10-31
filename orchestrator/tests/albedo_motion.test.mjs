import test from 'node:test';
import assert from 'node:assert/strict';
import {KikoArtEngine,ALBEDO_PERFORMANCES} from '../frontend/kiko_art_engine.mjs';
import {AlbedoMotionStage,MOTION_MODES,validatePerformanceMap} from '../frontend/albedo_motion.mjs';

test('All ten requested emotions have distinct real character motion plans',()=>{
  assert.equal(validatePerformanceMap(),true);
  assert.equal(ALBEDO_PERFORMANCES.length,10);
  const engine=Object.create(KikoArtEngine.prototype);
  engine.driver={
    pose:{},setEmotion(name){this.emotion=name},setActivity(name){this.activity=name}
  };
  engine.elapsed=1;engine.release=()=>{engine.handTarget=null};engine.performanceAt=0;
  const rotations=[];
  for(const state of ALBEDO_PERFORMANCES){
    engine.setPerformance(state);
    engine.performanceAt=0;
    const a=engine._angles();
    rotations.push([state,a.head,a.torso,a.arm_left_upper,a.arm_left_fore,
      a.arm_right_upper,a.arm_right_fore,a.leg_back,a.leg_front]);
  }
  const serialized=rotations.map(x=>JSON.stringify(x.slice(1)));
  assert.equal(new Set(serialized).size,10,'each state must alter actual rig joint transforms');
});

test('Motion changes over time inside each active performance',()=>{
  const engine=Object.create(KikoArtEngine.prototype);
  engine.driver={pose:{},setEmotion(){},setActivity(){}};
  engine.release=()=>{engine.handTarget=null};
  for(const state of ['processing','waiting','thinking','frustration','happy','excited']){
    engine.setPerformance(state);
    engine.performanceAt=0;
    engine.elapsed=1;
    const first=engine._angles();
    engine.elapsed=1.3;
    const later=engine._angles();
    assert.notDeepEqual(first,later,state+' must not be a frozen pose');
  }
});

test('Homepage motion controller displays articulated canvas for nine active states',()=>{
  const video={hidden:false,pauseCount:0,playCount:0,pause(){this.pauseCount++},play(){this.playCount++;return Promise.resolve()}};
  const canvas={hidden:true};
  const stage=new AlbedoMotionStage(canvas,video,{clock:()=>1});
  let count=0;
  stage.engine={setPerformance(state){this.state=state;count++},getArtQA(){return {ready:Array(13).fill(1)}}};
  stage.ready=true;
  for(const state of ALBEDO_PERFORMANCES){
    stage.setState(state);
    assert.equal(canvas.hidden,state==='idle');
    assert.equal(video.hidden,state!=='idle');
    assert.equal(stage.engine.state,state);
    assert.equal(MOTION_MODES[state].art,state==='idle'?'video':'rig');
  }
  assert.equal(count,10);
  assert.equal(stage.snapshot().production_ready,false);
  stage.setPaused(true);assert.equal(stage.paused,true);
});
