import test from 'node:test';import assert from 'node:assert/strict';
import {VoiceDirector,readableSpeech,splitSpeechChunks,chooseVoice,PROFILES} from '../frontend/companion_voice.mjs';
test('10 agents have different natural speech profiles',()=>{
 assert.equal(Object.keys(PROFILES).length,10);
 assert.notEqual(PROFILES.kiko.pitch,PROFILES.liu_bei.pitch);
});
test('speech reading strips formatting and media URLs',()=>{
 assert.equal(readableSpeech('**Weather**: 15°C. https://example.com/photo.png'),'Weather: 15°C.');
});
test('natural speech is split into short ordered chunks',()=>{
 const source='First sentence is ready quickly. Second sentence contains more useful detail. '+('Long explanation segment '.repeat(18));
 const chunks=splitSpeechChunks(source,90,700);
 assert.ok(chunks.length>2);
 assert.ok(chunks.every(chunk=>chunk.length<=90));
 assert.equal(chunks.join(' ').replace(/\s+/g,' '),readableSpeech(source,700));
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
