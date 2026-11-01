"""ChatGPT browser prompt submission tests: no consumer output extraction."""
import asyncio,time
import pytest
from fastapi.testclient import TestClient
from app.automation.chatgpt_bridge import ChatGPTSubmissionBridge
from app.automation.multi_wrapper import MultiWebSessionManager,OperatorActionRequired,SessionError

class Input:
 def __init__(self,page):self.page=page;self.first=self
 async def is_visible(self,timeout=650):return not self.page.blocked
 async def click(self,timeout=8000):
  self.page.focus=True
 async def is_enabled(self):return True
class Submit(Input):
 async def click(self,timeout=12000):
  if self.page.click_fails:raise TimeoutError('ambiguous click')
  assert self.page.focus and self.page.typed
  self.page.sent+=1
class Keys:
 def __init__(self,page):self.page=page
 async def press(self,key):self.page.pressed.append(key)
 async def insert_text(self,text):self.page.typed=text
class FakePage:
 def __init__(self):
  self.url='https://chatgpt.com';self.keyboard=Keys(self);self.focus=False
  self.typed='';self.sent=0;self.pressed=[];self.blocked=False
  self.click_fails=False;self.closed=False;self.shots=0
 async def goto(self,url,**kwargs):self.url=url
 def locator(self,selector):
  if selector in ('div.markdown','[data-message-author-role="assistant"]'):
   raise AssertionError('Automated consumer output extraction is prohibited here')
  if 'send' in selector.lower() or 'Send' in selector:return Submit(self)
  return Input(self)
 async def screenshot(self,**kwargs):self.shots+=1
 async def close(self):self.closed=True
class FakeContext:
 def __init__(self):self.pages=[FakePage()];self.created=[];self.closed=False
 async def new_page(self):
  page=FakePage();self.created.append(page);return page
 async def close(self):self.closed=True
class Factory:
 def __init__(self):self.contexts=[]
 async def launch_persistent_context(self,**kwargs):
  c=FakeContext();self.contexts.append(c);return c

def test_chatgpt_submit_two_isolated_tabs_and_manual_completion(tmp_path):
 async def run():
  factory=Factory()
  sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=ChatGPTSubmissionBridge(sessions,start_spacing=0)
  phases=[]
  first=await bridge.submit('first','Summarize this page',phase=phases.append)
  second=await bridge.submit('second','Explain the results')
  context=factory.contexts[0]
  assert len(context.created)==2
  assert [p.typed for p in context.created]==['Summarize this page','Explain the results']
  assert all(p.sent==1 for p in context.created)
  assert first['status']=='awaiting_operator' and not first['automatic_output']
  assert first['submission']=='send_clicked_unverified'
  assert 'typing' in phases and 'submitting' in phases
  assert bridge.snapshot()['pending_count']==2
  with pytest.raises(OperatorActionRequired,match='pending review'):
   await bridge.submit('third','This must not run')
  result=await bridge.complete('first','Operator-approved answer')
  assert result['source']=='operator_supplied'
  assert context.created[0].closed and not context.created[1].closed
  assert bridge.snapshot()['pending_count']==1
  await bridge.cancel('second')
  assert context.created[1].closed
  assert bridge.snapshot()['pending_count']==0
  assert not context.closed
  await sessions.close()
 asyncio.run(run())

def test_submit_fails_closed_and_takes_debug_screenshot_when_composer_missing(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=ChatGPTSubmissionBridge(sessions,start_spacing=0)
  async def not_ready(*args,**kwargs):return None
  bridge._visible=not_ready
  with pytest.raises(OperatorActionRequired,match='composer'):
   await bridge.submit('failed','One prompt')
  tab=factory.contexts[0].created[0]
  assert tab.sent==0 and tab.closed and tab.shots==1
  assert not bridge.tasks
  await sessions.close()
 asyncio.run(run())

def test_ambiguous_send_is_never_retried(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=ChatGPTSubmissionBridge(sessions,start_spacing=0)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   p=await original();p.click_fails=True;return p
  ctx.new_page=make_page
  with pytest.raises(SessionError,match='submission failed'):
   await bridge.submit('ambiguous','Do not double send')
  assert ctx.created[0].sent==0
  assert ctx.created[0].closed
  assert ctx.created[0].shots==1
  assert bridge.snapshot()['pending_count']==0
  await sessions.close()
 asyncio.run(run())

def test_api_task_auto_submission_delivers_only_user_supplied_answer(monkeypatch):
 from app.api import server
 called=[]
 async def fake_submit(task_id,prompt,*,phase=None):
  called.append(('submit',task_id,prompt))
  if phase:
   for state in ('typing','submitting','awaiting_operator'):phase(state)
  return {'status':'awaiting_operator','automatic_output':False}
 async def fake_complete(task_id,answer):
  called.append(('complete',task_id,answer))
  return {'source':'operator_supplied','answer':answer}
 monkeypatch.setattr(server.chatgpt_tasks,'submit',fake_submit)
 monkeypatch.setattr(server.chatgpt_tasks,'complete',fake_complete)
 headers={'X-Exodia-Client':'exodia-dashboard'}
 with TestClient(server.app) as client:
  r=client.post('/api/command/tasks',headers=headers,json={
   'agent_id':'kiko','model_choice':'chatgpt','prompt':'What are three design ideas?'})
  assert r.status_code==201,r.text
  task=r.json();assert task['state']=='opening'
  for _ in range(70):
   latest=next(x for x in client.get('/api/command/tasks').json()['tasks'] if x['id']==task['id'])
   if latest['state']=='awaiting_operator':break
   time.sleep(.018)
  assert latest['state']=='awaiting_operator',latest
  assert latest['answer']==''
  assert called[0]==('submit',task['id'],'What are three design ideas?')
  assert client.get('/api/command/tasks').json()['automatic_extraction']['chatgpt'] is False
  result=client.post('/api/command/tasks/'+task['id']+'/response',headers=headers,json={
   'answer':'Three personally imported ideas'})
  assert result.status_code==200,result.text
  assert result.json()['state']=='answered'
  assert result.json()['answer']=='Three personally imported ideas'
  assert called[1]==('complete',task['id'],'Three personally imported ideas')
  assert client.post('/api/command/tasks/'+task['id']+'/cancel',headers=headers).status_code==409
