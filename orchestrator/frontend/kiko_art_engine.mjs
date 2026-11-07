import {PuppetEngine,solveTwoBone} from './puppet_engine.mjs';
import {paintRegisteredLayers,validateRegistration,ART_RENDER_MODES} from './kiko_layer_runtime.mjs';
/* Exodia Tower A1.3 — source-pixel registered art rig.
 * Art is the approved original, not a substitute AI illustration.
 * Polygon cutouts are *pre-production* masks: missing rear-side paint and expression
 * plates are reported as QC blockers rather than concealed by a rigid sprite motion.
 */

const RAD=Math.PI/180;
const clamp=(x,min,max)=>Math.min(max,Math.max(min,x));
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
    this.layerImages=new Map();this.layerFailures=[];this.artRenderMode='registered';
    const spriteLoads=Object.entries(manifest.layers).filter(([,m])=>m.polygons&&m.src).map(async([name,m])=>{
      const image=new Image();image.src=m.src;
      try{await image.decode();this.layerImages.set(name,image)}
      catch(e){this.layerFailures.push(name)}
    });
    this.loaded=Promise.all([this.art.decode().catch(()=>null),...spriteLoads]);this.elapsed=0;this.reducedMotion=false;this.showBounds=false;
    this.operatorBlink=0;this.target=null;this.activeHand=null;this.speechText='';
    this.eyePhase=0;this.speaking=false;this.handTarget=null;
    this.performance='idle';this.performanceAt=0;this.transparentStage=false;
  }
  setArtRenderMode(mode){if(!ART_RENDER_MODES.includes(mode))throw Error('Unknown art render mode');this.artRenderMode=mode}
  getArtQA(){return validateRegistration(this.manifest,this.layerImages)}
  setPerformance(name){
    if(!ALBEDO_PERFORMANCES.includes(name))throw Error('Unknown Albedo performance');
    this.performance=name;this.performanceAt=this.elapsed;this.release();
    const mapping={
      idle:['neutral','idle'],sleeping:['sleeping','sleep'],processing:['processing','work'],
      waiting:['curious','idle'],thinking:['thinking','idle'],failed:['disappointed','idle'],
      frustration:['annoyed','idle'],happy:['happy','wave'],excited:['excited','wave'],proud:['proud','idle']
    };
    const [emotion,activity]=mapping[name];
    this.driver.setEmotion(emotion);this.driver.setActivity(activity);
  }
  getPerformance(){return this.performance}
  setEmotion(name){this.driver.setEmotion(name)}
  setActivity(name){this.driver.setActivity(name)}
  speak(text){this.speechText=String(text||'');this.driver.speak(this.speechText);this.speaking=Boolean(this.speechText)}
  blink(){this.driver.blink=1;this.operatorBlink=1}
  setReach(side,x,y){if(!['left','right'].includes(side))throw Error('Invalid hand');this.handTarget={side,x,y};}
  release(){this.handTarget=null;}
  moveTo(x,y){this.target={x:clamp(x,-120,120),y:clamp(y,-110,130)};this.driver.setActivity('walk');}
  read(){return {emotion:this.driver.emotion,activity:this.driver.activity,blink:this.driver.blink,viseme:this.driver.viseme,art_layers:Object.keys(this.manifest.layers).length,render_mode:this.artRenderMode,registered:this.getArtQA().ready.length,missing:this.getArtQA().rejected.map(x=>x.name),production_ready:false,source: this.manifest.approved_source.startsWith('data:')?'[embedded source image]':this.manifest.approved_source};}
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
    const phase=Math.max(0,this.elapsed-this.performanceAt);
    const transition=Math.min(1,phase/.32);
    const sway=Math.sin(phase*3),quick=Math.sin(phase*10);
    const perf=this.performance;
    const add=(bone,angle)=>{a[bone]=(a[bone]||0)+angle*transition;};
    switch(perf){
      case 'sleeping':
        add('torso',9);add('head',18+Math.sin(phase*1.5)*1.5);
        add('arm_left_upper',18);add('arm_right_upper',-22);
        add('arm_left_fore',-14);add('arm_right_fore',18);break;
      case 'processing':
        add('head',-7+Math.sin(phase*3)*2);
        add('arm_left_upper',-35+sway*7);add('arm_left_fore',-35+quick*12);
        add('arm_right_upper',25-sway*8);add('arm_right_fore',38-quick*11);break;
      case 'waiting':
        add('head',8+Math.sin(phase*2.2)*4);
        add('arm_right_upper',-24);add('arm_right_fore',-42);
        add('hand_right',Math.sin(phase*2)*7);break;
      case 'thinking':
        add('head',-12+Math.sin(phase*1.8)*3);
        add('arm_right_upper',-47);add('arm_right_fore',-52);
        add('torso',-5);break;
      case 'failed':
        add('torso',15);add('head',22);add('arm_left_upper',19);
        add('arm_right_upper',-18);break;
      case 'frustration':
        add('head',Math.sin(phase*9)*11);add('torso',8);
        add('arm_left_upper',-37+quick*7);add('arm_right_upper',43-quick*7);
        add('arm_left_fore',-30);add('arm_right_fore',30);break;
      case 'happy':
        add('head',-9+sway*5);add('arm_right_upper',-45);
        add('arm_right_fore',-40+quick*18);add('hand_right',quick*14);break;
      case 'excited':
        add('head',Math.sin(phase*8)*8);
        add('arm_left_upper',-65+quick*8);add('arm_right_upper',65-quick*8);
        add('arm_left_fore',-45);add('arm_right_fore',43);
        add('leg_back',Math.sin(phase*9)*9);add('leg_front',-Math.sin(phase*9)*9);break;
      case 'proud':
        add('head',-8);add('torso',-8);
        add('arm_left_upper',-29);add('arm_left_fore',38);
        add('arm_right_upper',35);add('arm_right_fore',-37);break;
    }
    return a;
  }
  _feature(ctx,name,angles){const meta=this.manifest.layers[name];if(!meta)return;
    ctx.save();withTransform(ctx,sourceJoints,'head',angles);
    const [x,y,w,h]=[meta.box[0],meta.box[1],meta.box[2]-meta.box[0],meta.box[3]-meta.box[1]];
    const blink=this.performance==='sleeping' ? 1 :
      clamp(this.driver.blink + this.operatorBlink,0,1);
    if(name.startsWith('eye') && blink>.03){
      const cx=x+w*.5,cy=y+h*.47;
      // Eye occlusion fill is a draft paint-over. Neutral source remains completely unchanged.
      const grad=ctx.createRadialGradient(cx,cy,1,cx,cy, Math.max(w,h)*.58);
      grad.addColorStop(0,'rgba(247,194,193,'+(blink*.94)+')');grad.addColorStop(1,'rgba(247,194,193,0)');
      ctx.fillStyle=grad;ctx.beginPath();ctx.ellipse(cx,cy,w*.47,h*.42,-.2,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle=`rgba(79,49,86,${blink*.92})`;ctx.lineWidth=4;ctx.lineCap='round';
      ctx.beginPath();ctx.moveTo(x+w*.16,cy+h*.03);ctx.quadraticCurveTo(cx,cy-h*.12,x+w*.85,cy-h*.12);ctx.stroke();
    }
    if(name==='mouth'&&(['happy','excited','frustration'].includes(this.performance)||this.driver.activity==='talk')){
      // Viseme proxy: a close/open paint-over using the SOURCE lip color; not accepted lip-sync art.
      const phase=this.performance==='frustration'?(.7+.3*Math.sin(this.elapsed*9)):
        this.performance==='happy'?(.5+.5*Math.sin(this.elapsed*4)):
        (.5+.5*Math.sin(this.elapsed*13));
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
    if(!this.transparentStage){
      const colors=ctx.createLinearGradient(0,0,1122,1402);colors.addColorStop(0,'#10182c');colors.addColorStop(.55,'#151734');colors.addColorStop(1,'#081b30');ctx.fillStyle=colors;ctx.fillRect(0,0,1122,1402);
      ctx.strokeStyle='#68c7ff13';ctx.lineWidth=2;
      for(let x=0;x<1122;x+=78){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,1402);ctx.stroke();}
      for(let y=0;y<1402;y+=78){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1122,y);ctx.stroke();}
    }
    const angles=this._angles();const layers=Object.entries(this.manifest.layers).filter(([,v])=>v.polygons);
    layers.sort((a,b)=>a[1].z-b[1].z);
    // Controlled translation (world roaming preview) is separated from bone articulation.
    const drift=this.target||{x:0,y:0};
    ctx.translate(drift.x,drift.y);
    const phase=Math.max(0,this.elapsed-this.performanceAt);
    const step=Math.min(1,phase/.35);
    if(this.performance==='excited'){
      // Full-body jumps are combined with independently driven arm/leg rotations.
      ctx.translate(0,-Math.abs(Math.sin(phase*5.8))*55*step);
    }else if(this.performance==='failed')ctx.translate(0,Math.min(16,phase*12));
    else if(this.performance==='sleeping')ctx.translate(0,Math.sin(phase*1.2)*4);
    if(this.artRenderMode==='registered'){
      this.lastArtFrame=paintRegisteredLayers(ctx,this.manifest,this.layerImages,angles,
        (c,name,a)=>withTransform(c,sourceJoints,name,a),{showBounds:this.showBounds});
    }else if(this.art.complete&&this.art.naturalWidth){
      for(const [name,data] of layers){
        ctx.save();withTransform(ctx,sourceJoints,name,angles);ctx.beginPath();
        for(const poly of data.polygons){poly.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();}
        ctx.clip();ctx.drawImage(this.art,0,0,1122,1402);
        if(this.showBounds){ctx.lineWidth=2;ctx.strokeStyle='#f9d772';ctx.stroke();}
        ctx.restore();
      }
    }
    for(const name of ['eye_left','eye_right','mouth'])this._feature(ctx,name,angles);
    ctx.restore();
    this.onUpdate?.(this.read());
  }
}

export const ART_JOINTS=sourceJoints;
export const ALBEDO_PERFORMANCES=Object.freeze(['idle','sleeping','processing','waiting','thinking','failed','frustration','happy','excited','proud']);
