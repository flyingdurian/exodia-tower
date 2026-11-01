import asyncio,base64
import pytest
from app.automation.gemini_media import (
 media_intent,validate_bytes,await_media_answer,store_media,MediaCaptureError
)
def test_media_intents():
 assert media_intent('Generate an image of a blue cottage')
 assert media_intent('Draw me a blue dragon')
 assert media_intent('Create a 6 second video clip of a kite')
 assert not media_intent('Summarize this text')
 assert not media_intent('What is the TSLA price?')
def test_content_signature():
 assert validate_bytes(b'\x89PNG\r\n\x1a\nhello','image')=='.png'
 assert validate_bytes(b'\x00\x00\x00\x18ftypisom000','video')=='.mp4'
 with pytest.raises(MediaCaptureError):validate_bytes(b'notimage','image')
class FakeLocator:
 def __init__(self,p):self.p=p;self.last=self
 async def count(self):return self.p.count
 async def inner_text(self,timeout=5000):return self.p.text
 async def is_visible(self):return self.p.generating
class FakePage:
 def __init__(self):
  self.media=[{'kind':'image','src':'https://example.com/old.png'}]
  self.count=1;self.text='old';self.generating=False
  self.calls=0
 def locator(self,selector):return FakeLocator(self)
 async def evaluate(self,script,args=None):
  self.calls+=1
  if args:
   return {'base64':base64.b64encode(b'\x89PNG\r\n\x1a\nhello').decode(),
           'type':'image/png'}
  if self.calls>=2:
   return self.media+[{'kind':'image','src':'blob:generated','width':512,'height':512}]
  return self.media
def test_media_first_result_without_text_is_accepted_and_saved(tmp_path):
 async def run():
  page=FakePage()
  result=await await_media_answer(page,text_selector='message-content',
   stop_selector='#stop',baseline=page.media,baseline_count=1,baseline_text='old',
   timeout=.4,stable=.02,poll=.006)
  assert result.answer==''
  assert len(result.media)==1
  stored=await store_media(page,result.media,tmp_path)
  assert stored[0]['kind']=='image'
  assert stored[0]['url'].startswith('/artifacts/')
  assert list(tmp_path.glob('*.png'))
 asyncio.run(run())
def test_old_media_is_not_reported_as_new():
 async def run():
  p=FakePage()
  async def same(script,args=None):return p.media
  p.evaluate=same
  with pytest.raises(MediaCaptureError):
   await await_media_answer(p,text_selector='message-content',
    stop_selector='#stop',baseline=p.media,baseline_count=1,baseline_text='old',
    timeout=.06,poll=.005,stable=.01)
 asyncio.run(run())
