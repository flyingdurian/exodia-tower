"""Chromium proof of task-scoped ChatGPT manual handoff, with synthetic task data."""
import asyncio, json, os, subprocess, sys
from pathlib import Path
import httpx, pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.getenv('EXODIA_VISUAL_QA')!='1',reason='Requires Chromium')
def test_chatgpt_auto_submit_handoff_panel_and_single_import():
 async def run():
  from playwright.async_api import async_playwright
  env={**os.environ,'PORT':'8898'}
  server=subprocess.Popen([sys.executable,'main.py'],cwd=ROOT,
    env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  screenshots=ROOT/'app_data'/'qa_albedo'
  screenshots.mkdir(parents=True,exist_ok=True)
  try:
   ready=False
   async with httpx.AsyncClient() as client:
    for _ in range(75):
     try:
      r=await client.get('http://127.0.0.1:8898/',timeout=.7)
      if r.status_code==200:ready=True;break
     except httpx.HTTPError:pass
     await asyncio.sleep(.2)
   assert ready,'Could not start local task UI'
   async with async_playwright() as playwright:
    browser=await playwright.chromium.launch(headless=True,args=['--no-sandbox'])
    try:
     page=await browser.new_page(viewport={'width':1460,'height':940})
     captured=[]
     state={'value':'awaiting_operator'}
     errors=[]
     page.on('pageerror',lambda error:errors.append(str(error)))
     async def route_task(route):
      if route.request.method=='POST':
       captured.append(json.loads(route.request.post_data))
       state['value']='answered'
      row={'id':'demo-chatgpt','agent_id':'kiko','provider':'chatgpt',
           'prompt':'Design three futuristic displays','state':state['value'],
           'answer':'Response imported manually' if state['value']=='answered' else '',
           'sources':[],'metrics':{},'media':[]}
      body=row if route.request.method=='POST' else {'tasks':[row]}
      await route.fulfill(status=200,content_type='application/json',body=json.dumps(body))
     await page.route('**/api/command/tasks',route_task)
     await page.route('**/api/command/tasks/demo-chatgpt/response',route_task)
     await page.goto('http://127.0.0.1:8898/',wait_until='domcontentloaded')
     await page.wait_for_selector('#chatgptHandoff',state='visible',timeout=15000)
     assert await page.locator('#chatgptHandoff').is_visible()
     assert 'the current chatgpt bridge attempts automatic delivery' in (await page.locator('#chatgptHandoff').inner_text()).lower()
     await page.locator('#chatgptResultText').fill('Response imported manually')
     await page.screenshot(path=str(screenshots/'chatgpt_handoff.png'),full_page=False)
     await page.locator('#chatgptImport').click()
     await page.wait_for_function("()=>document.querySelector('#terminalStatus')?.textContent==='RESPONSE READY'",timeout=9000)
     assert captured==[{'answer':'Response imported manually'}]
     assert not errors,errors
    finally:
     await browser.close()
  finally:
   server.terminate()
   try:server.wait(timeout=4)
   except subprocess.TimeoutExpired:server.kill()
 asyncio.run(run())
