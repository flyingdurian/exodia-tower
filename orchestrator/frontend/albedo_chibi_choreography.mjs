/** Deterministic, ground-registered micro-choreography.
 * Heading-only idle beats, NEVER invented animation frames or visual artwork.
 * Distance-driven walk remains owned exclusively by AlbedoChibiController.
 */
import {DIRECTIONS} from './albedo_chibi_controller.mjs';
const PRESETS=Object.freeze({
  idle:{label:'Standing by',dwell:2.6,heads:['s','sw','s','se','s']},
  dispatch:{label:'Approaching workstation',dwell:1.9,heads:['s','se','e','ne']},
  processing:{label:'Monitoring task',dwell:2.25,heads:['ne','n','ne','e','ne']},
  waiting:{label:'Awaiting response',dwell:2.45,heads:['nw','n','ne','n']},
  success:{label:'Response received',dwell:1.1,heads:['s','se','s','sw','s']},
  failure:{label:'Operator attention',dwell:1.7,heads:['s','sw','w','sw','s']},
  cancelled:{label:'Returning to standby',dwell:2.1,heads:['s','sw','s']}
});
export const CHIBI_BEHAVIORS=Object.freeze(Object.keys(PRESETS));
export function choreographyBeat(behavior,index=0){
  if(!Object.hasOwn(PRESETS,behavior)||!Number.isInteger(index)||index<0)
    throw Error('Invalid chibi behavior beat');
  const p=PRESETS[behavior],i=index%p.heads.length;
  const heading=p.heads[i];
  if(!DIRECTIONS.includes(heading))throw Error('Unregistered heading');
  return Object.freeze({behavior,heading,beat:i,label:p.label,dwell:p.dwell});
}
export class IdleChoreography{
  constructor(initial='idle'){
    if(!Object.hasOwn(PRESETS,initial))throw Error('Unsupported idle choreography');
    this.behavior=initial;this.elapsed=0;this.beat=0;this.paused=false;
    this.steps=0;
  }
  setBehavior(value){
    const next=Object.hasOwn(PRESETS,value)?value:'idle';
    if(this.behavior!==next){
      this.behavior=next;this.elapsed=0;this.beat=0;this.steps++;
    }
    return this.snapshot();
  }
  pause(pause=true){this.paused=!!pause;return this.snapshot();}
  reset(){this.elapsed=0;this.beat=0;return this.snapshot();}
  /** Tick time is bounded to prevent background-tab or RAF suspension leaps. */
  tick(seconds,{idle=true,motion=true}={}){
    if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<0)
      throw RangeError('Invalid choreography frame');
    if(this.paused||!idle||!motion)return this.snapshot();
    this.elapsed+=Math.min(.125,seconds);
    const setting=PRESETS[this.behavior];
    if(this.elapsed>=setting.dwell){
      this.elapsed-=setting.dwell;
      this.beat=(this.beat+1)%setting.heads.length;this.steps++;
    }
    return this.snapshot();
  }
  snapshot(){
    return Object.freeze({
      ...choreographyBeat(this.behavior,this.beat),
      elapsed:this.elapsed,paused:this.paused,steps:this.steps,
      source:'technical_headings_only',
      artReleased:false
    });
  }
}
export function routeCoordinates(snapshot,waypoints){
  if(!snapshot||!Number.isFinite(snapshot.x)||!Number.isFinite(snapshot.y)||
     !Array.isArray(waypoints)||waypoints.length>50)
    throw Error('Invalid path preview');
  const points=[{x:snapshot.x,y:snapshot.y},...waypoints];
  if(points.some(p=>!Number.isFinite(p.x)||!Number.isFinite(p.y)||
    p.x<0||p.x>1||p.y<0||p.y>1))throw Error('Non-finite floor point');
  return Object.freeze({
    path:points.length<=1?'':points.map((p,i)=>
      (i===0?'M':'L')+(p.x*1000).toFixed(1)+' '+(p.y*1000).toFixed(1)).join(' '),
    count:Math.max(0,points.length-1),
    target:points.at(-1)
  });
}
