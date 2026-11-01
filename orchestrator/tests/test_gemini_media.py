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


def test_distinct_urls_with_same_media_bytes_are_saved_once(tmp_path):
 async def run():
  page=FakePage()
  candidates=[
   {'kind':'image','src':'blob:first','width':512,'height':512},
   {'kind':'image','src':'blob:second','width':512,'height':512},
  ]
  stored=await store_media(page,candidates,tmp_path)
  assert len(stored)==1
  assert len(list(tmp_path.glob('*.png')))==1
  assert stored[0]['sha256']
 asyncio.run(run())

def test_fallback_screenshots_exact_generated_source_not_last_image(tmp_path):
 class ImageNode:
  def __init__(self,source):self.source=source
  async def screenshot(self,*,path,timeout):
   from pathlib import Path
   Path(path).write_bytes(bytes.fromhex('89504e470d0a1a0a')+self.source.encode())
 class ImageNodes:
  def __init__(self):self.sources=['blob:old','blob:new','blob:unrelated-last']
  async def evaluate_all(self,script,source):
   return self.sources.index(source) if source in self.sources else -1
  def nth(self,index):return ImageNode(self.sources[index])
 class ScreenshotPage:
  def locator(self,selector):
   assert selector=='img'
   return ImageNodes()
  async def evaluate(self,script,arg=None):
   raise RuntimeError('CORS denied generated image fetch')
 async def run():
  stored=await store_media(ScreenshotPage(),
   [{'kind':'image','src':'blob:new','width':512,'height':512}],tmp_path)
  assert len(stored)==1 and stored[0]['quality']=='preview'
  assert (tmp_path/stored[0]['url'].split('/')[-1]).read_bytes().endswith(b'blob:new')
  assert len(list(tmp_path.iterdir()))==1
 asyncio.run(run())

def test_screenshot_fallback_refuses_unmatched_image(tmp_path):
 class MissingNodes:
  async def evaluate_all(self,script,source):return -1
  def nth(self,index):raise AssertionError('must not screenshot unrelated image')
 class MissingPage:
  def locator(self,selector):return MissingNodes()
  async def evaluate(self,script,arg=None):raise RuntimeError('CORS blocked')
 async def run():
  records=await store_media(MissingPage(),
   [{'kind':'image','src':'blob:missing'}],tmp_path)
  assert records==[{'kind':'image','status':'capture_failed','reason':'RuntimeError'}]
  assert list(tmp_path.iterdir())==[]
 asyncio.run(run())
