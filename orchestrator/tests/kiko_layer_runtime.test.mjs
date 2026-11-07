import test from 'node:test';import assert from 'node:assert/strict';
import {layerOrder,paintRegisteredLayers,validateRegistration,ART_PRODUCTION_STATUS} from '../frontend/kiko_layer_runtime.mjs';
const manifest={source_size:[200,300],layers:{head:{z:2,box:[40,40,85,90],pivot:[53,50],polygons:[[[40,40],[85,40],[85,90]]]},body:{z:1,box:[15,72,113,200],pivot:[40,80],polygons:[[[15,72],[113,72],[113,200]]]}}};
const images=new Map([['head',{naturalWidth:45,naturalHeight:50}],['body',{naturalWidth:98,naturalHeight:128}]]);
test('registered layer sort respects depth',()=>assert.deepEqual(layerOrder(manifest).map(x=>x[0]),['body','head']));
test('registered RGBA renderer uses layer images and source-space boxes',()=>{const calls=[],ctx={save(){},restore(){},drawImage(...x){calls.push(x)}};const r=paintRegisteredLayers(ctx,manifest,images,{},()=>{});assert.equal(calls.length,2);assert.deepEqual(calls[0].slice(1),[15,72,98,128]);assert.deepEqual(r.missing,[])});
test('missing sprite is reported, never substituted by original background',()=>{const ctx={save(){},restore(){},drawImage(){throw Error('not called')}};const r=paintRegisteredLayers(ctx,manifest,new Map(),{},()=>{});assert.deepEqual(r.missing,['body','head'])});
test('registration validates source size, box, pivots and all needed images',()=>{const ok=validateRegistration(manifest,images);assert.equal(ok.ready.length,2);assert.equal(ok.production_ready,false);assert.equal(ok.quality_gate,ART_PRODUCTION_STATUS);assert.equal(validateRegistration(manifest,new Map()).rejected.length,2)});
