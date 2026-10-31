import {PuppetEngine,solveTwoBone} from './puppet_engine.mjs';
/* Exodia Tower A1.3 — source-pixel registered art rig.
 * Art is the approved original, not a substitute AI illustration.
 * Polygon cutouts are *pre-production* masks: missing rear-side paint and expression
 * plates are reported as QC blockers rather than concealed by a rigid sprite motion.
 */

const RAD=Math.PI/180;
const sourceJoints={
 hips:{at:[623,760]},torso:{at:[590,570],parent:'hips'},
 skirt:{at:[633,694],parent:'hips'},
 hair_back:{at:[503,316],parent:'head'},
 head:{at:[589,478],parent:'torso'},hair_front:{at:[585,310],parent:'head'},
 arm_left_upper:{at:[474,538],parent:'torso'},arm_left_fore:{at:[389,584],parent:'arm_left_upper'},hand_left:{at:[303,608],parent:'arm_left_fore'},
 arm_right_upper:{at:[766,574],parent:'torso'},arm_right_fore:{at:[823,622],parent:'arm_right_upper'},hand_right:{at:[862,658],parent:'arm_right_fore'},
 leg_back:{at:[594,825],parent:'hips'},leg_front:{at:[704,819],parent:'hips'}
};
function withTransform(ctx,joints,id,angles){
  const chain=[];let node=id;
  while(node){chain.unshift(node);node=joints[node]?.parent;}
  for(const part of chain){const [x,y]=joints[part].at;const rotation=(angles[part]||0)*RAD;
    ctx.translate(x,y);ctx.rotate(rotation);ctx.translate(-x,-y);
  }
}
const a2d=(a,b)=>Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI;
export function reachAngles(side,target){
  const p=side==='left'?[[474,538],[389,584],[303,608]]:[[766,574],[823,622],[862,658]];
  const [shoulder,elbow,hand]=p.map(([x,y])=>({x,y}));
  const sol=solveTwoBone(shoulder,target,Math.hypot(elbow.x-shoulder.x,elbow.y-shoulder.y),Math.hypot(hand.x-elbow.x,hand.y-elbow.y),-1);
  const initialA=a2d(p[0],p[1]),initialB=a2d(p[1],p[2]);
  const arm=clamp(sol.first-initialA,-36,36),fore=clamp(sol.second-initialB-arm,-55,55);
  return {arm,fore,reached:sol.reached};
}
export class KikoArtEngine {
  constructor(canvas,manifest,rig){
    if(manifest.agent_id!=='kiko'||!manifest.layers)throw Error('Kiko art manifest required');
    this.canvas=canvas;this.ctx=canvas.getContext('2d');this.manifest=manifest;
    this.driverCanvas=document.createElement('canvas');this.driverCanvas.width=530;this.driverCanvas.height=625;
    this.driver=new PuppetEngine(this.driverCanvas,rig,{debug:false});
    this.art=new Image();this.art.src=manifest.approved_source;
    this.loaded=this.art.decode();this.elapsed=0;this.reducedMotion=false;this.showBounds=false;
    this.operatorBlink=0;this.target=null;this.activeHand=null;this.speechText='';
    this.eyePhase=0;this.speaking=false;this.handTarget=null;
  }
  setEmotion(name){this.driver.setEmotion(name)}
  setActivity(name){this.driver.setActivity(name)}
  speak(text){this.speechText=String(text||'');this.driver.speak(this.speechText);this.speaking=Boolean(this.speechText)}
  blink(){this.driver.blink=1;this.operatorBlink=1}
  setReach(side,x,y){if(!['left','right'].includes(side))throw Error('Invalid hand');this.handTarget={side,x,y};}
  release(){this.handTarget=null;}
  moveTo(x,y){this.target={x:clamp(x,-120,120),y:clamp(y,-110,130)};this.driver.setActivity('walk');}
  read(){return {emotion:this.driver.emotion,activity:this.driver.activity,blink:this.driver.blink,viseme:this.driver.viseme,art_layers:Object.keys(this.manifest.layers).length,source: this.manifest.approved_source.startsWith('data:')?'[embedded source image]':this.manifest.approved_source.startsWith('data:')?'[embedded source image]':this.manifest.approved_source};}
  _angles(){
    const p=this.driver.pose,t=this.elapsed;
    const a={hips:0,torso:clamp((p.torso||0)*.5,-5,5),head:clamp((p.head||0)*.75,-12,12),
      hair_back:Math.sin(t*1.45)*2.5,hair_front:Math.sin(t*1.8)*1.1,
      arm_left_upper:clamp(p.upper_arm_left||0,-22,22),arm_right_upper:clamp(p.upper_arm_right||0,-22,22),
      arm_left_fore:clamp(p.forearm_left||0,-22,22),arm_right_fore:clamp(p.forearm_right||0,-22,22),
      hand_left:Math.sin(t*1.8)*2,hand_right:Math.sin(t*1.8)*2,
      leg_back:clamp((p.thigh_left||0)*.6,-14,14),leg_front:clamp((p.thigh_right||0)*.6,-14,14),
      skirt:Math.sin(t*2.2)*1.8};
    if(this.handTarget){const side=this.handTarget.side;const ik=reachAngles(side,this.handTarget);
      a[`arm_${side}_upper`]=ik.arm;a[`arm_${side}_fore`]=ik.fore;
    }
    return a;
  }
  _feature(ctx,name,angles){const meta=this.manifest.layers[name];if(!meta)return;
    ctx.save();withTransform(ctx,sourceJoints,'head',angles);
    const [x,y,w,h]=[meta.box[0],meta.box[1],meta.box[2]-meta.box[0],meta.box[3]-meta.box[1]];
    const blink=clamp(this.driver.blink + this.operatorBlink,0,1);
    if(name.startsWith('eye') && blink>.03){
      const cx=x+w*.5,cy=y+h*.47;
      // Eye occlusion fill is a draft paint-over. Neutral source remains completely unchanged.
      const grad=ctx.createRadialGradient(cx,cy,1,cx,cy, Math.max(w,h)*.58);
      grad.addColorStop(0,'rgba(247,194,193,'+(blink*.94)+')');grad.addColorStop(1,'rgba(247,194,193,0)');
      ctx.fillStyle=grad;ctx.beginPath();ctx.ellipse(cx,cy,w*.47,h*.42,-.2,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle=`rgba(79,49,86,${blink*.92})`;ctx.lineWidth=4;ctx.lineCap='round';
      ctx.beginPath();ctx.moveTo(x+w*.16,cy+h*.03);ctx.quadraticCurveTo(cx,cy-h*.12,x+w*.85,cy-h*.12);ctx.stroke();
    }
    if(name==='mouth'&&this.driver.activity==='talk'){
      // Viseme proxy: a close/open paint-over using the SOURCE lip color; not accepted lip-sync art.
      const phase=.5+.5*Math.sin(this.elapsed*13);
      ctx.save();ctx.translate(meta.pivot[0],meta.pivot[1]);ctx.globalAlpha=.27+phase*.28;
      ctx.fillStyle='#a25979';ctx.beginPath();ctx.ellipse(0,2,13,3+phase*8,0,0,Math.PI*2);ctx.fill();ctx.restore();
    }
    ctx.restore();
  }
  step(dt){dt=clamp(dt,0,.05);if(!this.reducedMotion){this.elapsed+=dt;this.driver.step(dt);} else this.driver.step(0);
    this.operatorBlink=Math.max(0,this.operatorBlink-dt*5);
    const ctx=this.ctx;ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
    ctx.save();ctx.scale(this.canvas.width/1122,this.canvas.height/1402);
    // Source-space art framing; no replacement / synthetic painted character.
    const colors=ctx.createLinearGradient(0,0,1122,1402);colors.addColorStop(0,'#10182c');colors.addColorStop(.55,'#151734');colors.addColorStop(1,'#081b30');ctx.fillStyle=colors;ctx.fillRect(0,0,1122,1402);
    ctx.strokeStyle='#68c7ff13';ctx.lineWidth=2;
    for(let x=0;x<1122;x+=78){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,1402);ctx.stroke();}
    for(let y=0;y<1402;y+=78){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1122,y);ctx.stroke();}
    const angles=this._angles();const layers=Object.entries(this.manifest.layers).filter(([,v])=>v.polygons);
    layers.sort((a,b)=>a[1].z-b[1].z);
    // Controlled translation (world roaming preview) is separated from bone articulation.
    const drift=this.target||{x:0,y:0};
    ctx.translate(drift.x,drift.y);
    if(this.art.complete&&this.art.naturalWidth){for(const [name,data] of layers){
      ctx.save();withTransform(ctx,sourceJoints,name,angles);ctx.beginPath();
      for(const poly of data.polygons){poly.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();}
      ctx.clip();ctx.drawImage(this.art,0,0,1122,1402);
      if(this.showBounds){ctx.lineWidth=2;ctx.strokeStyle='#f9d772';ctx.stroke();}
      ctx.restore();
    }}
    for(const name of ['eye_left','eye_right','mouth'])this._feature(ctx,name,angles);
    ctx.restore();
    this.onUpdate?.(this.read());
  }
}

export const ART_JOINTS=sourceJoints;