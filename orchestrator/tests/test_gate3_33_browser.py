"""Real Chromium QA for existing FastAPI 33-state review workbench.

The screenshots show honest unavailable-art states; no synthetic portrait is
promoted and no live provider is invoked.
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.getenv('EXODIA_VISUAL_QA')!='1',
                    reason='Chromium visual QA optional outside CI')
def test_33_state_workbench_desktop_and_mobile_browser():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen([sys.executable,'main.py'],cwd=ROOT,
              env={**os.environ,'PORT':'8909'},stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL)
        proof=ROOT/'app_data'/'qa_state33'
        proof.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as http:
                ready=False
                for _ in range(90):
                    try:
                        r=await http.get('http://127.0.0.1:8909/test-workbench',timeout=.8)
                        if r.status_code==200:ready=True;break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                assert ready,'local FastAPI test workbench unavailable'
            async with async_playwright() as playwright:
                browser=await playwright.chromium.launch(headless=True,
                                                          args=['--no-sandbox'])
                try:
                    page=await browser.new_page(viewport={'width':1600,'height':1000})
                    errors=[]
                    page.on('pageerror',lambda exc:errors.append(str(exc)))
                    await page.goto('http://127.0.0.1:8909/test-workbench',
                                    wait_until='domcontentloaded')
                    await page.wait_for_function(
                      "()=>window.__exodia33?.selected==='idle'",timeout=15000)
                    assert await page.locator('.state-button').count()==33
                    assert await page.locator('.state-group-heading').count()==2
                    assert await page.locator('.state-button').first.get_attribute('data-state')=='idle'
                    assert await page.locator('.state-button[data-state="idle"]').count()==1
                    assert await page.locator('.state-button[data-state="tantrum"]').count()==1
                    frame=await page.locator('#portraitFrame').bounding_box()
                    await page.locator('.state-button[data-state="angered"]').click()
                    await page.wait_for_function(
                        "()=>window.__exodia33?.selected==='angered'",timeout=7000)
                    assert await page.locator('.hero').get_attribute('data-signal')=='strain_glitch'
                    assert await page.locator('#artStatusTag').inner_text()=='PENDING_INDEPENDENT_ART'
                    missing=page.locator('.portrait-missing-layer').filter(has_text='ANGERED')
                    assert await missing.count()==1
                    assert await missing.is_visible(), 'Missing art must be visibly identified'
                    assert not await page.locator('.portrait-loading').count()
                    frame_after=await page.locator('#portraitFrame').bounding_box()
                    assert frame_after['y']+frame_after['height'] <= 960, (
                        'Desktop portrait pushed below fold by expanded state controls',frame_after)
                    assert abs(frame['height']-frame_after['height'])<1
                    assert abs(frame['width']-frame_after['width'])<1
                    await page.locator('.state-button[data-state="pointing"]').click()
                    await page.wait_for_function(
                        "()=>window.__exodia33?.selected==='pointing'",timeout=7000)
                    assert await page.locator('#gestureBeam').is_visible()
                    assert await page.evaluate('window.__exodia33.releaseEnabled') is False
                    assert await page.locator('#registryStatus').inner_text()=='33 / 33 pending production art'
                    assert not errors,errors
                    await page.screenshot(path=str(proof/'desktop_33_states_MISSING_ART.png'))
                    mobile=await browser.new_page(viewport={'width':390,'height':844},
                                                 device_scale_factor=1,
                                                 is_mobile=True,has_touch=True)
                    await mobile.goto('http://127.0.0.1:8909/test-workbench',
                                      wait_until='domcontentloaded')
                    await mobile.wait_for_function(
                        "()=>window.__exodia33?.selected==='neutral'",timeout=15000)
                    assert await mobile.locator('.state-button').count()==33
                    assert await mobile.locator('.state-group-heading').count()==2
                    await mobile.locator('.state-button[data-state="celebrating"]').click()
                    await mobile.wait_for_function(
                        "()=>window.__exodia33?.selected==='celebrating'",timeout=7000)
                    assert await mobile.locator('.hero').get_attribute('data-signal')=='triumphant_halo'
                    assert await mobile.locator('.portrait-missing-layer').filter(has_text='CELEBRATING').is_visible()
                    assert not await mobile.locator('.portrait-loading').count()
                    mobile_state=await mobile.evaluate("""() => ({
                      scrollWidth:document.documentElement.scrollWidth,
                      viewportWidth:window.innerWidth,
                      count:window.__exodia33.inspected,
                      release:window.__exodia33.releaseEnabled})""")
                    assert mobile_state['release'] is False
                    assert mobile_state['scrollWidth']<=mobile_state['viewportWidth']+8
                    await mobile.screenshot(path=str(proof/'mobile_33_states_MISSING_ART.png'),
                                            full_page=True)
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
    asyncio.run(run())
