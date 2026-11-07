import {DevelopmentPortraitStage} from './development_portrait_stage.mjs';
const manager=new DevelopmentPortraitStage();
if(await manager.initialize()){
 const card=document.getElementById('expressionCard');
 const mood=document.getElementById('moodLabel');
 const companion=document.getElementById('companion');
 if(manager.mount(card)){
  const refresh=()=>manager.setState(mood?.textContent||'idle',companion?.value||'kiko');
  if(mood)new MutationObserver(refresh).observe(mood,{childList:true,characterData:true,subtree:true});
  if(companion)companion.addEventListener('change',refresh);
  window.addEventListener('exodia:companion-signal',event=>manager.setSignal(event.detail||{}));
  window.addEventListener('pagehide',()=>manager.destroy(),{once:true});
  window.__exodiaDevelopmentPortraitStage=manager;
  await refresh();
 }
}
