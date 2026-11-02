import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolveState,registryValid,eligible,PortraitStateManager} from '../frontend/portrait_state_manager.mjs';
const r=JSON.parse(readFileSync(new URL('../frontend/companions/production/kiko/portrait_registry.json',import.meta.url)));
test('full matrix present',()=>{assert.equal(registryValid(r),true);assert.equal(Object.keys(r.states).length,33);assert.equal(Object.keys(r.loops).length,3)});
test('aliases bind to canonical statuses',()=>{assert.equal(resolveState('failed',r),'defeat');assert.equal(resolveState('frustration',r),'tantrum');assert.equal(resolveState('processing',r),'working')});
test('unverified assets cannot appear',()=>{for(const s of Object.values(r.states))assert.equal(eligible(r,s),false)});
test('release flag protects legacy screen',async()=>{const m=new PortraitStateManager({fetcher:async()=>({ok:true,json:async()=>r})});assert.equal(await m.initialize(),false);assert.equal(await m.setState('happy'),false)});
