/** EXODIA Albedo Operations sprite: deterministic movement logic, no DOM/provider code. */
export const DIRECTIONS=Object.freeze(['n','ne','e','se','s','sw','w','nw']);
export const ACTIVE_TASK_STATES=new Set(['queued','opening','researching','typing','submitting','running','rendering_media','waiting_for_reply','awaiting_operator']);
const MODES=Object.freeze(['idle','walk']);
const bounded=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const safeIdentifier=name=>/^[a-z0-9_-]+$/.test(name);
const validHash=hash=>typeof hash==='string'&&/^[0-9a-f]{64}$/.test(hash);

export function headingFromVector(dx,dy,last='s') {
  if(!finite(dx)||!finite(dy))throw new TypeError('Heading requires finite vector');
  if(Math.hypot(dx,dy)<1e-9)return last;
  // Screen coordinates grow downward; index zero is north (up).
  const angle=(Math.atan2(dx,-dy)*180/Math.PI+360)%360;
  return DIRECTIONS[Math.round(angle/45)%8];
}

export function validateChibiManifest(m){
  if(!m||m.schema!=='exodia.albedo-chibi/v1'||m.character_id!=='kiko'||m.production_release_enabled!==false)throw Error('Chibi manifest identity or release gate invalid');
  if(JSON.stringify(m.directions)!==JSON.stringify(DIRECTIONS)||m.frame_size_px?.width!==192||m.frame_size_px?.height!==256)throw Error('Chibi 8-way directions / canvas contract invalid');
  if(m.states?.idle?.frames_per_direction!==1||m.states?.walk?.frames_per_direction!==4||m.states?.walk?.advance_mode!=='distance_registered')throw Error('Chibi 40-frame animation contract invalid');
  for(const pair of [m.anchors?.foot,m.anchors?.shadow])if(!Array.isArray(pair)||pair.length!==2||pair.some(x=>!finite(x)||x<0||x>1))throw Error('Foot/shadow anchor invalid');
  const foot=m.anchors.foot;
  if(Math.abs(foot[0]-.5)>.08||foot[1]<.86)throw Error('Foot registration must remain ground-centered');
  if(!finite(m.anchors?.collision?.radius_normalized)||m.anchors.collision.radius_normalized<=0||m.anchors.collision.floor_only!==true)throw Error('Floor collision contract invalid');
  const b=m.anchors.floor_bounds;
  if(!b||!Array.isArray(b.x)||!Array.isArray(b.y)||b.x.length!==2||b.y.length!==2||!b.x.every(finite)||!b.y.every(finite)||b.x[0]>=b.x[1]||b.y[0]>=b.y[1])throw Error('Floor bounds invalid');
  const t=m.motion;
  if(!t||!finite(t.speed_normalized_per_second)||t.speed_normalized_per_second<=0||!finite(t.max_step_seconds)||t.max_step_seconds<=0||t.max_step_seconds>.1||!finite(t.arrival_epsilon)||t.arrival_epsilon<=0||!finite(t.stride_frame_distance_normalized)||t.stride_frame_distance_normalized<=0)throw Error('Movement parameters invalid');
  if(!m.zones||!['home','terminal','waiting','result','recovery'].every(z=>finite(m.zones[z]?.x)&&finite(m.zones[z]?.y)&&m.zones[z].x>=b.x[0]&&m.zones[z].x<=b.x[1]&&m.zones[z].y>=b.y[0]&&m.zones[z].y<=b.y[1]))throw Error('Floor zones invalid');
  if(!m.task_zone_mapping||Object.values(m.task_zone_mapping).some(zone=>!m.zones[zone]))throw Error('Task-zone contract invalid');
  const names=[];
  for(const d of DIRECTIONS){names.push('idle_'+d);for(let i=0;i<4;i++)names.push(`walk_${d}_${String(i).padStart(2,'0')}`);}
  const expected=Object.keys(m.frames||{});
  if(expected.length!==40||names.some(k=>!Object.hasOwn(m.frames,k)))throw Error('Missing or additional chibi frame (expected 40)');
  const pending=m.asset_status==='pending_production_frames';
  if(!pending&&m.asset_status!=='approved_40_frame_set')throw Error('Unsupported chibi asset status');
  const unique=new Set();
  for(const n of names){
    const f=m.frames[n];if(!f||!safeIdentifier(n))throw Error('Invalid frame ID');
    if(pending){if(f.status!=='pending_independent_art'||f.src!==null||f.sha256!==null||f.approval_sha256!==null||f.source_provenance!==null)throw Error('No partially promoted frames in pending set');}
    else{
      if(f.status!=='owner_approved'||!/^\/assets\/albedo_chibi\/frames\/[a-z0-9_-]+\.png$/.test(f.src||'')||!validHash(f.sha256)||f.approval_sha256!==f.sha256||f.source_provenance?.source_kind!=='independent_standalone')throw Error('Approved frames require independent image SHA and source provenance');
      if(unique.has(f.sha256))throw Error('Cloned chibi frames prohibited');
      unique.add(f.sha256);
    }
  }
  if(pending&&m.source_policy?.development_marker_is_not_art!==true)throw Error('Technical marker must be explicitly non-art');
  return true;
}

export function zoneForTaskState(taskState,manifest){
  return manifest.task_zone_mapping[taskState]||'home';
}

export class AlbedoChibiController {
  constructor(manifest){
    validateChibiManifest(manifest);
    this.manifest=manifest;this.mode='idle';this.heading='s';this.zone='home';
    const z=manifest.zones.home;this.position={x:z.x,y:z.y};
    this.target={...this.position};this.distanceInWalk=0;this.frame=0;
    this.enabled=true;this.arrived=true;this.totalDistance=0;
  }
  setEnabled(on){this.enabled=!!on;if(!on){this.mode='idle';this.frame=0;}else if(!this.arrived)this.mode='walk';return this.snapshot();}
  goToZone(name){
    const z=this.manifest.zones[name];if(!z)throw new RangeError('Unknown chibi floor zone');
    if(name===this.zone)return this.snapshot(); // Polling may repeat the same task state; never reset the walk loop.
    this.zone=name;this.target={x:z.x,y:z.y};
    this.arrived=Math.hypot(this.target.x-this.position.x,this.target.y-this.position.y)<=this.manifest.motion.arrival_epsilon;
    if(!this.arrived&&this.enabled){this.mode='walk';this.frame=0;this.distanceInWalk=0;}
    return this.snapshot();
  }
  dispatchTaskState(state,agentId='kiko'){
    this.setEnabled(agentId==='kiko');
    if(this.enabled)this.goToZone(zoneForTaskState(state,this.manifest));
    return this.snapshot();
  }
  tick(dtSeconds){
    if(!finite(dtSeconds)||dtSeconds<0)throw new RangeError('Invalid elapsed time');
    if(!this.enabled||this.arrived||dtSeconds===0)return this.snapshot();
    const t=this.manifest.motion;
    // Avoid leaps after sleep/tab suspension. A long frame advances only one safe step.
    const dt=Math.min(dtSeconds,t.max_step_seconds);
    const dx=this.target.x-this.position.x,dy=this.target.y-this.position.y;
    const distance=Math.hypot(dx,dy);
    if(distance<=t.arrival_epsilon)return this.finish();
    const step=Math.min(distance,t.speed_normalized_per_second*dt);
    this.heading=headingFromVector(dx,dy,this.heading);
    this.position.x+=dx/distance*step;this.position.y+=dy/distance*step;
    this.position.x=bounded(this.position.x,...this.manifest.anchors.floor_bounds.x);
    this.position.y=bounded(this.position.y,...this.manifest.anchors.floor_bounds.y);
    this.totalDistance+=step;this.distanceInWalk+=step;
    this.mode='walk';
    this.frame=Math.floor(this.distanceInWalk/t.stride_frame_distance_normalized)%4;
    if(distance-step<=t.arrival_epsilon)return this.finish();
    return this.snapshot();
  }
  finish(){this.position={...this.target};this.mode='idle';this.frame=0;this.arrived=true;return this.snapshot();}
  snapshot(){return Object.freeze({mode:this.mode,heading:this.heading,frame:this.frame,zone:this.zone,x:this.position.x,y:this.position.y,arrived:this.arrived,enabled:this.enabled,frame_key:this.mode==='idle'?`idle_${this.heading}`:`walk_${this.heading}_${String(this.frame).padStart(2,'0')}`});}
}
