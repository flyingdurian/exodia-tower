/** Operator workspace controls: native DnD + buttons; browser-local layout only. */
import {ROLES,defaultLayout,readLayout,saveLayout,reduceLayout}
  from './frontshell_layout_contract.mjs';
const TITLES=Object.freeze({
  output:'Response / missions',hero:'Albedo operations',control:'Operator / systems'
});
const panelSelectors=Object.freeze({
  output:'.output-col',hero:'.hero-col',control:'.control-col'
});
function button(text,title,action){
  const el=document.createElement('button');
  el.type='button';el.className='fs-layout-button';
  el.title=title;el.setAttribute('aria-label',title);
  el.dataset.layoutAction=action;
  el.textContent=text;
  return el;
}
export function startFrontshellLayout({
  doc=document,win=window,
  storage=null
}={}){
  const grid=doc.querySelector('.command-grid');
  const shell=doc.querySelector('.app-shell');
  if(!grid||!shell)return null;
  let localStorage=storage;
  if(!localStorage)try{localStorage=win.localStorage;}catch(_){}
  const nodes=Object.fromEntries(
    ROLES.map(role=>[role,doc.querySelector(panelSelectors[role])])
  );
  if(ROLES.some(role=>!nodes[role]))return null;
  let layout=readLayout(localStorage);
  let dragging=null;
  const headers={};
  const saved=doc.getElementById('fsLayoutSaved');
  const reset=doc.getElementById('fsLayoutReset');
  function dispatch(action){
    const next=reduceLayout(layout,action);
    if(JSON.stringify(next)===JSON.stringify(layout))return layout;
    layout=next;
    const stored=saveLayout(localStorage,layout);
    apply();
    if(saved)saved.textContent=stored?'LAYOUT SAVED LOCALLY':
      'LOCAL STORAGE UNAVAILABLE · SESSION ONLY';
    return layout;
  }
  for(const role of ROLES){
    const column=nodes[role];
    column.dataset.fsPanel=role;
    const bar=doc.createElement('div');
    bar.className='fs-panel-toolbar';
    bar.dataset.fsHandle=role;
    bar.draggable=true;
    bar.setAttribute('aria-label',TITLES[role]+' workspace controls');
    const label=doc.createElement('span');
    label.className='fs-panel-title';label.textContent=TITLES[role];
    bar.append(label);
    const actions=doc.createElement('div');
    actions.className='fs-panel-actions';
    const left=button('←','Move '+TITLES[role]+' left','left');
    const right=button('→','Move '+TITLES[role]+' right','right');
    const min=button('−','Minimize '+TITLES[role],'minimize');
    const expand=button('⤢','Expand '+TITLES[role],'expand');
    const controls=[left,right,min,expand];
    for(const control of controls)actions.append(control);
    bar.append(actions);column.prepend(bar);
    left.addEventListener('click',()=>dispatch({type:'move',role,direction:-1}));
    right.addEventListener('click',()=>dispatch({type:'move',role,direction:1}));
    min.addEventListener('click',()=>dispatch({type:'minimize',role}));
    expand.addEventListener('click',()=>{
      if(shell.dataset.frontshellFocus==='true'){
        doc.getElementById('frontshellFocusToggle')?.click();
      }
      dispatch({type:'expand',role});
    });
    bar.addEventListener('dragstart',event=>{
      if(event.target?.closest?.('button')){event.preventDefault();return;}
      dragging=role;
      try{
        event.dataTransfer.effectAllowed='move';
        event.dataTransfer.setData('text/plain',role);
      }catch(_){}
    });
    bar.addEventListener('dragend',()=>{dragging=null;});
    bar.addEventListener('dragover',event=>{
      if(dragging&&dragging!==role)event.preventDefault();
    });
    bar.addEventListener('drop',event=>{
      if(!dragging||dragging===role)return;
      event.preventDefault();
      const src=layout.order.indexOf(dragging);
      const dst=layout.order.indexOf(role);
      if(src>=0&&dst>=0){
        // Repeated adjacent swaps are validated and persisted individually.
        const direction=src<dst?1:-1;
        let current=dragging;
        for(let i=src;i!==dst;i+=direction){
          layout=reduceLayout(layout,{type:'move',role:current,direction});
        }
        const stored=saveLayout(localStorage,layout);
        if(saved)saved.textContent=stored?'LAYOUT SAVED LOCALLY':'SESSION ONLY';
        apply();
      }
      dragging=null;
    });
    headers[role]={bar,left,right,min,expand};
  }
  function apply(){
    const width=win.innerWidth||1400;
    const expanded=layout.expanded;
    const focused=shell.dataset.frontshellFocus==='true';
    shell.dataset.fsExpanded=expanded||'none';
    for(const role of ROLES){
      const index=layout.order.indexOf(role);
      const node=nodes[role],header=headers[role];
      node.style.order=String(index);
      node.dataset.fsMinimized=String(layout.minimized[role]);
      node.dataset.fsExpanded=String(expanded===role);
      header.min.setAttribute('aria-expanded',String(!layout.minimized[role]));
      header.min.textContent=layout.minimized[role]?'+':'−';
      header.min.title=(layout.minimized[role]?'Restore ':'Minimize ')+TITLES[role];
      header.min.setAttribute('aria-label',header.min.title);
      header.expand.setAttribute('aria-pressed',String(expanded===role));
      header.expand.textContent=expanded===role?'⤡':'⤢';
      header.expand.title=(expanded===role?'Restore ':'Expand ')+TITLES[role];
      header.expand.setAttribute('aria-label',header.expand.title);
      header.left.disabled=index===0||!!expanded;
      header.right.disabled=index===2||!!expanded;
      node.style.gridColumn='';
      node.style.gridRow='';
    }
    if(focused||expanded){
      grid.style.gridTemplateColumns='minmax(0,1fr)';
      const active=focused?'hero':expanded;
      nodes[active].style.gridColumn='1';
      nodes[active].style.gridRow='1';
    }else if(width>1180){
      grid.style.gridTemplateColumns=layout.order.map(role=>
        'minmax(0,'+(role==='hero'?'1.56':'0.83')+'fr)').join(' ');
      for(const role of ROLES){
        nodes[role].style.gridColumn=String(layout.order.indexOf(role)+1);
        nodes[role].style.gridRow='1';
      }
    }else if(width>910){
      grid.style.gridTemplateColumns='repeat(2,minmax(0,1fr))';
      for(const role of ROLES){
        const index=layout.order.indexOf(role);
        nodes[role].style.gridColumn=index===2?'1 / -1':String(index+1);
        nodes[role].style.gridRow=index===2?'2':'1';
      }
    }else{
      grid.style.gridTemplateColumns='';
    }
    if(saved&&saved.textContent==='')saved.textContent='BROWSER-LOCAL WORKSPACE';
  }
  reset?.addEventListener('click',()=>{
    layout=defaultLayout();
    const stored=saveLayout(localStorage,layout);
    if(shell.dataset.frontshellFocus==='true'){
      doc.getElementById('frontshellFocusToggle')?.click();
    }
    apply();
    if(saved)saved.textContent=stored?'DEFAULT LAYOUT SAVED':'DEFAULT · SESSION ONLY';
  });
  const onFocus=()=>{
    if(shell.dataset.frontshellFocus==='true'&&layout.expanded){
      layout=reduceLayout(layout,{type:'expand',role:layout.expanded});
      saveLayout(localStorage,layout);
    }
    apply();
  };
  doc.getElementById('frontshellFocusToggle')?.addEventListener('click',onFocus);
  win.addEventListener('resize',apply);
  apply();
  const runtime={
    get layout(){return layout;},
    change:dispatch,
    reset:()=>reset?.click(),
    stop(){win.removeEventListener('resize',apply);}
  };
  win.__exodiaPhase2Layout=runtime;
  return runtime;
}
if(typeof document!=='undefined')startFrontshellLayout();
