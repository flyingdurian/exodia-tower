/** Task-bound, privacy-minimal in-room Albedo behavior reducer.
 * Uses public task metadata only. Never reads provider sessions, prompts, answers,
 * private instructions, cookies or stored authentication state.
 */
import {zoneForTaskState} from './albedo_chibi_controller.mjs';

const PHASES=Object.freeze({
  idle:['idle','Standing by'],draft:['idle','Standing by'],
  queued:['dispatch','Approaching terminal'],opening:['dispatch','Opening model workspace'],
  cooldown:['dispatch','Preparing provider'],
  researching:['processing','Researching at terminal'],typing:['processing','Entering task'],
  submitting:['processing','Submitting task'],running:['processing','Working at terminal'],
  rendering_media:['processing','Rendering task media'],
  waiting_for_reply:['waiting','Awaiting provider reply'],
  awaiting_operator:['waiting','Operator attention required'],
  answered:['success','Response received'],failed:['failure','Task failed'],
  cancelled:['cancelled','Returning home after local cancellation']
});

const saneId=value=>typeof value==='string'&&value.length<=128?value:'';
const parseRevision=value=>{
  if(typeof value!=='string'||!value)return null;
  const stamp=Date.parse(value);
  return Number.isFinite(stamp)?stamp:null;
};

export class AlbedoRoomBehavior {
  constructor(manifest,{selectedAgent='kiko'}={}){
    if(!manifest?.task_zone_mapping)throw Error('Behavior requires approved zone map');
    this.manifest=manifest;
    this.selectedAgent=saneId(selectedAgent)||'kiko';
    this.task={id:'',agentId:this.selectedAgent,state:'idle',updatedAt:null,revision:null};
    this.lastResult=null;
  }
  selectCompanion(id){
    this.selectedAgent=saneId(id)||'kiko';
    return this.snapshot();
  }
  ingest(event){
    // This function is deliberately a narrow projection of the public task event.
    const next={
      id:saneId(event?.taskId),
      agentId:saneId(event?.agentId)||this.selectedAgent,
      state:Object.hasOwn(PHASES,event?.state)?event.state:'idle',
      updatedAt:typeof event?.updatedAt==='string'?event.updatedAt:null,
      revision:parseRevision(event?.updatedAt)
    };
    const previous=this.task;
    // A delayed poll for the *same task* cannot revert a more recent lifecycle
    // state. Task selection changes are intentional and always allowed.
    if(next.id && next.id===previous.id && next.revision!==null &&
       previous.revision!==null && next.revision<previous.revision){
      this.lastResult={...this.snapshot(),accepted:false,stale:true};
      return this.lastResult;
    }
    this.task=next;
    this.lastResult={...this.snapshot(),accepted:true,stale:false};
    return this.lastResult;
  }
  snapshot(){
    const phase=PHASES[this.task.state]||PHASES.idle;
    const enabled=this.selectedAgent==='kiko'&&this.task.agentId==='kiko';
    const zone=zoneForTaskState(this.task.state,this.manifest);
    return Object.freeze({
      taskId:this.task.id,agentId:this.task.agentId,selectedAgent:this.selectedAgent,
      state:this.task.state,behavior:phase[0],cue:phase[1],
      zone,visible:enabled,
      // Local cancellation never implies that a remote provider stopped.
      remoteCancellationConfirmed:false
    });
  }
}
