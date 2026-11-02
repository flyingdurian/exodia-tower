import {PortraitStateManager} from './portrait_state_manager.mjs';
// Runtime is strictly opt-in: a failed audit leaves all existing visuals untouched.
const manager=new PortraitStateManager();
if(await manager.initialize()){
 const card=document.getElementById('expressionCard');
 const mood=document.getElementById('moodLabel');
 const companion=document.getElementById('companion');
 if(manager.mount(card)){
  const refresh=()=>manager.setState(mood?.textContent||'idle',companion?.value||'kiko');
  if(mood)new MutationObserver(refresh).observe(mood,{childList:true,characterData:true,subtree:true});
  if(companion)companion.addEventListener('change',refresh);
  refresh();
 }
}
