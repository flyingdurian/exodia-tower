import {FootPlantPlanner} from './foot_plant.mjs';
/* Exodia Tower A1.1. Articulated sprite controller. Missing parts render a diagnostic skeleton,
 * never a fake "animated" static portrait. Requires separately painted transparent sprite layers. */
export const ACTIVITIES=['idle','walk','work','wave','talk','sleep'];
export const REQUIRED_LAYERS=['hips','torso','head','hair_back','hair_front','upper_arm_left','forearm_left','hand_left','upper_arm_right','forearm_right','hand_right','thigh_left','shin_left','foot_left','thigh_right','shin_right','foot_right','eye_left','eye_right','mouth'];
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x)),rad=x=>x*Math.PI/180,deg=x=>x*180/Math.PI;
export const shortestAngle=(a,b)=>((b-a+540)%360)-180;
export function solveTwoBone(p,target,l1,l2,side=1){
 if(!(l1>0&&l2>0))throw Error('Positive bone lengths required');
 const dx=target.x-p.x,dy=target.y-p.y,dist=Math.hypot(dx,dy);
 const d=clamp(dist,Math.abs(l1-l2)+.0001,l1+l2-.0001),direction=Math.atan2(dy,dx);
 const a=Math.acos(clamp((l1*l1+d*d-l2*l2)/(2*l1*d),-1,1));
 const theta=direction+a*side,elbow={x:p.x+Math.cos(theta)*l1,y:p.y+Math.sin(theta)*l1};
 return {elbow,first:deg(theta),second:deg(Math.atan2(target.y-elbow.y,target.x-elbow.x)),reached:dist<=l1+l2};
}
export function validateVisualManifest(visual,bones){
 if(!visual||typeof visual!=='object')throw Error('Missing visual manifest');
 const out={loaded:0,missing:[],invalid:[]};
 for(const bone of REQUIRED_LAYERS){
  const item=visual.layers?.[bone];
  if(!item)out.missing.push(bone);
  else if(!bones[bone]||!item.src||!Array.isArray(item.origin)||item.origin.length!==2||!item.origin.every(Number.isFinite))out.invalid.push(bone);
  else out.loaded++;
 }
 return {...out,complete:out.missing.length===0&&out.invalid.length===0};
}
export class PuppetEngine{
 constructor(canvas,manifest,{debug=true,reducedMotion=false}={}){
  if(!canvas?.getContext)throw Error('Canvas required');
  this.canvas=canvas;this.ctx=canvas.getContext('2d');this.manifest=manifest;this.debug=debug;this.reducedMotion=reducedMotion;
  this.pose={};this.world={};this.emotion='neutral';this.activity='idle';this.elapsed=0;
  this.sprites=new Map();this.spriteDefs={};this.position={x:canvas.width/2,y:canvas.height*.57};
  this.destination=null;this.gaze={x:canvas.width/2,y:160};this.leftHandTarget=null;this.rightHandTarget=null;
  this.blink=0;this.nextBlink=3.2;this.viseme='rest';this.talking=false;this.voiceText='';this.speechProgress=0;
  this.hair={front:0,back:0,frontV:0,backV:0};this.gait=new FootPlantPlanner();this.gaitDirection={x:1,y:0};
  this.children={};for(const [k,v] of Object.entries(manifest.bones))if(v.parent)(this.children[v.parent]??=[]).push(k);
 }
 setEmotion(e){if(!(e in this.manifest.poses))throw Error('Unsupported emotion');this.emotion=e}
 setActivity(a){if(!ACTIVITIES.includes(a))throw Error('Unknown activity');this.activity=a;if(a!=='talk'){this.talking=false;this.viseme='rest'}}
 moveTo(x,y){this.destination={x:clamp(x,80,this.canvas.width-80),y:clamp(y,120,this.canvas.height-90)};const dx=this.destination.x-this.position.x,dy=this.destination.y-this.position.y,d=Math.hypot(dx,dy)||1;this.gaitDirection={x:dx/d,y:dy/d};this.activity='walk'}
 lookAt(x,y){this.gaze={x,y}}
 reach(hand,x,y){if(!['left','right'].includes(hand))throw Error('Invalid hand');this[hand==='left'?'leftHandTarget':'rightHandTarget']={x,y}}
 releaseHands(){this.leftHandTarget=null;this.rightHandTarget=null}
 speak(text){this.voiceText=String(text||'');this.speechProgress=0;this.talking=Boolean(text);this.activity=this.talking?'talk':'idle'}
 setViseme(v){if(!['rest','A','E','I','O','U','M','F'].includes(v))throw Error('Invalid viseme');this.viseme=v}
 attachLayer(bone,img,origin=[0,0],scale=1){
  if(!this.manifest.bones[bone]||!origin.every(Number.isFinite)||!(scale>0))throw Error('Invalid art registration');
  this.sprites.set(bone,img);this.spriteDefs[bone]={src:'operator-import',origin,scale};
 }
 async loadLayers(visual){
  const check=validateVisualManifest(visual,this.manifest.bones);this.spriteDefs={...visual.layers};this.sprites.clear();
  await Promise.all(Object.entries(this.spriteDefs).filter(([,v])=>v?.src).map(async([name,v])=>{
   const img=new Image();img.src=v.src;try{await img.decode();this.sprites.set(name,img)}catch{check.invalid.push(name)}
  }));
  return {...check,decoded:this.sprites.size};
 }
 getCapture(){return {position:{...this.position},pose:{...this.pose},emotion:this.emotion,activity:this.activity,blink:this.blink,viseme:this.viseme}}
 update(dt){
  const t=this.elapsed,base=this.manifest.poses[this.emotion]||{},goal={...base};
  const gait=Math.sin(t*2*Math.PI/.74),breathe=Math.sin(t*2*Math.PI/3.1);
  switch(this.activity){
   case 'walk':goal.thigh_left=(base.thigh_left||0)+gait*24;goal.thigh_right=(base.thigh_right||0)-gait*24;
    goal.shin_left=Math.max(0,-gait)*31;goal.shin_right=Math.max(0,gait)*31;
    goal.upper_arm_left=(base.upper_arm_left||0)-gait*19;goal.upper_arm_right=(base.upper_arm_right||0)+gait*19;
    goal.torso=(base.torso||0)+Math.sin(t*4*Math.PI/.74)*2;break;
   case 'wave':goal.upper_arm_right=-112;goal.forearm_right=-35+Math.sin(t*12)*24;goal.head=-5+Math.sin(t*3)*3;break;
   case 'work':goal.upper_arm_left=-55+Math.sin(t*7)*6;goal.forearm_left=-47+Math.sin(t*9)*9;goal.upper_arm_right=45;goal.forearm_right=50+Math.cos(t*7)*8;break;
   case 'talk':goal.forearm_right=-38+Math.sin(t*6)*15;goal.upper_arm_right=-40;goal.head=-6+Math.sin(t*3)*3;break;
   case 'sleep':goal.head=35;goal.torso=18;goal.upper_arm_left=18;goal.upper_arm_right=-18;break;
   default:goal.torso=(base.torso||0)+breathe*1.5;goal.head=(base.head||0)-breathe*.8;
  }
  const blend=1-Math.exp(-dt*10);
  for(const name of Object.keys(this.manifest.bones))this.pose[name]=(this.pose[name]||0)+shortestAngle(this.pose[name]||0,goal[name]||0)*blend;
  if(this.destination){
   const dx=this.destination.x-this.position.x,dy=this.destination.y-this.position.y,d=Math.hypot(dx,dy),s=80*dt;
   if(d<=Math.max(1.5,s)){this.position={...this.destination};this.destination=null;this.activity='idle'}
   else{this.position.x+=dx/d*s;this.position.y+=dy/d*s}
  }
  this.blink=Math.max(0,this.blink-dt*8);
  if(t>this.nextBlink){this.blink=1;this.nextBlink=t+3.1+(Math.sin(t*7)+1)*1.15}
  if(this.activity==='sleep')this.blink=1;
  if(this.talking){
   const i=Math.floor(this.speechProgress+=dt*8.5),c=(this.voiceText[i]||' ').toLowerCase();
   this.viseme=/[ae]/.test(c)?'A':/[io]/.test(c)?'O':/u/.test(c)?'U':/[mf]/.test(c)?'M':'rest';
   if(i>=this.voiceText.length){this.talking=false;this.activity='idle';this.viseme='rest'}
  }
  for(const k of ['front','back']){
   this.hair[k+'V']+=((-this.pose.head*(k==='front'?.28:.18)-this.hair[k])*28-this.hair[k+'V']*8)*dt;
   this.hair[k]+=this.hair[k+'V']*dt;
  }
 }
 branch(name,x,y,parent){
  const angle=parent+rad(this.pose[name]||0);this.world[name]={x,y,angle};
  for(const child of this.children[name]||[]){
   const [dx,dy]=this.manifest.bones[child].pivot;
   this.branch(child,x+Math.cos(angle)*dx-Math.sin(angle)*dy,y+Math.sin(angle)*dx+Math.cos(angle)*dy,angle);
  }
 }
 ik(side,target){
  const upper=this.world['upper_arm_'+side];if(!upper)return;
  const p1=this.manifest.bones['forearm_'+side].pivot,p2=this.manifest.bones['hand_'+side].pivot;
  const solution=solveTwoBone(upper,target,Math.hypot(...p1),Math.hypot(...p2),side==='left'?1:-1);
  const a=rad(solution.first)-Math.atan2(p1[1],p1[0]),b=rad(solution.second)-Math.atan2(p2[1],p2[0]);
  this.pose['upper_arm_'+side]=deg(a-this.world.torso.angle);
  this.pose['forearm_'+side]=deg(b-a);
  this.branch('upper_arm_'+side,upper.x,upper.y,this.world.torso.angle);
 }
 legIK(side,target){
  const upper=this.world['thigh_'+side];if(!upper)return;
  const p1=this.manifest.bones['shin_'+side].pivot,p2=this.manifest.bones['foot_'+side].pivot;
  const solution=solveTwoBone(upper,target,Math.hypot(...p1),Math.hypot(...p2),side==='left'?-1:1);
  const a=rad(solution.first)-Math.atan2(p1[1],p1[0]);
  const b=rad(solution.second)-Math.atan2(p2[1],p2[0]);
  this.pose['thigh_'+side]=deg(a-this.world.hips.angle);
  this.pose['shin_'+side]=deg(b-a);
  this.branch('thigh_'+side,upper.x,upper.y,this.world.hips.angle);
 }
 draw(){
  const ctx=this.ctx;ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
  const order=['hair_back','thigh_left','thigh_right','shin_left','shin_right','foot_left','foot_right',
   'upper_arm_left','upper_arm_right','forearm_left','forearm_right','hand_left','hand_right','hips','torso','neck',
   'head','eye_left','eye_right','mouth','hair_front'];
  for(const bone of order){
   const j=this.world[bone],im=this.sprites.get(bone),def=this.spriteDefs[bone];if(!j||!im||!def)continue;
   ctx.save();ctx.translate(j.x,j.y);
   ctx.rotate(j.angle+(bone==='hair_front'?rad(this.hair.front):bone==='hair_back'?rad(this.hair.back):0));
   ctx.scale(def.scale||1,def.scale||1);ctx.drawImage(im,-def.origin[0],-def.origin[1]);ctx.restore();
  }
  for(const side of ['left','right']){
   const k='eye_'+side,j=this.world[k],img=this.sprites.get(k+'_closed'),def=this.spriteDefs[k];
   if(j&&img&&def){ctx.save();ctx.translate(j.x,j.y);ctx.rotate(j.angle);ctx.globalAlpha=this.blink;ctx.drawImage(img,-def.origin[0],-def.origin[1]);ctx.restore()}
  }
  const m=this.world.mouth,vis=this.sprites.get('mouth_'+this.viseme);
  if(m&&vis){const def=this.spriteDefs.mouth;ctx.save();ctx.translate(m.x,m.y);ctx.rotate(m.angle);ctx.drawImage(vis,-def.origin[0],-def.origin[1]);ctx.restore()}
  if(this.debug){
   ctx.lineWidth=1.5;ctx.strokeStyle='rgba(124,232,254,.65)';ctx.fillStyle='#8fe5fa';
   for(const [name,j] of Object.entries(this.world)){
    const parent=this.manifest.bones[name].parent;
    if(parent){const p=this.world[parent];ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(j.x,j.y);ctx.stroke()}
    ctx.beginPath();ctx.arc(j.x,j.y,2.5,0,2*Math.PI);ctx.fill();
   }
   if(this.sprites.size===0){const h=this.world.head;if(h){ctx.save();ctx.translate(h.x,h.y);ctx.rotate(h.angle);
    ctx.beginPath();ctx.ellipse(0,-13,29,28,0,0,2*Math.PI);ctx.stroke();
    const gx=clamp((this.gaze.x-h.x)/120,-3,3),gy=clamp((this.gaze.y-h.y)/120,-3,3);
    for(const ex of [-10,10]){ctx.beginPath();ctx.ellipse(ex+gx,-18+gy,4,this.blink>.2?1:6,0,0,2*Math.PI);ctx.fill()}
    ctx.beginPath();ctx.ellipse(0,-3,4,this.activity==='talk'?Math.abs(Math.sin(this.elapsed*16))*7+1:2,0,0,2*Math.PI);ctx.fill();ctx.restore()}}
  }
 }
 step(dt){
  if(!this.reducedMotion){dt=clamp(dt,0,.05);this.elapsed+=dt;this.update(dt)}
  this.world={};this.branch('root',this.position.x,this.position.y,0);
  const feet=this.gait.update(dt,this.position,this.activity==='walk',this.gaitDirection);
  if(this.activity==='walk'){for(const side of ['left','right'])this.legIK(side,feet[side]);}
  if(this.leftHandTarget)this.ik('left',this.leftHandTarget);
  if(this.rightHandTarget)this.ik('right',this.rightHandTarget);
  this.draw();
 }
}