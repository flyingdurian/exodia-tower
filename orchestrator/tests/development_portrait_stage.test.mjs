import test from 'node:test';
import assert from 'node:assert/strict';
import {validDevelopmentManifest, MOOD_TO_REVIEW} from '../frontend/development_portrait_stage.mjs';

function fixture(){
 const keys=Array.from({length:33},(_,i)=>'state_'+i);
 keys.splice(0,10,'idle','working','awaiting_command','thinking','defeat','angered','happy','excited','celebrating','sleeping');
 const states=Object.fromEntries(keys.map((key,i)=>[key,{
   key,sha256:i.toString(16).padStart(64,'0'),source_sha256:(i+50).toString(16).padStart(64,'0'),
   image_url:'/api/albedo/state33/review-assets/'+key,
   owner_approved:false,native_production_certified:false,
   owner_development_status:i<4?'REVIEW_ONLY_OWNER_ACCEPTED_NON_NATIVE':'OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT'}]));
 return {count:33,production_release_enabled:false,owner_development_review_only_count:4,
  state_order:keys,states};
}

test('valid 33-state development review does not imply production certification',()=>{
 const m=fixture();
 assert.equal(validDevelopmentManifest(m),true);
 assert.equal(MOOD_TO_REVIEW.processing,'working');
 assert.equal(MOOD_TO_REVIEW.waiting,'awaiting_command');
 assert.equal(MOOD_TO_REVIEW.failed,'defeat');
 assert.equal(MOOD_TO_REVIEW.frustration,'angered');
 assert.equal(MOOD_TO_REVIEW.proud,'celebrating');
});
test('rejects production release, missing/duplicate states and forged approval',()=>{
 const m=fixture();m.production_release_enabled=true;
 assert.equal(validDevelopmentManifest(m),false);
 m.production_release_enabled=false;m.states.idle.owner_approved=true;
 assert.equal(validDevelopmentManifest(m),false);
 m.states.idle.owner_approved=false;m.state_order[1]=m.state_order[0];
 assert.equal(validDevelopmentManifest(m),false);
});
test('rejects unsafe remote URLs, wrong hash and false native certification',()=>{
 const m=fixture();m.states.idle.image_url='https://example.com/bad.png';
 assert.equal(validDevelopmentManifest(m),false);
 m.states.idle.image_url='/api/albedo/state33/review-assets/idle';m.states.idle.sha256='not-hash';
 assert.equal(validDevelopmentManifest(m),false);
 m.states.idle.sha256='0'.repeat(64);m.states.idle.native_production_certified=true;
 assert.equal(validDevelopmentManifest(m),false);
});

test('duplicate source or review bytes fail closed',()=>{
 const m=fixture();m.states.working.source_sha256=m.states.idle.source_sha256;
 assert.equal(validDevelopmentManifest(m),false);
});
