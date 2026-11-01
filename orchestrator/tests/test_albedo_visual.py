"""Acceptance: no debug cutout UI; stage changes automatically with status text."""
import asyncio,os,subprocess,sys
from pathlib import Path
import httpx,pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.skipif(os.getenv('EXODIA_VISUAL_QA')!='1',reason='requires Chromium')
def test_portrait_expression_transitions_in_browser():
 async def run():
  from playwright.async_api import async_playwright
  proc=subprocess.Popen([sys.executable,'main.py'],cwd=ROOT,
      env={**os.environ,'PORT':'8897'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  root=ROOT/'app_data'/'qa_albedo';root.mkdir(parents=True,exist_ok=True)
  try:
   ready=False
   async with httpx.AsyncClient() as c:
    for _ in range(60):
     try:
      if (await c.get('http://127.0.0.1:8897/',timeout=.7)).status_code==200:
       ready=True;break
     except httpx.HTTPError:pass
     await asyncio.sleep(.2)
   assert ready
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
    try:
     page=await browser.new_page(viewport={'width':1600,'height':980})
     # Isolate visual-state testing from leftover mutable SQLite task history.
     await page.route('**/api/command/tasks',lambda route:route.fulfill(
       status=200,content_type='application/json',body='{"tasks":[]}'))
     await page.goto('http://127.0.0.1:8897/',wait_until='domcontentloaded')
     await page.wait_for_selector('#expressionFace',state='attached',timeout=15000)
     # Without the optional expression-pack ZIP, the selected agent portrait
     # remains visible and state changes still update the expression controller.
     assert await page.locator('#expressionFace').count()==1
     assert await page.locator('#agentPortrait').count()==1
     assert await page.locator('.mood').count()==0
     assert await page.locator('#albedoRig').count()==0
     assert await page.locator('#albedoVideo').count()==0
     await page.wait_for_function("()=>document.querySelector('#expressionName')?.textContent==='Ready'",timeout=3000)
     before=await page.locator('#expressionFace').evaluate('(el)=>getComputedStyle(el).backgroundPosition')
     await page.locator('#moodLabel').evaluate("(el)=>el.textContent='SLEEPING'")
     await page.wait_for_function("()=>document.querySelector('#expressionName')?.textContent==='Resting'",timeout=4000)
     after=await page.locator('#expressionFace').evaluate('(el)=>getComputedStyle(el).backgroundPosition')
     assert before!=after
     await page.screenshot(path=str(root/'expression_transition.png'),full_page=False)
    finally:await browser.close()
  finally:
   proc.terminate()
   try:proc.wait(timeout=4)
   except subprocess.TimeoutExpired:proc.kill()
 asyncio.run(run())
