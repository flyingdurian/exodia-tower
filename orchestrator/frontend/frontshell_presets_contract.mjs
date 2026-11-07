/** Phase 4: browser-only named workspace views. No task, provider or art data persisted. */
import {defaultLayout,validateLayout} from './frontshell_layout_contract.mjs';
export const PRESET_KEY='exodia.frontshell.presets.v1';
export const PRESET_SCHEMA='exodia.frontshell.presets/v1';
export const BUILTINS=Object.freeze(['command','investigation','operations','triage']);
export const SLOTS=Object.freeze(['custom1','custom2','custom3']);
const schema=()=>({schema:PRESET_SCHEMA,slots:{}});
export function builtinPreset(name){
  if(!BUILTINS.includes(name))throw Error('Unknown workspace preset');
  const current=defaultLayout();
  const requested=name==='investigation'?'output':name==='operations'?'hero':
    name==='triage'?'control':null;
  return validateLayout({...current,expanded:requested});
}
export function validatePresets(value){
  if(!value||value.schema!==PRESET_SCHEMA||!value.slots||
     typeof value.slots!=='object'||Array.isArray(value.slots)||
     Object.keys(value.slots).some(k=>!SLOTS.includes(k)))
    throw Error('Invalid browser preset storage');
  const result={};
  for(const key of SLOTS){
    if(Object.hasOwn(value.slots,key))result[key]=validateLayout(value.slots[key]);
  }
  return Object.freeze({schema:PRESET_SCHEMA,slots:Object.freeze(result)});
}
export function readPresets(storage){
  try{
    const raw=storage?.getItem?.(PRESET_KEY);
    if(!raw)return validatePresets(schema());
    if(raw.length>2800)throw Error('Oversized browser presets');
    return validatePresets(JSON.parse(raw));
  }catch(_){return validatePresets(schema());}
}
export function savePreset(storage,slot,layout){
  if(!SLOTS.includes(slot))throw Error('Unknown browser preset slot');
  const current=readPresets(storage);
  const candidate=validatePresets({schema:PRESET_SCHEMA,
    slots:{...current.slots,[slot]:validateLayout(layout)}});
  if(!storage||typeof storage.setItem!=='function')return false;
  try{storage.setItem(PRESET_KEY,JSON.stringify(candidate));return true;}catch(_){return false;}
}
export function presetFor(storage,name){
  if(BUILTINS.includes(name))return builtinPreset(name);
  if(!SLOTS.includes(name))throw Error('Unknown preset');
  return readPresets(storage).slots[name]||null;
}
