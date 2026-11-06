import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {AlbedoRoomBehavior} from '../frontend/albedo_room_behavior.mjs';
const manifest=JSON.parse(readFileSync(fileURLToPath(new URL('../frontend/albedo_chibi_manifest.json',import.meta.url)),'utf8'));
const engine=()=>new AlbedoRoomBehavior(manifest);

test('actual task lifecycle maps terminal -> waiting -> results -> home, never fabricated remote abort',()=>{
  const b=engine();const base={taskId:'task-a',agentId:'kiko'};
  for(const [state,zone,phase] of [
    ['queued','terminal','dispatch'],['opening','terminal','dispatch'],
    ['running','terminal','processing'],['waiting_for_reply','waiting','waiting'],
    ['answered','result','success'],['cancelled','home','cancelled']]){
    const x=b.ingest({...base,state});
    assert.equal(x.zone,zone);assert.equal(x.behavior,phase);assert.equal(x.visible,true);
    assert.equal(x.remoteCancellationConfirmed,false);
  }
});
test('failures use recovery zone; task owner and selected companion both gate Albedo',()=>{
  const b=engine();let x=b.ingest({taskId:'failed',agentId:'kiko',state:'failed'});
  assert.equal(x.zone,'recovery');assert.equal(x.behavior,'failure');
  x=b.selectCompanion('router');assert.equal(x.visible,false);
  x=b.ingest({taskId:'new',agentId:'kiko',state:'running'});assert.equal(x.visible,false);
  x=b.selectCompanion('kiko');assert.equal(x.visible,true);
  x=b.ingest({taskId:'another',agentId:'router',state:'answered'});assert.equal(x.visible,false);
});
test('a slower poll for the same task cannot undo a newer cancellation or result',()=>{
 const b=engine();const base={taskId:'same',agentId:'kiko'};
 b.ingest({...base,state:'running',updatedAt:'2026-11-04T12:00:00Z'});
 b.ingest({...base,state:'cancelled',updatedAt:'2026-11-04T12:00:03Z'});
 const stale=b.ingest({...base,state:'running',updatedAt:'2026-11-04T12:00:02Z'});
 assert.equal(stale.accepted,false);assert.equal(stale.stale,true);
 assert.equal(b.snapshot().state,'cancelled');
 // Explicitly choosing an older historic task is a user action, not a stale poll.
 assert.equal(b.ingest({taskId:'old',agentId:'kiko',state:'answered',updatedAt:'2026-01-01T00:00:00Z'}).accepted,true);
});
test('only minimal public task fields are copied; private instructions and answer never appear',()=>{
 const b=engine();const x=b.ingest({taskId:'uuid',agentId:'kiko',state:'waiting_for_reply',
   provider:'chatgpt',prompt:'SECRET_PROMPT',answer:'SECRET_ANSWER',private_instructions:'SECRET_INSTRUCTIONS',
   updatedAt:'2026-11-04T12:00:00Z'});
 assert.equal(x.zone,'waiting');
 const serialized=JSON.stringify(b.snapshot())+JSON.stringify(b.task);
 for(const secret of ['SECRET_PROMPT','SECRET_ANSWER','SECRET_INSTRUCTIONS'])assert.equal(serialized.includes(secret),false);
});
test('unknown provider task phase fails safe to home without unsafe exception or inferred success',()=>{
 const b=engine();const x=b.ingest({taskId:'new',agentId:'kiko',state:'provider_unexpected_state'});
 assert.equal(x.state,'idle');assert.equal(x.zone,'home');assert.equal(x.behavior,'idle');
});
