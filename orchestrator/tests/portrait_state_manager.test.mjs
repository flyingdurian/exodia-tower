import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolveState,registryValid,eligible,PortraitStateManager} from '../frontend/portrait_state_manager.mjs';
const r=JSON.parse(readFileSync(new URL('../frontend/companions/production/kiko/portrait_registry.json',import.meta.url)));
test('full matrix present',()=>{assert.equal(registryValid(r),true);assert.equal(Object.keys(r.states).length,33);assert.equal(Object.keys(r.loops).length,3)});
test('aliases bind to canonical statuses',()=>{assert.equal(resolveState('failed',r),'defeat');assert.equal(resolveState('frustration',r),'tantrum');assert.equal(resolveState('processing',r),'working')});
test('unverified assets cannot appear',()=>{for(const s of Object.values(r.states))assert.equal(eligible(r,s),false)});
test('release flag protects legacy screen',async()=>{const m=new PortraitStateManager({fetcher:async()=>({ok:true,json:async()=>r})});assert.equal(await m.initialize(),false);assert.equal(await m.setState('happy'),false)});

import {signalForState,resolveSignal,SIGNALS} from '../frontend/signal_overlay.mjs';
test('33 signals are defined and eligible values',()=>{assert.equal(Object.keys(r.states).length,33);for(const state of Object.values(r.states))assert.ok(SIGNALS.includes(state.signal_overlay))});
test('status auras respond to HP, alerts, casting without affecting base image',()=>{assert.equal(signalForState(r,'working'),'focus_resonance');assert.equal(signalForState(r,'idle',{hp:.10}),'low_hp');assert.equal(signalForState(r,'working',{alert:true,hp:.05}),'warning_pulse');assert.equal(signalForState(r,'working',{specialCasting:true}),'casting_arcana');assert.equal(resolveSignal('bogus'),'none')});
