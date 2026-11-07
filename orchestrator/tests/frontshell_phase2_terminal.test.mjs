import test from 'node:test';
import assert from 'node:assert/strict';
import {COMMANDS,highlightCommand,normalizeCommand,
        runOperatorCommand,CommandHistory} from '../frontend/frontshell_terminal_contract.mjs';
test('allowlist supports only local UI commands with safe syntax tokens',()=>{
  assert.equal(COMMANDS.length,10);
  assert.equal(normalizeCommand('  LAYOUT   RESET  '),'layout reset');
  assert.equal(normalizeCommand('rm -rf /'),null);
  assert.equal(normalizeCommand('provider login'),null);
  assert.equal(normalizeCommand('fetch /api/command/tasks'),null);
  assert.deepEqual(highlightCommand('open workflows').map(x=>x.kind),
    ['keyword','space','argument']);
  assert.equal(highlightCommand('<script>alert(1)</script>')[0].kind,'unknown');
});
test('terminal status and providers are read-only projections without secret echoes',()=>{
  const service={summary:()=>({
    transportLabel:'LOCAL EVENTS LINKED',active:2,
    providers:[{id:'chatgpt',session:'Open · sign-in unverified',active:1},
      {id:'ollama',session:'Local model reachable',active:1}],
    prompt:'SECRET_PROMPT',answer:'PRIVATE_ANSWER'
  })};
  const status=runOperatorCommand('status',{telemetry:service});
  assert.equal(status.ok,true);
  assert.ok(status.lines.join(' ').includes('NOT VERIFIED'));
  assert.equal(status.lines.join(' ').includes('SECRET_PROMPT'),false);
  const providers=runOperatorCommand('providers',{telemetry:service});
  assert.ok(providers.lines.join(' ').includes('WebSocket is verified')===false);
  assert.ok(providers.lines.join(' ').includes('No individual provider WebSocket is verified'));
  assert.equal(runOperatorCommand('layout reset').action,'layout reset');
  const invalid=runOperatorCommand('shell rm -rf /');
  assert.equal(invalid.ok,false);
  assert.equal(invalid.action,null);
  assert.ok(invalid.lines.join(' ').includes('disabled'));
});
test('history tracks only allowlisted commands and supports arrow navigation',()=>{
  const h=new CommandHistory(3);
  h.push('status');h.push('providers');h.push('tasks');h.push('help');
  h.push('eval(window.secret)'); // rejected, not saved
  assert.deepEqual(h.items,['providers','tasks','help']);
  assert.equal(h.previous('unfinished draft'),'help');
  assert.equal(h.previous(),'tasks');
  assert.equal(h.next(),'help');
  assert.equal(h.next(),'unfinished draft');
  h.clear();
  assert.deepEqual(h.items,[]);
  assert.equal(h.previous('draft'),'draft');
});
