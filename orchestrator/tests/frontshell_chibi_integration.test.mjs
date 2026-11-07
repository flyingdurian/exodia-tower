import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {startAlbedoChibi} from '../frontend/albedo_chibi_boot.mjs';
import {AlbedoChibiController,DIRECTIONS} from '../frontend/albedo_chibi_controller.mjs';

const manifest=JSON.parse(readFileSync(new URL('../frontend/albedo_chibi_manifest.json',import.meta.url),'utf8'));

function harness({reduced=false}={}){
  const events={};let raf=0;const buttons=[];
  function makeButton(name,key){
    const attributes={};
    const button={dataset:{[key]:name},attributes,
      addEventListener(type,fn){events['button:'+key+':'+name+':'+type]=fn;},
      removeEventListener(){},
      setAttribute(key,value){attributes[key]=value;},
      removeAttribute(key){delete attributes[key];}
    };
    buttons.push(button);return button;
  }
  const mapNodes={};const zoneButtons=['home','terminal','waiting','result','recovery']
    .map(name=>makeButton(name,'chibiZone'));
  const developerButtons=['terminal','waiting'].map(name=>makeButton(name,'chibiGo'));
  const actor={hidden:false,style:{left:'',top:'',setProperty(){}},dataset:{}};
  const heading={textContent:''};
  const marker={hidden:false,querySelector:()=>heading};
  const frame={src:'',hidden:true};
  const text={textContent:'',parentElement:{append(node){mapNodes.chibiBehaviorCue=node;}}};
  const floor={clientWidth:740,clientHeight:350,
    addEventListener(type,fn){events['floor:'+type]=fn;},
    removeEventListener(){},
    getBoundingClientRect(){return {left:10,top:20,width:740,height:350};}};
  const toggle={textContent:'',attributes:{},
    addEventListener(type,fn){events['toggle:'+type]=fn;},
    removeEventListener(){},
    setAttribute(k,v){this.attributes[k]=v}};
  Object.assign(mapNodes,{
    chibiActor:actor,chibiFrame:frame,chibiMarker:marker,
    chibiArtStatus:{textContent:''},chibiZoneState:text,
    chibiFloor:floor,chibiMotionToggle:toggle,
    chibiHeadingReadout:{textContent:''},chibiStrideReadout:{textContent:''}
  });
  const root={dataset:{},
    querySelector(s){return mapNodes[s.slice(1)]??null;},
    querySelectorAll(s){return s==='[data-chibi-zone]'?zoneButtons:[]}};
  const companion={value:'kiko',
    addEventListener(type,fn){events['companion:'+type]=fn;},
    removeEventListener(){}};
  const doc={
    getElementById(id){return id==='chibiOperations'?root:
      id==='chibiArtStatus'?mapNodes.chibiArtStatus:
      id==='companion'?companion:null;},
    querySelectorAll(s){return s==='[data-chibi-go]'?developerButtons:[];},
    createElement(){return {id:'',textContent:'',setAttribute(){}};}
  };
  const win={
    addEventListener(type,fn){events['window:'+type]=fn;},
    removeEventListener(){},
    requestAnimationFrame(){return ++raf;},
    cancelAnimationFrame(){},
    matchMedia(){return {matches:reduced}}
  };
  return {doc,win,events,root,mapNodes,frame,actor,
    companion,zoneButtons,developerButtons,toggle};
}

test('direct waypoint movement respects finite bounds and all eight heading contracts',()=>{
  const c=new AlbedoChibiController(manifest);
  for(const [x,y] of [[-7,7],[2,-4],[.2,.3],[.9,.8]]){
    c.goToPoint(x,y);
    for(let i=0;i<3000&&!c.arrived;i++)c.tick(.05);
    assert.equal(c.arrived,true);
    assert.ok(c.position.x>=manifest.anchors.floor_bounds.x[0]);
    assert.ok(c.position.x<=manifest.anchors.floor_bounds.x[1]);
    assert.ok(c.position.y>=manifest.anchors.floor_bounds.y[0]);
    assert.ok(c.position.y<=manifest.anchors.floor_bounds.y[1]);
    assert.ok(DIRECTIONS.includes(c.snapshot().heading));
  }
  assert.throws(()=>c.goToPoint(NaN,.2),/finite/);
  assert.throws(()=>c.goToPoint(.2,Infinity),/finite/);
  assert.throws(()=>c.goToPoint(.2,.2,'nonexistent'),/Unknown floor/);
});
test('clickable floor, station navigation and public task updates use same controller',async()=>{
  const h=harness();
  const runtime=await startAlbedoChibi({
    doc:h.doc,win:h.win,loadManifest:async()=>manifest
  });
  assert.equal(h.root.dataset.ready,'1');
  assert.ok(h.mapNodes.chibiArtStatus.textContent.includes('40 ART FRAMES PENDING'));
  assert.equal(h.frame.hidden,true);
  h.events['button:chibiZone:terminal:click']();
  assert.equal(runtime.controller.zone,'terminal');
  assert.equal(runtime.manualRoute,true);
  assert.equal(h.zoneButtons[1].attributes['aria-current'],'location');
  assert.equal(h.mapNodes.chibiBehaviorCue.textContent.includes('Operator floor'),true);
  h.events['floor:click']({target:{closest:()=>null},clientX:185,clientY:265});
  assert.equal(runtime.controller.zone,'manual');
  assert.ok(Math.abs(runtime.controller.target.x-175/740)<.00001);
  assert.ok(Math.abs(runtime.controller.target.y-245/350)<.00001);
  const initial=runtime.controller.position.x;
  runtime.controller.tick(.05);
  assert.notEqual(runtime.controller.position.x,initial);
  h.events['window:exodia:command-task']({detail:{
    taskId:'t-1',state:'running',agentId:'kiko',
    updatedAt:'2026-11-06T20:00:00Z'
  }});
  assert.equal(runtime.controller.zone,'terminal');
  assert.equal(runtime.manualRoute,false);
  assert.equal(h.root.dataset.behavior,'processing');
  h.events['button:chibiZone:recovery:click']();
  assert.equal(runtime.controller.zone,'recovery');
  h.events['window:exodia:command-task']({detail:{
    taskId:'t-1',state:'running',agentId:'kiko',
    updatedAt:'2026-11-06T20:00:10Z'
  }});
  assert.equal(runtime.controller.zone,'recovery',
    "Updated polling timestamp must not break operator route");
  h.events['window:exodia:command-task']({detail:{
    taskId:'t-1',state:'answered',agentId:'kiko',
    updatedAt:'2026-11-06T20:00:12Z'
  }});
  assert.equal(runtime.controller.zone,'result');
  assert.equal(h.root.dataset.behavior,'success');
  assert.equal(h.frame.hidden,true,'Pending artwork must never render as production');
  runtime.stop();
});
test('reduced motion and offstage companion selection suppress manual navigation',async()=>{
  const h=harness({reduced:true});
  const runtime=await startAlbedoChibi({
    doc:h.doc,win:h.win,loadManifest:async()=>manifest
  });
  assert.equal(h.toggle.attributes['aria-pressed'],'false');
  h.events['button:chibiZone:terminal:click']();
  assert.equal(runtime.controller.arrived,true);
  assert.equal(runtime.controller.zone,'terminal');
  h.events['toggle:click']();
  assert.equal(h.toggle.attributes['aria-pressed'],'true');
  h.events['button:chibiZone:home:click']();
  assert.equal(runtime.controller.arrived,false);
  h.companion.value='liu_bei';
  h.events['companion:change']();
  assert.equal(h.actor.hidden,true);
  assert.equal(runtime.moveToPoint(.5,.5),false);
  assert.equal(runtime.moveToZone('terminal'),false);
  runtime.stop();
});
