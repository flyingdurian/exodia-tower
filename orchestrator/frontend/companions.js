'use strict';
const root = document.querySelector('#app');
const one = s=>document.querySelector(s);
const all = s=>Array.from(document.querySelectorAll(s));
const MODES = Object.freeze(['idle','thinking','working','success','rest','alert']);
const SIGNS = {idle:'☾',thinking:'✧',working:'⚔',success:'✦',rest:'☕',alert:'!'};
let roster=[], agent=null, mood='idle', lastLog=[], filmAllowed=false;
let reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const hero=one('#heroIllustration'), camera=one('#heroCamera'), canvas=one('#particles'), ctx=canvas.getContext('2d',{alpha:true});
let stars=[], lastFrame=0, size={w:1,h:1,dpr:1};
const random=(a,b)=>a+Math.random()*(b-a);
const now=()=>new Intl.DateTimeFormat('en-CA',{hour:'numeric',minute:'2-digit',second:'2-digit'}).format(new Date());
function makeStars(){stars=Array.from({length:65},()=>({x:Math.random(),y:Math.random(),r:random(.4,2.1),vy:random(.018,.075),vx:random(-.016,.016),phase:random(0,7),pulse:random(.5,2)}));}
function resize(){const rect=canvas.getBoundingClientRect();size={w:rect.width||1,h:rect.height||1,dpr:Math.min(devicePixelRatio||1,2)};canvas.width=Math.round(size.w*size.dpr);canvas.height=Math.round(size.h*size.dpr);ctx.setTransform(size.dpr,0,0,size.dpr,0,0);}
function colorToRGBA(hex,alpha){const h=hex.replace('#','');const z=parseInt(h,16);return `rgba(${(z>>16)&255},${(z>>8)&255},${z&255},${alpha})`;}
function particles(t){if(document.hidden){lastFrame=0;requestAnimationFrame(particles);return;}
 const dt=Math.min((t-(lastFrame||t))/1000,.05);lastFrame=t;
 ctx.clearRect(0,0,size.w,size.h); const speed=({idle:.85,thinking:1.5,working:2.7,success:2.3,rest:.35,alert:3})[mood];
 const c=agent?.accent||'#75b6ff';
 for(let i=0;i<stars.length;i++){
  const p=stars[i]; if(!reduced){p.y-=p.vy*dt*speed;p.x+=p.vx*dt*speed;if(p.y<-.015){p.y=1.015;p.x=Math.random()}if(p.x>1.02)p.x=-.02;if(p.x<-.02)p.x=1.02;}
  const x=p.x*size.w,y=p.y*size.h;
  const a=reduced?.5:(.24+.44*(.5+.5*Math.sin(t*.0017*p.pulse+p.phase)));
  ctx.fillStyle=colorToRGBA(i%5===0?'#fff4d5':c,a);
  ctx.shadowColor=c;ctx.shadowBlur=i%5===0?11:5;
  ctx.beginPath();ctx.arc(x,y,p.r*(mood==='success'?1.5:1),0,Math.PI*2);ctx.fill();
 }
 ctx.shadowBlur=0;
 if(!reduced&&(mood==='working'||mood==='alert'||mood==='thinking')){
  const y=size.h*(.52+.025*Math.sin(t*.0017));const sweep=(t*.0003*speed)%1;
  ctx.strokeStyle=colorToRGBA(c,mood==='alert'?.8:.4);ctx.lineWidth=1.3;
  ctx.beginPath();ctx.ellipse(size.w*.5,y,size.w*(.19+.16*sweep),size.h*(.06+.02*sweep),-.12,0,Math.PI*2);ctx.stroke();
 }
 requestAnimationFrame(particles);
}
function say(message){lastLog.unshift(`${now()} · ${message}`);lastLog=lastLog.slice(0,5);one('#agentLog').replaceChildren(...lastLog.map(text=>{const p=document.createElement('p');p.textContent=text;return p;}));}
function updateControls(){all('[data-mood]').forEach(b=>{b.classList.toggle('active',b.dataset.mood===mood);b.setAttribute('aria-pressed',String(b.dataset.mood===mood))});}
function displayClip(){const video=one('#heroVideo'), img=one('#heroArt');const src=agent?.clips?.[mood];video.pause();video.removeAttribute('src');video.load();if(src&&filmAllowed&&!reduced){video.src=src;video.hidden=false;img.hidden=true;video.play().catch(()=>{video.hidden=true;img.hidden=false;});}else{video.hidden=true;img.hidden=false;}}
function setMood(next,{log=true,persist=false}={}){if(!MODES.includes(next)||!agent)return;mood=next;root.dataset.mood=next;one('#stateIndicator').textContent=next.toUpperCase();one('#moodEmblem').textContent=SIGNS[next];one('#agentLine').textContent=agent.lines[next]||`${agent.name}: ${next} (rig pending)`;updateControls();displayClip();if(log)say(`${agent.name} → ${next.toUpperCase()} (preview${persist?' + local event':''})`);
 if(persist)fetch(`/api/companions/${encodeURIComponent(agent.id)}/react`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:next})}).catch(()=>{});
}
function selectAgent(next,{log=true}={}){const item=roster.find(a=>a.id===next);if(!item)return;agent=item;root.dataset.hero=item.id;root.style.setProperty('--accent',item.accent);root.style.setProperty('--secondary',item.secondary);
 if(item.portrait){one('#heroArt').src=item.portrait;one('#heroArt').hidden=false;}else{one('#heroArt').removeAttribute('src');one('#heroArt').hidden=true;}one('#heroArt').alt=`${item.name} — ${item.title} companion illustration`;one('#heroName').textContent=item.name;one('#heroPillar').textContent=`${item.pillar} · ${item.agent_class}`;one('#agentClass').textContent=item.title.toUpperCase();one('#identityTitle').textContent=item.pillar;one('#identityClass').textContent=`${item.agent_class} · ${item.title}`;one('#personaLine').textContent=item.persona;one('#folio').textContent=String(roster.indexOf(item)+1).padStart(2,'0');one('#identityMark').textContent=({Guardian:'♜',Vanguard:'⚔',Scholar:'✧',Archivist:'◈',Artificer:'⚙',Scout:'☽',Support:'☕',Tactician:'✥'})[item.agent_class]||'✦';
 all('.roster-card').forEach(btn=>{const active=btn.dataset.agent===item.id;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',String(active))});
 setMood('idle',{log:false});if(log)say(`Now visiting ${item.name} · ${item.agent_class}`);
}
function buildRoster(){const holder=one('#roster');holder.replaceChildren();for(const a of roster){const btn=document.createElement('button');btn.type='button';btn.className='roster-card';btn.dataset.agent=a.id;btn.style.setProperty('--card-color',a.accent);btn.setAttribute('aria-label',`${a.name}, ${a.agent_class}`);
 const img=document.createElement('img');if(a.thumbnail){img.src=a.thumbnail;}else{img.hidden=true;}img.alt='';img.loading=a.id==='kiko'?'eager':'lazy';
 const dot=document.createElement('i');dot.className='roster-active';const info=document.createElement('span');info.className='roster-info';const b=document.createElement('b');b.textContent=a.name;const sm=document.createElement('small');sm.textContent=a.agent_class;info.append(b,sm);btn.append(img,dot,info);btn.addEventListener('click',()=>selectAgent(a.id));holder.append(btn);}}
function connect(){const url=(location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/ws/events';let ws;try{ws=new WebSocket(url);}catch{return;}
 ws.onopen=()=>{one('#backendStatus').textContent='LOCAL ENGINE LINKED';one('.live-dot').classList.add('linked')};
 ws.onmessage=e=>{try{const event=JSON.parse(e.data);if(event.kind==='companion'&&event.detail){const [id,state]=event.detail.split(':');if(agent?.id===id&&MODES.includes(state)){setMood(state,{log:false});say(`ENGINE EVENT · ${agent.name}: ${state}`)}}}catch{}};
 ws.onclose=()=>{one('#backendStatus').textContent='PREVIEW ONLY · OFFLINE';one('.live-dot').classList.remove('linked');setTimeout(connect,3500)};
}
async function boot(){try{const r=await fetch('/api/companions');if(r.ok){const body=await r.json();roster=body.agents;filmAllowed=true;}}catch{}
 if(!roster.length){const r=await fetch('/assets/companions/roster.json');roster=await r.json();one('#backendStatus').textContent='PORTRAIT PREVIEW'}
 buildRoster();selectAgent('kiko',{log:false});say('Nine companions loaded · interactive portrait preview');
 for(const b of all('[data-mood]'))b.addEventListener('click',()=>setMood(b.dataset.mood,{persist:true}));
 one('#surprise').addEventListener('click',()=>{const items=roster.filter(a=>a.id!==agent.id);const next=items[Math.floor(Math.random()*items.length)];selectAgent(next.id);setMood(MODES[1+Math.floor(Math.random()*(MODES.length-1))]);});
 one('#reduceMotion').addEventListener('click',()=>{reduced=!reduced;root.classList.toggle('motion-off',reduced);one('#reduceMotion').textContent=reduced?'Motion off':'Motion on';one('#reduceMotion').setAttribute('aria-pressed',String(reduced));displayClip();});
 if(reduced){root.classList.add('motion-off');one('#reduceMotion').textContent='Motion off';}
 window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA'].includes(e.target?.tagName))return;const index=roster.indexOf(agent);if(e.key==='ArrowRight')selectAgent(roster[(index+1)%roster.length].id);if(e.key==='ArrowLeft')selectAgent(roster[(index+roster.length-1)%roster.length].id);if(/^[1-6]$/.test(e.key))setMood(MODES[Number(e.key)-1],{persist:true});});
 hero.addEventListener('pointermove',ev=>{if(reduced)return;const b=hero.getBoundingClientRect(),x=(ev.clientX-b.left)/b.width-.5,y=(ev.clientY-b.top)/b.height-.5;camera.style.setProperty('--px',`${-x*19}px`);camera.style.setProperty('--py',`${-y*14}px`);});
 hero.addEventListener('pointerleave',()=>{camera.style.setProperty('--px','0px');camera.style.setProperty('--py','0px');});
 new ResizeObserver(resize).observe(canvas);resize();makeStars();requestAnimationFrame(particles);connect();
}
boot().catch(e=>{one('#backendStatus').textContent='FAILED TO LOAD PORTRAITS';console.error(e)});
