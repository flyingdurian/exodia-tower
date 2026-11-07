/** Cosmetic state-driven signals. Neither portraits nor registration coordinates are mutated. */
export const SIGNALS=Object.freeze(['none','warning_pulse','focus_resonance','strain_glitch','triumphant_halo','casting_arcana','low_hp']);
const accepted=new Set(SIGNALS);
export function resolveSignal(base='none',telemetry={}){
 if(telemetry.alert===true)return 'warning_pulse';
 if(Number.isFinite(telemetry.hp)&&telemetry.hp<=0.25)return 'low_hp';
 if(telemetry.specialCasting===true)return 'casting_arcana';
 if(telemetry.strained===true)return 'strain_glitch';
 return accepted.has(base)?base:'none';
}
export function signalForState(registry,key,telemetry={}){
 return resolveSignal(registry?.states?.[key]?.signal_overlay??'none',telemetry);
}
export function applySignalLayer(el,name){
 if(!el)return;el.setAttribute('data-signal',accepted.has(name)?name:'none');
 el.setAttribute('aria-hidden','true');
}
