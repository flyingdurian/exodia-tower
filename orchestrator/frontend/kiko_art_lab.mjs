import {KikoArtEngine} from './kiko_art_engine.mjs';
import {ACTIVITIES} from './puppet_engine.mjs';
const $=s=>document.querySelector(s);let art,last=0,idx=0,tourTimer=0;const tour=['neutral','curious','thinking','processing','happy','excited','wonder','annoyed','angry','disappointed','sad','sleeping','relieved','celebrating'];
function options(el,keys){el.replaceChildren(...keys.map(k=>{const o=document.createElement('option');o.value=k;o.textContent=k.replaceAll('_',' ');return o;}));}
async function boot(){const [visual,rig]=await Promise.all([fetch('/assets/artwork/kiko_prime/manifest.json').then(r=>r.json()),fetch('/assets/rigs/kiko.json').then(r=>r.json())]);
 art=new KikoArtEngine($('#kikoCanvas'),visual,rig);await art.loaded;options($('#emotion'),Object.keys(rig.poses));options($('#activity'),ACTIVITIES);
 $('#emotion').addEventListener('change',e=>art.setEmotion(e.target.value));$('#activity').addEventListener('change',e=>art.setActivity(e.target.value));
 $('#blink').onclick=()=>art.blink();$('#speak').onclick=()=>art.speak('Analyzing. I found an answer. Let me explain!');$('#reach').onclick=()=>{art.setReach('left',345,495);art.setActivity('wave');};
 $('#bounds').onchange=e=>art.showBounds=e.target.checked;$('#pause').onchange=e=>art.reducedMotion=e.target.checked;$('#reference').onchange=e=>{let c=$('#kikoCanvas'),m=$('#master');m.hidden=!e.target.checked;c.hidden=e.target.checked;};
 $('#reset').onclick=()=>{art.target=null;art.release();art.setEmotion('neutral');art.setActivity('idle');$('#emotion').value='neutral';$('#activity').value='idle';};
 $('#tour').onclick=e=>{if(tourTimer){clearInterval(tourTimer);tourTimer=0;e.target.textContent='▶ Expression tour';return;}
  tourTimer=setInterval(()=>{let name=tour[idx++%tour.length];art.setEmotion(name);art.setActivity(name==='sleeping'?'sleep':name==='processing'?'work':name==='celebrating'?'wave':'idle');$('#emotion').value=name;$('#activity').value=art.driver.activity;},1600);e.target.textContent='■ Stop tour';};
 const c=$('#kikoCanvas');const xy=e=>{const r=c.getBoundingClientRect();return {x:(e.clientX-r.left)*c.width/r.width,y:(e.clientY-r.top)*c.height/r.height};};
 c.addEventListener('pointermove',e=>{const p=xy(e);art.driver.lookAt(p.x*.472,p.y*.446);if(e.buttons){art.setReach('left',p.x,p.y);}});
 c.addEventListener('pointerdown',e=>{c.setPointerCapture(e.pointerId);const p=xy(e);art.setReach('left',p.x,p.y)});
 c.addEventListener('pointerup',()=>art.release());c.addEventListener('pointercancel',()=>art.release());
 function frame(t){const dt=Math.min((t-(last||t))/1000,.05);last=t;art.step(dt);$('#state').textContent=`${art.driver.emotion.toUpperCase()} / ${art.driver.activity.toUpperCase()}`;if(Math.round(t/400)%2===0)$('#telemetry').textContent=JSON.stringify(art.read(),null,2);requestAnimationFrame(frame)}requestAnimationFrame(frame);
}
boot().catch(e=>{$('#telemetry').textContent='ART STUDIO ERROR: '+e.message;console.error(e)});