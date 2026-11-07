/* Frontshell focus and live readout. Presentation only; no API writes. */
import {presentPublicTask} from './frontshell_signal.mjs';

const shell=document.querySelector('.app-shell');
const toggle=document.getElementById('frontshellFocusToggle');
const signal=document.getElementById('frontshellLiveSignal');
function setFocus(yes){
  if(!shell||!toggle)return;
  shell.dataset.frontshellFocus=String(yes);
  toggle.setAttribute('aria-pressed',String(yes));
  toggle.textContent=yes?'Show full command room':'Focus operations floor';
}
toggle?.addEventListener('click',()=>setFocus(shell?.dataset.frontshellFocus!=='true'));
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&shell?.dataset.frontshellFocus==='true')setFocus(false);
});
function renderSignal(detail){
  const publicState=presentPublicTask(detail);
  if(!signal)return publicState;
  signal.dataset.phase=publicState.phase;
  signal.textContent=publicState.title;
  // Never display prompt, private instructions, provider cookies or answer text.
  return publicState;
}
window.addEventListener('exodia:command-task',event=>renderSignal(event.detail));
renderSignal(window.__exodiaLastPublicTaskState||{state:'idle',agentId:'kiko'});
