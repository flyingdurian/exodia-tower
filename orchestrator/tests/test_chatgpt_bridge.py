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
class Hidden:
 def __init__(self,page):self.page=page;self.first=self
 async def is_visible(self,timeout=650):return False
 async def click(self,timeout=12000):raise AssertionError('hidden send was clicked')
class Submit(Input):
 async def click(self,timeout=12000):
  if self.page.click_fails:raise TimeoutError('ambiguous click')
  assert self.page.focus and self.page.typed
  self.page.sent+=1
class Keys:
 def __init__(self,page):self.page=page
 async def press(self,key):self.page.pressed.append(key)
 async def insert_text(self,text):self.page.typed=text;self.page.method='insert_text'
 async def type(self,text,delay=0):self.page.typed=text;self.page.method='keyboard_type';self.page.delay=delay
class FakePage:
 def __init__(self):
  self.url='https://chatgpt.com';self.keyboard=Keys(self);self.focus=False
  self.typed='';self.sent=0;self.pressed=[];self.blocked=False;self.hide_send=False
  self.click_fails=False;self.closed=False;self.shots=0;self.method=''
  self.eval_count=0;self.stream_polls=0;self.image=None
  self.partial='This is only the first sentence of a longer reading'
  self.final_text='Completed ChatGPT answer with enough characters to accept as finished.'
 async def goto(self,url,**kwargs):self.url=url
 def locator(self,selector):
  if 'send' in selector.lower() or 'Send' in selector:
   if self.hide_send:return Hidden(self)
   return Submit(self)
  return Input(self)
 async def evaluate(self,script,arg=None):
  if isinstance(arg,str) and arg.startswith('blob:'):
   return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
  self.eval_count+=1
  if self.eval_count<=self.stream_polls:
   return {'foundText':self.partial,'candidates':[],'isGenerating':True,'stopVisible':True,
           'turnCount':0,'composerIdle':False,'finishedControls':False}
  return {'foundText':self.final_text,'candidates':[self.image] if self.image else [],
          'isGenerating':False,'stopVisible':False,
          'turnCount':0,'composerIdle':False,'finishedControls':False}
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

def _bridge(sessions):
 return ChatGPTSubmissionBridge(sessions,start_spacing=0,idle_stable_s=0.05,max_wait_s=2,poll_s=0.01)

def test_chatgpt_submit_two_isolated_tabs_and_waits_for_finished_reply(tmp_path):
 async def run():
  factory=Factory()
  sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  phases=[]
  first=await bridge.submit('first','Summarize this page',phase=phases.append)
  second=await bridge.submit('second','Explain the results')
  context=factory.contexts[0]
  assert len(context.created)==2
  assert [p.typed for p in context.created]==['Summarize this page','Explain the results']
  assert all(p.sent==1 for p in context.created)
  assert first['status']=='answered' and first['automatic_output']
  assert first['answer']==context.created[0].final_text
  assert first['submission']=='send_clicked'
  assert 'typing' in phases and 'submitting' in phases and 'waiting_for_reply' in phases
  assert all(p.closed for p in context.created)
  assert bridge.snapshot()['pending_count']==0
  assert not context.closed
  await sessions.close()
 asyncio.run(run())

def test_does_not_capture_partial_reply_while_chatgpt_is_still_writing(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   page=await original();page.stream_polls=8;return page
  ctx.new_page=make_page
  result=await bridge.submit('stream','Give me the full tarot reading')
  page=ctx.created[0]
  assert page.eval_count>8
  assert result['answer']==page.final_text
  assert page.partial not in result['answer']
  assert page.closed
  await sessions.close()
 asyncio.run(run())

def test_image_only_reply_returns_the_picture_without_requiring_text(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   page=await original()
   page.final_text=''
   page.image={'src':'blob:https://chatgpt.com/generated','width':1024,'height':1024,'index':0}
   return page
  ctx.new_page=make_page
  result=await bridge.submit('picture','Draw a picture of the moon')
  assert result['answer']=='Generated image'
  assert result['media'][0]['kind']=='image'
  assert result['media'][0]['url'].startswith('/artifacts/')
  assert ctx.created[0].closed
  await sessions.close()
 asyncio.run(run())

def test_timeout_while_generating_does_not_return_partial_text(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=ChatGPTSubmissionBridge(sessions,start_spacing=0,idle_stable_s=0.05,max_wait_s=0.12,poll_s=0.02)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   page=await original();page.stream_polls=1000;return page
  ctx.new_page=make_page
  with pytest.raises(SessionError,match='still generating|finished reply|finished long enough'):
   await bridge.submit('partial','Do not cut this off')
  assert ctx.created[0].closed
  await sessions.close()
 asyncio.run(run())

def test_submit_fails_closed_and_takes_debug_screenshot_when_composer_missing(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  async def not_ready(*args,**kwargs):return None
  bridge._visible=not_ready
  with pytest.raises(OperatorActionRequired,match='composer'):
   await bridge.submit('failed','One prompt')
  tab=factory.contexts[0].created[0]
  assert tab.sent==0 and tab.closed and tab.shots==1
  assert not bridge.tasks
  await sessions.close()
 asyncio.run(run())

def test_long_prompt_uses_insert_text_and_still_skips_output(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  prompt='Design a display. '*20
  assert len(prompt.strip())>=250
  result=await bridge.submit('long',prompt)
  page=factory.contexts[0].created[0]
  assert page.method=='insert_text' and page.typed==prompt.strip() and page.sent==1
  assert result['automatic_output'] is True and result['typing_method']=='insert_text'
  assert result['answer']==page.final_text
  await sessions.close()
 asyncio.run(run())

def test_missing_send_button_presses_enter_once_without_reading_reply(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   page=await original();page.hide_send=True;return page
  ctx.new_page=make_page
  result=await bridge.submit('enter','Review this layout')
  page=ctx.created[0]
  assert page.sent==0 and page.pressed.count('Enter')==1
  assert result['submission']=='enter_submitted'
  assert result['automatic_output'] is True
  assert page.closed
  await sessions.close()
 asyncio.run(run())

def test_ambiguous_send_is_never_retried(tmp_path):
 async def run():
  factory=Factory();sessions=MultiWebSessionManager(tmp_path,browser_factory=factory)
  bridge=_bridge(sessions)
  await sessions.initialize_one('chatgpt')
  ctx=factory.contexts[0]
  original=ctx.new_page
  async def make_page():
   p=await original();p.click_fails=True;return p
  ctx.new_page=make_page
  with pytest.raises(SessionError,match='submission/extraction failed'):
   await bridge.submit('ambiguous','Do not double send')
  assert ctx.created[0].sent==0
  assert ctx.created[0].closed
  assert ctx.created[0].shots==1
  assert bridge.snapshot()['pending_count']==0
  await sessions.close()
 asyncio.run(run())

def test_api_task_auto_submission_waits_for_finished_chatgpt_answer(monkeypatch):
 from app.api import server
 called=[]
 finished='Full finished ChatGPT reading with every card interpreted in complete sentences.'
 async def fake_submit(task_id,prompt,*,phase=None):
  called.append(('submit',task_id,prompt))
  if phase:
   for state in ('typing','submitting','waiting_for_reply'):phase(state)
  return {'status':'answered','automatic_output':True,'answer':finished,'media':[],'timings':{'total_s':2.4}}
 monkeypatch.setattr(server.chatgpt_tasks,'submit',fake_submit)
 headers={'X-Exodia-Client':'exodia-dashboard'}
 with TestClient(server.app) as client:
  r=client.post('/api/command/tasks',headers=headers,json={
   'agent_id':'kiko','model_choice':'chatgpt','prompt':'What are three design ideas?'})
  assert r.status_code==201,r.text
  task=r.json();assert task['state']=='opening'
  for _ in range(70):
   latest=next(x for x in client.get('/api/command/tasks').json()['tasks'] if x['id']==task['id'])
   if latest['state']=='answered':break
   time.sleep(.018)
  assert latest['state']=='answered',latest
  assert latest['answer']==finished
  assert called[0]==('submit',task['id'],'What are three design ideas?')
  assert client.get('/api/command/tasks').json()['automatic_extraction']['chatgpt'] is True
  assert client.post('/api/command/tasks/'+task['id']+'/cancel',headers=headers).status_code==409
