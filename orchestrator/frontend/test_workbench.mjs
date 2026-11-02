import {PrototypePortraitStateManager,PROTOTYPE_STATES} from './prototype_state_manager.mjs';

const $ = id => document.getElementById(id);
const icons = {idle:'✧',working:'⌘',explaining:'✦',monitoring:'◉',pointing:'➤'};
const descriptions = {idle:'Available for a new mission',working:'Executing tasks at the holographic console',explaining:'Presenting an explanation',monitoring:'Keeping watch over system signals',pointing:'Directing your attention to a target'};
const manager = new PrototypePortraitStateManager({container:$('portraitFrame')});
let selected=0, timer=null, visited=new Set();

function addStates(reg){
  $('stateMenu').replaceChildren();
  PROTOTYPE_STATES.forEach((state,index)=>{
    const item=reg.states[state];
    const button=document.createElement('button');
    button.className='state-button';button.type='button';button.dataset.state=state;
    button.setAttribute('aria-pressed','false');
    button.innerHTML=`<span class="glyph">${icons[state]}</span><span class="detail"><strong>${item.label}</strong><small>${descriptions[state]}</small></span><span class="arrow">›</span>`;
    button.addEventListener('click',()=>go(index));
    $('stateMenu').append(button);
  });
}
function renderState(state){
  const item=manager.registry.states[state];
  document.querySelectorAll('[data-state]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.state===state)));
  $('stateKey').textContent=state.toUpperCase();$('stateTitle').textContent=item.label;
  $('statusLabel').textContent=item.label;$('innerState').textContent=item.activity;
  $('statusText').textContent=item.description;
  $('actionDetails').textContent=state==='pointing'?item.caveat:item.description;
  $('assetHash').textContent=item.sha256.slice(0,15)+'…';
  $('sourceName').textContent=item.original_source;
  $('gestureBeam').hidden=state!=='pointing';
  $('loadStatus').textContent=`Verified preview pixels: ${item.path} · ${item.source_canvas[0]}×${item.source_canvas[1]} original`;
  $('frameCount').textContent=`${visited.size} / 5`;
}
async function go(index){
  selected=(index+PROTOTYPE_STATES.length)%PROTOTYPE_STATES.length;
  const state=PROTOTYPE_STATES[selected];
  try {
    $('loadStatus').textContent=`Checking ${state} asset SHA-256…`;
    const success=await manager.setState(state);
    if(success){visited.add(state);renderState(state);}
  }catch(error){$('loadStatus').textContent=`Preview failed: ${error.message}`;console.error(error);}
}
function autoLoop(){
  if(timer){clearInterval(timer);timer=null;}
  if($('autoCycle').checked) timer=setInterval(()=>go(selected+1),4000);
}
$('autoCycle').addEventListener('change',autoLoop);
$('transitionSpeed').addEventListener('input',e=>{manager.duration=Number(e.target.value);$('speedValue').textContent=manager.duration+' ms';});
$('ambientMotion').addEventListener('change',e=>document.body.classList.toggle('quiet-ambience',!e.target.checked));
$('restart').addEventListener('click',()=>go(0));
$('copyDebug').addEventListener('click',()=>{
  const payload={state:manager.current,asset:manager.registry?.states[manager.current],history:manager.events,
    prototype_only:true,production_release_enabled:false};
  navigator.clipboard?.writeText(JSON.stringify(payload,null,2)).then(()=>$('loadStatus').textContent='Telemetry copied to clipboard').catch(()=>{ $('loadStatus').textContent='Clipboard permission not available'; });
});
document.addEventListener('keydown',e=>{if(e.target?.tagName==='INPUT')return;
  if(e.key==='ArrowRight'){e.preventDefault();go(selected+1);}
  if(e.key==='ArrowLeft'){e.preventDefault();go(selected-1);}
});
function clock(){const d=new Date();$('clock').textContent=d.toLocaleTimeString('en-CA',{hour:'2-digit',minute:'2-digit'});}
clock();setInterval(clock,30000);
try{
  const registry=await manager.initialize();addStates(registry);await go(0);
  // Preload URLs but never set state, so the first click is immediate.
  for(const state of PROTOTYPE_STATES.slice(1))manager.load(state).catch(e=>console.warn(`Unable to preload ${state}:`,e.message));
}catch(error){$('loadStatus').textContent='Workbench initialization failed: '+error.message;console.error(error);}
