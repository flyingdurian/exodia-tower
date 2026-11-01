import test from 'node:test';import assert from 'node:assert/strict';
import {VoiceDirector,readableSpeech,chooseVoice,PROFILES} from '../frontend/companion_voice.mjs';
test('10 agents have different natural speech profiles',()=>{
 assert.equal(Object.keys(PROFILES).length,10);
 assert.notEqual(PROFILES.kiko.pitch,PROFILES.riven.pitch);
});
test('speech reading strips formatting and media URLs',()=>{
 assert.equal(readableSpeech('**Weather**: 15°C. https://example.com/photo.png'),'Weather: 15°C.');
});
test('voice prefers installed local voices',()=>{
 const voices=[{name:'Online Aria',lang:'en-US',localService:false},{name:'Microsoft Aria',lang:'en-US',localService:true}];
 assert.equal(chooseVoice(voices,'kiko').name,'Microsoft Aria');
});
test('speak is triggered only manually or by explicit auto setting',()=>{
 const calls=[];const synth={cancel(){calls.push('cancel')},speak(x){calls.push('speak');this.last=x},getVoices(){return [{name:'Aria',lang:'en-US',localService:true}]}};
 class Utterance{constructor(text){this.text=text}}
 const director=new VoiceDirector(synth,Utterance);director.setAgent('kiko');
 assert.equal(director.speak('Hi.'),false);
 assert.equal(director.speak('Hi.',{manual:true}),true);
 assert.equal(synth.last.text,'Hi.');
 director.setAuto(true);assert.equal(director.speak('Ready.'),true);
 director.cancel();assert.equal(calls.filter(x=>x==='speak').length,2);
});
