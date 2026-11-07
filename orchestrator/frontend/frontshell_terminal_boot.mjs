/** Phase 2 Frontshell drawer: syntax preview + bounded in-memory command history.
 * Does not provide a shell, arbitrary URL opener, or privileged API action.
 */
import {highlightCommand,normalizeCommand,
        runOperatorCommand,CommandHistory} from './frontshell_terminal_contract.mjs';
const COLORS=Object.freeze({keyword:'fs-token-keyword',argument:'fs-token-argument',
  unknown:'fs-token-unknown',invalid:'fs-token-invalid',space:'fs-token-space'});
function span(type,text){
  const el=document.createElement('span');
  el.className=COLORS[type]||COLORS.unknown;
  el.textContent=text;
  return el;
}
function paintTokens(target,raw){
  target.replaceChildren(...highlightCommand(raw).map(t=>span(t.kind,t.text)));
}
export function startFrontshellTerminal({
  doc=document,win=window
}={}){
  const root=doc.getElementById('fsOperatorTerminal');
  const toggle=doc.getElementById('fsTerminalToggle');
  const entry=doc.getElementById('fsTerminalInput');
  const form=doc.getElementById('fsTerminalForm');
  const preview=doc.getElementById('fsTerminalSyntax');
  const log=doc.getElementById('fsTerminalLog');
  const state=doc.getElementById('fsTerminalStatus');
  if(!root||!toggle||!entry||!form||!preview||!log||!state)return null;
  const history=new CommandHistory(40);
  function message(lines,{error=false,command=''}={}){
    const item=doc.createElement('div');
    item.className='fs-terminal-entry'+(error?' fs-terminal-error':'');
    if(command){
      const commandLine=doc.createElement('div');
      commandLine.className='fs-terminal-echo';
      commandLine.append(span('argument','› '));
      for(const t of highlightCommand(command))
        commandLine.append(span(t.kind,t.text));
      item.append(commandLine);
    }
    for(const line of lines){
      const row=doc.createElement('div');
      row.className='fs-terminal-line';
      row.textContent=String(line);
      item.append(row);
    }
    log.append(item);
    while(log.children.length>55)log.firstChild.remove();
    log.scrollTop=log.scrollHeight;
  }
  function execute(raw){
    const result=runOperatorCommand(raw,{
      telemetry:win.__exodiaPhase2Telemetry,
      layout:win.__exodiaPhase2Layout
    });
    if(result.ok&&result.action==='clear'){
      log.replaceChildren();
      history.clear();
      message(['Operator terminal history cleared.']);
    }else{
      message(result.lines,{error:!result.ok,command:raw});
      if(result.ok){
        history.push(raw);
        if(result.action==='layout reset')win.__exodiaPhase2Layout?.reset();
        else if(result.action==='focus')doc.getElementById('frontshellFocusToggle')?.click();
        else if(result.action==='open workflows')win.location.assign('/workflow-planner');
        else if(result.action==='open companions')win.location.assign('/companions');
      }
    }
    state.textContent=result.ok?'LOCAL COMMAND · NO PROVIDER DISPATCH':
      'COMMAND REJECTED · ONLY ALLOWLISTED ACTIONS';
    root.dataset.lastCommand=result.action||'rejected';
    return result;
  }
  const onSubmit=event=>{
    event.preventDefault();
    const raw=entry.value.trim();
    if(!raw)return;
    execute(raw);
    entry.value='';
    paintTokens(preview,'');
    entry.focus();
  };
  form.addEventListener('submit',onSubmit);
  const onInput=()=>paintTokens(preview,entry.value);
  entry.addEventListener('input',onInput);
  const onKey=event=>{
    if(event.key==='ArrowUp'){
      event.preventDefault();
      entry.value=history.previous(entry.value);
      onInput();
    }else if(event.key==='ArrowDown'){
      event.preventDefault();
      entry.value=history.next();
      onInput();
    }
  };
  entry.addEventListener('keydown',onKey);
  for(const button of root.querySelectorAll('[data-terminal-quick]')){
    button.addEventListener('click',()=>{
      const action=button.dataset.terminalQuick;
      if(!normalizeCommand(action))return;
      execute(action);
    });
  }
  toggle.addEventListener('click',()=>{
    root.open=!root.open;
    toggle.setAttribute('aria-expanded',String(root.open));
    if(root.open)entry.focus();
  });
  root.addEventListener('toggle',()=>{
    toggle.setAttribute('aria-expanded',String(root.open));
  });
  message([
    'EXODIA / OPERATOR TERMINAL · UI-ONLY',
    'Type help or select a quick action. Shell/provider commands are disabled.'
  ]);
  return {execute,history,stop(){
    form.removeEventListener('submit',onSubmit);
    entry.removeEventListener('input',onInput);
    entry.removeEventListener('keydown',onKey);
  }};
}
if(typeof document!=='undefined')startFrontshellTerminal();
