/** Phase 4 interactive command palette and local workspace presets.
 * No code execution, arbitrary URL navigation, provider POST, or saved task text.
 */
import {ACTIONS,searchActions,actionById,safeOperatorNotice}
  from './frontshell_palette_contract.mjs';
import {builtinPreset,presetFor,savePreset}
  from './frontshell_presets_contract.mjs';

function node(tag,cls,text){
  const n=document.createElement(tag);if(cls)n.className=cls;
  if(text!==undefined)n.textContent=text;return n;
}
export function startFrontshellPalette({doc=document,win=window}={}){
  const container=doc.querySelector('.frontshell-brief-actions');
  const shell=doc.querySelector('.app-shell');
  if(!container||!shell)return null;
  let storage=null;
  try{storage=win.localStorage;}catch(_){}
  const launch=node('button','fs-palette-launch','Command palette  ⌘K');
  launch.type='button';launch.setAttribute('aria-haspopup','dialog');
  launch.setAttribute('aria-label','Open local command palette');
  const presetSelect=node('select','fs-presets-select');
  presetSelect.setAttribute('aria-label','Named workspace view');
  for(const [value,label] of [
    ['command','Command overview'],['investigation','Investigation'],
    ['operations','Operations focus'],['triage','Task triage'],
    ['custom1','Saved slot 1'],['custom2','Saved slot 2']
  ]){
    const option=node('option','',label);option.value=value;presetSelect.append(option);
  }
  container.append(launch,presetSelect);

  const dialog=node('dialog','fs-palette-dialog');
  dialog.id='fsOperatorPalette';
  dialog.setAttribute('aria-label','Local operator command palette');
  const panel=node('div','fs-palette-panel');
  const title=node('h2','','OPERATOR / COMMAND PALETTE');
  const tagline=node('p','','Local navigation, workspace presets and safe task context. No external commands.');
  const search=node('input','fs-palette-search');
  search.id='fsPaletteSearch';search.placeholder='Find a command or workspace…';
  search.autocomplete='off';search.spellcheck=false;search.maxLength=100;
  search.setAttribute('aria-label','Search safe operator actions');
  const results=node('div','fs-palette-results');
  results.id='fsPaletteResults';results.setAttribute('role','listbox');
  const hint=node('p','fs-palette-hint',
    '↑ ↓ Select · Enter Apply · Esc Close · Ctrl/⌘ K Toggle');
  const status=node('p','fs-palette-status','Browser-local commands only');
  status.setAttribute('role','status');
  panel.append(title,tagline,search,results,hint,status);
  dialog.append(panel);doc.body.append(dialog);

  const notices=node('div','fs-operator-notices');
  notices.id='fsOperatorNotices';notices.setAttribute('aria-label','Operational activity notices');
  notices.setAttribute('aria-live','polite');
  doc.body.append(notices);
  const noticeKeys=new Set();
  let matches=[],selected=0,lastActive=null;
  function showNotice(message,attention=false){
    const el=node('div','fs-operator-notice',message);
    if(attention)el.dataset.attention='true';
    notices.prepend(el);
    while(notices.children.length>4)notices.lastElementChild.remove();
  }
  function applyWorkspace(layout,name){
    const runtime=win.__exodiaPhase2Layout;
    if(!runtime||typeof runtime.applyPreset!=='function'){
      showNotice('Workspace control unavailable',true);return false;
    }
    const persisted=runtime.applyPreset(layout);
    status.textContent=name+(persisted?' · SAVED LOCALLY':' · SESSION ONLY');
    showNotice(status.textContent);
    return true;
  }
  function execute(id){
    const action=actionById(id);
    if(!action)return false;
    if(action.kind==='navigate'){
      win.location.assign(action.path);
    }else if(action.kind==='focus'){
      const target=doc.getElementById(action.target);
      if(!target)return false;
      if(action.target==='fsOperatorTerminal'&&!target.open)
        doc.getElementById('fsTerminalToggle')?.click();
      target.scrollIntoView?.({block:'center',behavior:'instant'});
    }else if(action.kind==='preset'){
      if(!applyWorkspace(builtinPreset(action.preset),action.label))return false;
      presetSelect.value=action.preset;
    }else if(action.kind==='save-slot'){
      if(!win.__exodiaPhase2Layout)return false;
      const stored=savePreset(storage,action.slot,win.__exodiaPhase2Layout.layout);
      showNotice(stored?'Workspace stored in '+action.slot:
        'Browser storage unavailable · preset not saved',!stored);
    }else if(action.kind==='load-slot'){
      const layout=presetFor(storage,action.slot);
      if(!layout){showNotice('No saved workspace in '+action.slot,true);return false;}
      if(!applyWorkspace(layout,action.label))return false;
      presetSelect.value=action.slot;
    }
    close();
    return true;
  }
  function render(){
    matches=searchActions(search.value);
    selected=Math.max(0,Math.min(selected,matches.length-1));
    const buttons=matches.map((a,i)=>{
      const button=node('button','fs-palette-option');
      button.type='button';button.dataset.action=a.id;
      button.id='fsPaletteOption'+i;
      button.setAttribute('role','option');
      button.setAttribute('aria-selected',String(selected===i));
      const left=node('span','fs-palette-item-name',a.label);
      const right=node('span','fs-palette-item-group',a.group);
      button.append(left,right);
      button.addEventListener('click',()=>execute(a.id));
      return button;
    });
    results.replaceChildren(...buttons);
    if(!matches.length)results.append(node('p','fs-palette-empty',
      'No matching allowlisted command'));
    search.setAttribute('aria-activedescendant',
      matches.length?'fsPaletteOption'+selected:'');
  }
  function open(){
    if(dialog.open)return;
    lastActive=doc.activeElement;
    search.value='';selected=0;render();
    dialog.showModal();search.focus();
  }
  function close(){
    if(dialog.open)dialog.close();
    lastActive?.focus?.();
  }
  function onKey(event){
    const editing=event.target?.matches?.('input,textarea,select,[contenteditable=true]');
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){
      event.preventDefault();dialog.open?close():open();return;
    }
    if(!dialog.open)return;
    if(event.key==='Escape'){event.preventDefault();close();return;}
    if(editing&&event.target!==search)return;
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();
      const direction=event.key==='ArrowDown'?1:-1;
      selected=matches.length?(selected+direction+matches.length)%matches.length:0;
      render();
    }else if(event.key==='Enter'){
      event.preventDefault();
      if(matches[selected])execute(matches[selected].id);
    }
  }
  const onTask=event=>{
    const notice=safeOperatorNotice(event?.detail);
    if(!notice||noticeKeys.has(notice.key))return;
    noticeKeys.add(notice.key);
    if(noticeKeys.size>100)noticeKeys.clear();
    if(notice.requiresAttention||['answered','failed'].includes(event.detail.state))
      showNotice(notice.label,notice.requiresAttention);
  };
  const onPreset=()=>{
    const id=presetSelect.value;
    const layout=id.startsWith('custom')?presetFor(storage,id):builtinPreset(id);
    if(!layout){showNotice('Preset slot is empty',true);return;}
    applyWorkspace(layout,'PRESET · '+id.toUpperCase());
  };
  launch.addEventListener('click',open);
  search.addEventListener('input',()=>{selected=0;render();});
  doc.addEventListener('keydown',onKey);
  win.addEventListener('exodia:command-task',onTask);
  presetSelect.addEventListener('change',onPreset);
  dialog.addEventListener('click',event=>{
    if(event.target===dialog)close();
  });
  const api={
    open,close,execute,
    get options(){return [...matches];},
    stop(){
      doc.removeEventListener('keydown',onKey);
      win.removeEventListener('exodia:command-task',onTask);
      launch.remove();presetSelect.remove();dialog.remove();notices.remove();
    }
  };
  win.__exodiaPhase4Palette=api;
  return api;
}
if(typeof document!=='undefined')startFrontshellPalette();
