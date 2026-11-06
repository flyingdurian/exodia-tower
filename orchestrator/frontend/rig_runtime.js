"use strict";
// Developer diagnostic only. This animates independent skeletal joints;
// it does not falsely present flattened images as articulated characters.
const $=s=>document.querySelector(s),canvas=$("#rigCanvas"),ctx=canvas.getContext("2d");
const names=["kiko","liu_bei","memory","archives","inventory","vault","ninja","cache","strategy","nova"];
const emotions=["neutral","happy","excited","proud","curious","wonder","thinking","processing","concentrating","working","speaking","annoyed","angry","disappointed","sad","hurt","pain","alarmed","panic","bored","sleepy","sleeping","relieved","celebrating"];
const length={hips:20,torso:36,neck:8,head:36,upper_arm_left:27,upper_arm_right:27,forearm_left:23,forearm_right:23,hand_left:11,hand_right:11,thigh_left:37,thigh_right:37,shin_left:31,shin_right:31,foot_left:12,foot_right:12};
let rig=null,t=0,last=0;
const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
async function load(name){
  const response=await fetch("/assets/rigs/"+encodeURIComponent(name)+".json");
  if(!response.ok)throw Error("Missing rig metadata");
  rig=await response.json();
  $("#readout").textContent=rig.name+" · "+rig.status;
  $("#assetStatus").textContent=rig.production_ready?"Sprite layers registered":"22 independent joints / 24 poses. Production layers pending.";
  $("#reference").hidden=!rig.reference;
  if(rig.reference)$("#reference").src=rig.reference;
  t=0;
}
function angles(seconds){
  const base=rig.poses[$("#emotion").value]||{},pose={...base},mode=$("#activity").value;
  const cyc=seconds*2*Math.PI/.72;
  if(mode==="walk"){
    const step=Math.sin(cyc)*24;
    pose.thigh_left=(base.thigh_left||0)+step;
    pose.thigh_right=(base.thigh_right||0)-step;
    pose.shin_left=25*Math.max(0,-Math.sin(cyc));
    pose.shin_right=25*Math.max(0,Math.sin(cyc));
    pose.upper_arm_left=(base.upper_arm_left||0)-step*.65;
    pose.upper_arm_right=(base.upper_arm_right||0)+step*.65;
  }else if(mode==="talk"){
    pose.head=(base.head||0)+Math.sin(seconds*3)*2;
    pose.forearm_right=(base.forearm_right||0)+Math.sin(seconds*4)*8;
  }else if(mode==="work"){
    pose.upper_arm_left=(base.upper_arm_left||0)+Math.sin(seconds*4)*9;
    pose.forearm_left=(base.forearm_left||0)+Math.cos(seconds*4)*9;
  }else pose.torso=(base.torso||0)+Math.sin(seconds*2*Math.PI/3.2)*1.5;
  return pose;
}
function draw(ms){
  const dt=Math.min((ms-(last||ms))/1000,.05);last=ms;
  if(!reduced)t+=dt*Number($("#speed").value);
  ctx.clearRect(0,0,480,650);
  if(rig){
    const pose=angles(t),world={};
    function visit(name,x,y,rot){
      const theta=rot+(pose[name]||0)*Math.PI/180;
      world[name]=[x,y,theta];
      if(length[name]){
        ctx.beginPath();ctx.moveTo(x,y);
        ctx.lineTo(x+Math.sin(theta)*length[name],y+Math.cos(theta)*length[name]);
        ctx.lineWidth=/thigh|torso/.test(name)?12:/arm|shin/.test(name)?8:4;
        ctx.strokeStyle="#99dff4";ctx.lineCap="round";ctx.stroke();
      }
      ctx.fillStyle="#b8f8ed";ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill();
      for(const [child,data] of Object.entries(rig.bones)){
        if(data.parent!==name)continue;
        const [ox,oy]=data.pivot;
        visit(child,x+ox*Math.cos(theta)-oy*Math.sin(theta),
              y+ox*Math.sin(theta)+oy*Math.cos(theta),theta);
      }
    }
    visit("root",240,385,0);
    const [x,y]=world.head;
    ctx.beginPath();ctx.arc(x,y-14,32,0,Math.PI*2);ctx.lineWidth=2;ctx.strokeStyle="#e2f8ff";ctx.stroke();
    const blink=Math.sin(t*.45)>.996;
    ctx.fillStyle="#a0ffef";
    for(const dx of [-12,12]){
      ctx.beginPath();ctx.ellipse(x+dx,y-19,5,blink?1:7,0,0,Math.PI*2);ctx.fill();
    }
    ctx.fillStyle="#f5bad6";ctx.beginPath();
    const h=$("#activity").value==="talk"?Math.abs(Math.sin(t*12))*9:2.5;
    ctx.ellipse(x,y-4,5,h,0,0,Math.PI*2);ctx.fill();
  }
  requestAnimationFrame(draw);
}
async function init(){
  for(const name of names){
    const option=document.createElement("option");option.value=name;option.textContent=name.toUpperCase();
    $("#agent").append(option);
  }
  for(const e of emotions){
    const option=document.createElement("option");option.value=e;option.textContent=e;
    $("#emotion").append(option);
  }
  $("#agent").addEventListener("change",()=>load($("#agent").value));
  await load("kiko");requestAnimationFrame(draw);
}
init().catch(e=>$("#readout").textContent=e.message);
