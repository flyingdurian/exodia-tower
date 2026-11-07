/** Constrained local UI command interpreter. Never executes shell, JS or providers. */
export const COMMANDS=Object.freeze([
  'help','status','providers','tasks','layout','layout reset',
  'focus','clear','open workflows','open companions'
]);
const KEYWORDS=new Set(['help','status','providers','tasks','layout','focus','clear','open']);
const SUBCOMMANDS=new Set(['reset','workflows','companions']);
export function highlightCommand(value){
  if(typeof value!=='string'||value.length>120)return [{kind:'invalid',text:'Invalid input'}];
  const fragments=value.split(/(\s+)/).filter(Boolean);
  return Object.freeze(fragments.map((fragment,index)=>{
    const key=fragment.toLowerCase();
    return Object.freeze({
      kind:/^\s+$/.test(fragment)?'space':
        index===0&&KEYWORDS.has(key)?'keyword':
        SUBCOMMANDS.has(key)?'argument':'unknown',
      text:fragment
    });
  }));
}
export function normalizeCommand(raw){
  if(typeof raw!=='string'||raw.length>120)return null;
  const normalized=raw.trim().replace(/\s+/g,' ').toLowerCase();
  if(!normalized||normalized.length>96)return null;
  return COMMANDS.includes(normalized)?normalized:null;
}
export function runOperatorCommand(raw,{telemetry=null,layout=null}={}){
  const action=normalizeCommand(raw);
  if(!action)return Object.freeze({
    ok:false,action:null,lines:Object.freeze([
      'Unrecognized command. Type help for the read-only command list.',
      'Shell execution and provider dispatch are disabled.'
    ])
  });
  let lines=[];
  if(action==='help'){
    lines=[
      'EXODIA LOCAL OPERATOR TERMINAL · UI-ONLY COMMANDS',
      'help · status · providers · tasks · layout · layout reset',
      'focus · clear · open workflows · open companions',
      'Commands never dispatch providers, execute shell code or publish.'
    ];
  }else if(action==='status'){
    const summary=telemetry?.summary?.();
    lines=[
      'Command bridge: '+(summary?.transportLabel||'Telemetry unavailable'),
      'Active provider tasks: '+(Number.isInteger(summary?.active)?summary.active:'unknown'),
      'Authenticated vendor channels: NOT VERIFIED',
      'Production release: DISABLED'
    ];
  }else if(action==='providers'){
    const summary=telemetry?.summary?.();
    lines=['PROVIDER SESSIONS · local observations only'];
    for(const row of summary?.providers||[]){
      lines.push(row.id.toUpperCase()+' · '+row.session+' · '+row.active+' active');
    }
    if(!summary?.providers?.length)lines.push('Provider snapshots unavailable');
    lines.push('No individual provider WebSocket is verified');
  }else if(action==='tasks'){
    const summary=telemetry?.summary?.();
    lines=['Observed active tasks: '+(Number.isInteger(summary?.active)?summary.active:'unknown'),
      'Task prompts, answers and private instructions are not exposed here.'];
  }else if(action==='layout'){
    const view=layout?.layout;
    lines=['Desktop order: '+(Array.isArray(view?.order)?view.order.join(' → '):'unavailable'),
      'Compact order: '+(Array.isArray(view?.compactOrder)?view.compactOrder.join(' → '):'unavailable'),
      'Expanded: '+(view?.expanded||'none'),
      'Preferences: browser-local only'];
  }else if(action==='layout reset'){
    lines=['Default panel order restored on this browser.'];
  }else if(action==='focus'){
    lines=['Operations focus toggled locally.'];
  }else if(action==='clear'){
    lines=['Terminal history cleared (session only).'];
  }else if(action==='open workflows'){
    lines=['Opening the local workflow planner.'];
  }else if(action==='open companions'){
    lines=['Opening the local companion roster.'];
  }
  return Object.freeze({ok:true,action,lines:Object.freeze(lines)});
}
export class CommandHistory{
  constructor(limit=40){
    if(!Number.isInteger(limit)||limit<1||limit>100)throw RangeError('Invalid terminal history limit');
    this.limit=limit;
    this.items=[];this.index=0;this.draft='';
  }
  push(value){
    if(!normalizeCommand(value))return;
    if(this.items[this.items.length-1]!==value){
      this.items.push(value);
      if(this.items.length>this.limit)this.items.shift();
    }
    this.index=this.items.length;this.draft='';
  }
  previous(draft=''){
    if(this.index===this.items.length)this.draft=draft;
    this.index=Math.max(0,this.index-1);
    return this.items[this.index]??draft;
  }
  next(){
    this.index=Math.min(this.items.length,this.index+1);
    return this.items[this.index]??this.draft;
  }
  clear(){this.items=[];this.index=0;this.draft='';}
}
