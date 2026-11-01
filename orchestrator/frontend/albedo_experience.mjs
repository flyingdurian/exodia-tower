import {VoiceDirector,readableSpeech} from './companion_voice.mjs';

/* Public Exodia companion UX: portrait expression plates, generated media,
 * and opt-in instant system speech. No debug puppet preview or fake talk wobble. */
const $=selector=>document.querySelector(selector);
const voice=new VoiceDirector();
let neuralAudio=null,voiceVersion=0;
function stopNeural(){
 voiceVersion++;
 if(neuralAudio){neuralAudio.pause();URL.revokeObjectURL(neuralAudio.src);neuralAudio=null;}
}
async function speakCompanion(text,agent,{manual=false}={}){
 if(!manual&&!voice.auto)return false;
 const spoken=readableSpeech(text,950);
 if(!spoken)return false;
 stopNeural();
 if($('#ttsEngine')?.value==='system')return voice.speak(spoken,{manual:true});
 voice.cancel();
 const version=voiceVersion;
 voiceStatus('Preparing natural companion voice…');
 try{
   const res=await fetch('/api/voice/speak',{
      method:'POST',headers:{'X-Exodia-Client':'exodia-dashboard','Content-Type':'application/json'},
      body:JSON.stringify({agent_id:agent,text:spoken})});
   if(!res.ok){
      let problem='Neural TTS unavailable';try{problem=(await res.json()).detail||problem}catch{}
      throw Error(problem);
   }
   const blob=await res.blob();
   if(version!==voiceVersion)return false;
   const src=URL.createObjectURL(blob);
   neuralAudio=new Audio(src);
   neuralAudio.onended=()=>{if(version===voiceVersion){voiceStatus('Speech complete');URL.revokeObjectURL(src);neuralAudio=null;}};
   neuralAudio.onerror=()=>voiceStatus('Audio playback failed');
   await neuralAudio.play();
   voiceStatus('Speaking with local neural voice…');
   return true;
 }catch(e){
   voiceStatus(e.message+' · Choose system fallback or start Kokoro.');
   return false;
 }
}
const STATES=['idle','sleeping','processing','waiting','thinking','failed','frustration','happy','excited','proud'];
const labels={
  idle:'Ready',sleeping:'Resting',processing:'Working',waiting:'Awaiting reply',
  thinking:'Thinking',failed:'Task failed',frustration:'Regrouping',
  happy:'Successful',excited:'Celebrating',proud:'Mission complete'
};
let active='',activeId='',lastMediaKey='',lastSpokenId='',lastAgent='kiko',lastRenderedAnswer='';
let lastAttentionId='';
let atlasAvailable=false,agents=[];
const EPOCH=Date.now();
const computerStates={
 idle:['✦','All systems ready','Your companion is waiting for a command'],
 sleeping:['☾','Rest mode','Quiet time in the digital lounge'],
 processing:['⌨','Working on your task','Preparing and dispatching the prompt'],
 thinking:['◇','Analyzing','Working through the details'],
 waiting:['◌','Awaiting model response','Monitoring the live response stream'],
 failed:['×','Action failed','See diagnostics and the task response'],
 frustration:['!','Reassessing','Preparing a fresh route'],
 happy:['✓','Mission complete','Your response is ready'],
 excited:['✧','Great result!','The response is now in your terminal'],
 proud:['✓','Delivered to terminal','View the answer in the next panel']
};
function paintComputer(key){
 const data=computerStates[key]||computerStates.idle;
 const el=$('#computerSymbol');if(el)el.textContent=data[0];
 const title=$('#computerTitle');if(title)title.textContent=data[1];
 const sub=$('#computerSubtitle');if(sub)sub.textContent=data[2];
 const btn=$('#resultPointer');if(btn)btn.hidden=!['happy','excited','proud'].includes(key);
 const model=$('#computerModel');if(model)model.textContent=$('#model')?.selectedOptions[0]?.textContent.split(' · ')[0]||'STANDBY';
}
function selectAgentStage(id){
 const info=agents.find(a=>a.id===id);
 if(!info)return;
 const name=$('#agentStageName');if(name)name.textContent=info.name;
 const role=$('#agentStageRole');if(role)role.textContent=info.pillar||info.title||'Companion';
 const face=$('#expressionFace'),portrait=$('#agentPortrait');
 if(face&&portrait){
   const showAtlas=id==='kiko'&&atlasAvailable;
   face.hidden=!showAtlas;
   portrait.hidden=showAtlas;
   if(!showAtlas){portrait.src=info.thumbnail||info.portrait||'/assets/companions/thumbs/kiko.webp';portrait.alt=info.name+' portrait';}
 }
}
async function loadAgentRoster(){
 try{
  const resp=await fetch('/api/companions');if(!resp.ok)return;
  agents=(await resp.json()).agents||[];
  selectAgentStage($('#companion')?.value||'kiko');
 }catch(error){/* Default portrait remains available */ }
}
const atlasCheck=new Image();
atlasCheck.onload=()=>{atlasAvailable=true;selectAgentStage($('#companion')?.value||'kiko');};
atlasCheck.onerror=()=>{atlasAvailable=false;selectAgentStage($('#companion')?.value||'kiko');};
atlasCheck.src='/assets/companions/expressions/albedo_expression_atlas.webp';
loadAgentRoster();
$('#resultPointer')?.addEventListener('click',()=>$('#answerFrame')?.scrollIntoView({block:'center',behavior:'smooth'}));
function expression(state){
 if(!STATES.includes(state)||active===state)return;
 active=state;
 const card=$('#expressionCard'),face=$('#expressionFace');
 if(!card||!face)return;
 card.classList.add('changing');
 setTimeout(()=>{
   const n=STATES.indexOf(state);
   face.style.backgroundPosition=(25*(n%5))+'% '+(100*Math.floor(n/5))+'%';
   paintComputer(state);
   $('#expressionName').textContent=labels[state]||state;
   card.classList.remove('changing');
 },160);
}
function captureExpressionState(){
 const raw=($('#moodLabel')?.textContent||'IDLE').trim().toLowerCase().replaceAll(' ','_');
 expression(raw==='failed_result'?'failed':raw==='happy_success'?'happy':raw==='excited_success'?'excited':raw);
}
const label=$('#moodLabel');
if(label)new MutationObserver(captureExpressionState).observe(label,{childList:true,characterData:true,subtree:true});
captureExpressionState();
document.documentElement.dataset.expressionControllerReady='1';
function element(tag,cls,text){
 const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;
}
function renderMedia(task){
 const gallery=$('#mediaGallery');if(!gallery)return;
 const items=Array.isArray(task?.media)?task.media.filter(x=>x.url):[];
 if(task?.artifact&&!items.some(x=>x.url===task.artifact))items.unshift({kind:'image',url:task.artifact});
 const key=JSON.stringify([task?.id,[...new Set(items.map(x=>x.url))]]);if(lastMediaKey===key)return;
 lastMediaKey=key;gallery.replaceChildren();
 const shown=new Set();
 for(const item of items){
  const url=String(item.url||'');
  if(shown.has(url))continue;
  shown.add(url);
  if(!/^\/artifacts\/[a-f0-9]{32}\.(png|jpg|jpeg|webp|mp4|webm)$/.test(url))continue;
  const card=element('div','media-item'),media=item.kind==='video'?element('video'):element('img');
  media.src=url;
  if(item.kind==='video'){media.controls=true;media.preload='metadata';media.playsInline=true;}
  else media.alt='Generated companion image';
  const row=element('div','media-info'),caption=element('span','',item.kind==='video'?'Video generated by '+task.provider:'Image generated by '+task.provider);
  const link=element('a','','Download');link.href=url;link.download='';
  row.append(caption,link);card.append(media,row);gallery.append(card);
 }
 const failures=(task?.media||[]).filter(x=>x.status==='capture_failed');
 if(failures.length)gallery.append(element('p','muted',failures.length+' file(s) were generated but the local import failed; open the Gemini window and inspect the saved diagnostic screenshot.'));
}
function voiceStatus(message){$('#speechStatus').textContent=message}
function updateVoices(){
 const select=$('#voiceChoice');if(!select)return;
 const current=select.value;
 select.replaceChildren();
 const auto=element('option','','Automatic voice for companion');auto.value='';select.append(auto);
 const options=voice.getVoices().filter(x=>/^en(?:-|_)/i.test(x.lang||''));
 for(const v of options){const option=element('option','',v.name+(v.localService===false?' (online)':''));option.value=v.voiceURI||v.name;select.append(option);}
 select.value=current;
 voiceStatus(voice.available()?options.length+' available English voice(s)':'Speech not supported here');
}
voice.onState=state=>{
 if($('#ttsEngine')?.value==='system')
   voiceStatus(state==='speaking'?'Reading response…':state==='unavailable'?'Speech synthesis unavailable':'Speech ready');
};
updateVoices();
if(voice.available())speechSynthesis.addEventListener?.('voiceschanged',updateVoices);
$('#autoSpeech')?.addEventListener('change',event=>{
 voice.setAuto(event.target.checked);
 voiceStatus(event.target.checked?'Auto speech enabled; neural service used when selected':'Voice autoplay disabled');
});
$('#ttsEngine')?.addEventListener('change',event=>{
 stopNeural();voice.cancel();
 voiceStatus(event.target.value==='neural'?'Natural Kokoro voice: requires local TTS service on port 8880':'System voice fallback selected');
});
$('#voiceChoice')?.addEventListener('change',event=>voice.setVoiceName(event.target.value));
$('#companion')?.addEventListener('change',event=>{
 voice.setAgent(event.target.value);
 selectAgentStage(event.target.value);
});
$('#speakNow')?.addEventListener('click',()=>{
 voice.setAgent(lastAgent);
 if(!lastRenderedAnswer)voiceStatus('No completed text response to speak.');
 else speakCompanion(lastRenderedAnswer,lastAgent,{manual:true});
});
$('#stopSpeech')?.addEventListener('click',()=>{stopNeural();voice.cancel();});
async function refreshDelivery(){
 const selected=document.querySelector('.task-item.active');
 const id=selected?.dataset.id||'';
 if(!id){if(activeId){activeId='';lastMediaKey='';renderMedia(null);}return;}
 try{
  const response=await fetch('/api/command/tasks',{headers:{'X-Exodia-Client':'exodia-dashboard'}});
  if(!response.ok)return;
  const rows=(await response.json()).tasks||[];
  const task=rows.find(item=>item.id===id);
  if(!task)return;
  activeId=id;lastAgent=task.agent_id||'kiko';lastRenderedAnswer=task.answer||'';
  selectAgentStage(lastAgent);
  paintComputer(task.state==='answered'?'happy':
     task.state==='waiting_for_reply'?'waiting':
     task.state==='rendering_media'?'processing':
     task.state==='running'?'thinking':
     task.state==='failed'?'failed':
     ['queued','cooldown','opening','typing','submitting','researching'].includes(task.state)?'processing':'idle');
  renderMedia(task);
  if(task.state==='answered'&&lastAttentionId!==id){
    lastAttentionId=id;
    const terminal=document.querySelector('.response');
    terminal?.classList.add('response-handoff');
    setTimeout(()=>terminal?.classList.remove('response-handoff'),3700);
  }
  if(task.state==='answered'&&lastSpokenId!==id){
   // Read only tasks completed after this page opened; history is never auto-played.
   if(Date.parse(task.updated_at||0)<EPOCH){lastSpokenId=id;return;}
   lastSpokenId=id;
   voice.setAgent(lastAgent);
   speakCompanion(task.answer,lastAgent);
  }
 }catch(error){voiceStatus('Companion delivery refresh: '+error.message);}
}
setInterval(refreshDelivery,900);
refreshDelivery();

$('#model')?.addEventListener('change',()=>paintComputer(active));
paintComputer('idle');

if($('#ttsEngine'))voiceStatus('Natural neural voices require the optional local Kokoro service (port 8880)');
