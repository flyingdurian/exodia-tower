/** EXODIA Phase 2 local layout preference contract. Never persist tasks or secrets. */
export const LAYOUT_KEY='exodia.frontshell.layout.v2';
export const ROLES=Object.freeze(['output','hero','control']);
export const SCHEMA='exodia.frontshell.layout/v2';
const base=()=>({
  schema:SCHEMA,
  order:[...ROLES],
  minimized:{output:false,hero:false,control:false},
  expanded:null
});
export function validateLayout(candidate){
  if(!candidate||typeof candidate!=='object'||candidate.schema!==SCHEMA
     ||!Array.isArray(candidate.order)
     ||candidate.order.length!==3
     ||new Set(candidate.order).size!==3
     ||candidate.order.some(v=>!ROLES.includes(v))
     ||!candidate.minimized||typeof candidate.minimized!=='object'
     ||ROLES.some(id=>typeof candidate.minimized[id]!=='boolean')
     ||(candidate.expanded!==null&&!ROLES.includes(candidate.expanded))
     ||(candidate.expanded!==null&&candidate.minimized[candidate.expanded]))
    throw new Error('Invalid persisted Frontshell layout');
  return Object.freeze({
    schema:SCHEMA,
    order:Object.freeze([...candidate.order]),
    minimized:Object.freeze(Object.fromEntries(
      ROLES.map(role=>[role,candidate.minimized[role]]))),
    expanded:candidate.expanded
  });
}
export function defaultLayout(){return validateLayout(base());}
export function readLayout(storage){
  try{
    const raw=storage?.getItem?.(LAYOUT_KEY);
    if(!raw)return defaultLayout();
    if(raw.length>2000)throw Error('Preference record is oversized');
    return validateLayout(JSON.parse(raw));
  }catch(_){return defaultLayout();}
}
export function saveLayout(storage,layout){
  const validated=validateLayout(layout);
  try{
    storage?.setItem?.(LAYOUT_KEY,JSON.stringify(validated));
    return true;
  }catch(_){return false;}
}
export function reduceLayout(layout,action){
  const previous=validateLayout(layout);
  const next={
    schema:SCHEMA,
    order:[...previous.order],
    minimized:{...previous.minimized},
    expanded:previous.expanded
  };
  if(action?.type==='reset')return defaultLayout();
  if(!ROLES.includes(action?.role))throw Error('Unknown workspace panel');
  const role=action.role;
  if(action.type==='move'){
    if(!Number.isInteger(action.direction)||Math.abs(action.direction)!==1)
      throw Error('Direction must be left or right');
    const pos=next.order.indexOf(role);
    const at=pos+action.direction;
    if(at>=0&&at<next.order.length){
      [next.order[pos],next.order[at]]=[next.order[at],next.order[pos]];
    }
  }else if(action.type==='minimize'){
    if(next.expanded===role)next.expanded=null;
    next.minimized[role]=!next.minimized[role];
  }else if(action.type==='expand'){
    if(next.minimized[role])next.minimized[role]=false;
    next.expanded=next.expanded===role?null:role;
  }else{
    throw Error('Unsupported layout action');
  }
  return validateLayout(next);
}
