/** Exodia A1.2: deterministic world-space footsteps for skeletal 2D characters.
 * During stance the planted foot remains fixed as the root moves; during swing
 * it follows a smooth raised arc. Artwork and bone IK remain separate stages. */
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
const smooth=x=>{x=clamp(x,0,1);return x*x*(3-2*x)};
export class FootPlantPlanner{
 constructor({period=.78,stanceFraction=.62,stride=22,lift=12,groundOffset=51}={}){
  if(!(period>0&&stanceFraction>0&&stanceFraction<1&&stride>=0&&lift>=0))throw Error('Invalid gait');
  this.period=period;this.stanceFraction=stanceFraction;this.stride=stride;this.lift=lift;this.groundOffset=groundOffset;
  this.phase=0;this.feet={};this.active=false;
 }
 reset(root){this.phase=0;this.active=false;this.feet={};
  for(const side of ['left','right']){const offset=side==='left'?-13:13;
   this.feet[side]={anchor:{x:root.x+offset,y:root.y+this.groundOffset},swingFrom:null,lastTarget:null,lastStance:false,offset};}
 }
 update(dt,root,moving=true,direction={x:1,y:0}){
  if(!this.feet.left)this.reset(root);
  if(!moving){this.reset(root);return this.targets();}
  if(!this.active){this.active=true;this.phase=.03;}
  else this.phase=(this.phase+clamp(dt,0,.08)/this.period)%1;
  const result={};const dx=clamp(direction.x,-1,1);
  for(const side of ['left','right']){
   const state=this.feet[side];
   const local=(this.phase+(side==='right'?.5:0))%1;
   const stance=local<this.stanceFraction;
   if(stance){
    if(!state.lastStance){
     const landing=state.lastTarget||state.anchor;
     state.anchor={x:landing.x,y:root.y+this.groundOffset};state.swingFrom=null;state.lastTarget=null;
    }
    result[side]={...state.anchor,planted:true};
   }else{
    if(state.lastStance||!state.swingFrom)state.swingFrom={...state.anchor};
    const u=(local-this.stanceFraction)/(1-this.stanceFraction),e=smooth(u);
    const target={x:root.x+state.offset+dx*this.stride,y:root.y+this.groundOffset};
    result[side]={x:state.swingFrom.x+(target.x-state.swingFrom.x)*e,
      y:state.swingFrom.y+(target.y-state.swingFrom.y)*e-Math.sin(Math.PI*u)*this.lift,planted:false};
    state.lastTarget={...result[side]};
   }
   state.lastStance=stance;
  }
  return result;
 }
 targets(){return Object.fromEntries(Object.entries(this.feet).map(([side,s])=>[side,{...s.anchor,planted:true}]));}
}