/* Local low-latency speech, no TTS API and no prerecorded provider audio. */
export const PROFILES={
 kiko:{pitch:1.18,rate:1.08,voiceHint:['zira','aria','jenny']},
 nova:{pitch:1.05,rate:1.09,voiceHint:['sonia','jenny','sara']},
 liu_bei:{pitch:.85,rate:1.02,voiceHint:['guy','david','mark']},
 mira:{pitch:1.0,rate:.94,voiceHint:['emma','hazel','zira']},
 lyra:{pitch:1.09,rate:.93,voiceHint:['aria','susan','sonia']},
 pip:{pitch:1.22,rate:1.17,voiceHint:['jenny','sara']},
 aurelia:{pitch:.99,rate:.9,voiceHint:['aria','zira']},
 nyx:{pitch:.91,rate:1.06,voiceHint:['guy','david']},
 mochi:{pitch:1.17,rate:1.06,voiceHint:['jenny','sara']},
 orion:{pitch:.83,rate:.95,voiceHint:['david','guy']}
};
export function readableSpeech(raw,max=1300){
 return String(raw||'')
 .replace(/https?:\/\/[^\s)]+/g,'')
 .replace(/\*\*|__|`|^#+\s*/gm,'')
 .replace(/^[-*]\s*/gm,'')
 .replace(/\b(?:1D|5D|1M|6M|YTD|MAX)\b(?:\s+|$)/g,'')
 .replace(/\s+/g,' ').trim().slice(0,max);
}
export function splitSpeechChunks(raw,maxChunk=220,maxTotal=1300){
 const content=readableSpeech(raw,maxTotal);
 if(!content)return [];
 const sentences=content.match(/[^.!?]+(?:[.!?]+["']?|$)/g)||[content];
 const chunks=[];
 let current='';
 const flush=()=>{if(current){chunks.push(current);current='';}};
 for(const sentenceValue of sentences){
  let sentence=sentenceValue.trim();
  while(sentence.length>maxChunk){
   flush();
   let cut=sentence.lastIndexOf(' ',maxChunk);
   if(cut<Math.floor(maxChunk*.55))cut=maxChunk;
   chunks.push(sentence.slice(0,cut).trim());
   sentence=sentence.slice(cut).trim();
  }
  if(!sentence)continue;
  if(current&&current.length+1+sentence.length>maxChunk)flush();
  current=current?current+' '+sentence:sentence;
 }
 flush();
 return chunks;
}
export function chooseVoice(voices,agent,override=''){
 const list=voices.filter(v=>/^en(?:-|_)/i.test(v.lang||''));
 if(!list.length)return voices[0]||null;
 const requested=override&&list.find(v=>v.voiceURI===override||v.name===override);
 if(requested)return requested;
 const local=list.filter(v=>v.localService!==false);
 const available=local.length?local:list;
 for(const hint of PROFILES[agent]?.voiceHint||[]){
  const found=available.find(v=>v.name.toLowerCase().includes(hint));
  if(found)return found;
 }
 return available[Math.min(Object.keys(PROFILES).indexOf(agent)%available.length,available.length-1)]||available[0];
}
export class VoiceDirector{
 constructor(speech=typeof window!=='undefined'?window.speechSynthesis:null,
             Utterance=typeof window!=='undefined'?window.SpeechSynthesisUtterance:null){
  this.speech=speech;this.Utterance=Utterance;this.enabled=false;this.auto=false;this.agent='kiko';this.current=null;this.onState=null;
 }
 available(){return Boolean(this.speech&&this.Utterance);}
 getVoices(){return this.available()?this.speech.getVoices():[];}
 setAgent(agent){this.agent=agent;}
 setAuto(on){this.auto=Boolean(on);if(!on)this.cancel();}
 setVoiceName(name){this.customVoice=name||'';}
 cancel(){this.current=null;if(this.available())this.speech.cancel();this.onState?.('idle');}
 speak(answer,{manual=false}={}){
  if(!this.available()||(!manual&&!this.auto))return false;
  const content=readableSpeech(answer);
  if(!content)return false;
  this.cancel();
  const profile=PROFILES[this.agent]||PROFILES.kiko;
  const utterance=new this.Utterance(content);
  utterance.voice=chooseVoice(this.getVoices(),this.agent,this.customVoice);
  utterance.pitch=profile.pitch;utterance.rate=profile.rate;utterance.volume=1;
  utterance.onstart=()=>this.onState?.('speaking');
  utterance.onend=()=>{if(this.current===utterance){this.current=null;this.onState?.('idle');}};
  utterance.onerror=()=>{if(this.current===utterance){this.current=null;this.onState?.('unavailable');}};
  this.current=utterance;
  this.speech.speak(utterance);
  return true;
 }
}
