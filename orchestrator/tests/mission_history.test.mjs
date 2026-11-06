import test from 'node:test';
import assert from 'node:assert/strict';
import {filterMissionHistory,describeTask,publicApiRows} from '../frontend/mission_history.mjs';
const tasks=[
 {id:'1',provider:'chatgpt',agent_id:'kiko',state:'answered',prompt:'Summarize my report',answer:'ok',private_instructions:'DO NOT DISPLAY'},
 {id:'2',provider:'gemini',agent_id:'router',state:'failed',prompt:'Analyze region',error:'Could not connect'},
 {id:'3',provider:'ollama',agent_id:'kiko',state:'running',prompt:'Write summary'},
 {id:'4',provider:'deepseek',agent_id:'kiko',state:'cancelled',prompt:'Compute budget'}
];
test('searches prompt/provider/agent/ID but never private instructions or model answers',()=>{
 assert.deepEqual(filterMissionHistory(tasks,{query:'summary'}).map(x=>x.id),['3']);
 assert.deepEqual(filterMissionHistory(tasks,{query:'DO NOT DISPLAY'}),[]);
 assert.deepEqual(filterMissionHistory(tasks,{query:'ok'}),[]);
 assert.deepEqual(filterMissionHistory(tasks,{query:'router'}).map(x=>x.id),['2']);
});
test('provider and status filters are composable and do not modify persisted records',()=>{
 const before=JSON.stringify(tasks);
 assert.deepEqual(filterMissionHistory(tasks,{provider:'chatgpt',state:'answered'}).map(x=>x.id),['1']);
 assert.deepEqual(filterMissionHistory(tasks,{state:'active'}).map(x=>x.id),['3']);
 assert.deepEqual(filterMissionHistory(tasks,{provider:'deepseek',state:'cancelled'}).map(x=>x.id),['4']);
 assert.equal(JSON.stringify(tasks),before);
});
test('cancellation and result messaging never claim remote abort or missing response',()=>{
 assert.match(describeTask(tasks[3]).lifecycle,/remote request may continue/i);
 assert.equal(describeTask(tasks[0]).lifecycle,'Answered');
 assert.match(describeTask({...tasks[0],state:'waiting_for_reply'}).lifecycle,/In progress/);
});
test('API configuration comes from catalog and never assumes credentials',()=>{
 const opts=[{value:'chatgpt',transport:'browser',available:true},
 {value:'chatgpt:api',label:'ChatGPT (api)',transport:'api',available:false,status:'not_configured'},
 {value:'gemini:api',label:'Gemini (api)',transport:'api',available:false,status:'not_configured'},
 {value:'deepseek:api',label:'DeepSeek (api)',transport:'api',available:false,status:'not_configured'}];
 const rows=publicApiRows({options:opts});assert.equal(rows.length,3);
 assert.ok(rows.every(x=>!x.configured&&x.description.includes('no requests sent')));
 assert.deepEqual(publicApiRows({}),[]);
});
