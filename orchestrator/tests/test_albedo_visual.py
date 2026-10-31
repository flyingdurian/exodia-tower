"""Browser-level Albedo motion acceptance smoke: actual pixels change, not just labels.

Run locally: EXODIA_VISUAL_QA=1 python -m pytest tests/test_albedo_visual.py -q
Screenshots are saved to app_data/qa_albedo (untracked).
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]
PORT=8897

@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="requires installed Playwright Chromium")
def test_albedo_real_frames_in_browser():
    async def run():
        from playwright.async_api import async_playwright
        env={**os.environ,"PORT":str(PORT),"HOST":"127.0.0.1","WEB_SESSIONS_ENABLED":"false"}
        server=subprocess.Popen([sys.executable,"main.py"],cwd=str(ROOT),env=env,
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        images=ROOT/"app_data"/"qa_albedo"
        images.mkdir(parents=True,exist_ok=True)
        try:
            alive=False
            async with httpx.AsyncClient() as c:
                for _ in range(75):
                    if server.poll() is not None:break
                    try:
                        r=await c.get(f"http://127.0.0.1:{PORT}/",timeout=.75)
                        if r.status_code==200:alive=True;break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.15)
            assert alive,"Local Exodia server didn't start"
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    page=await browser.new_page(viewport={"width":1600,"height":980})
                    await page.goto(f"http://127.0.0.1:{PORT}/",wait_until="domcontentloaded")
                    await page.wait_for_selector('.mood[data-mood="excited"]',timeout=15000)
                    errors=[]
                    page.on('pageerror',lambda err:errors.append(str(err)))
                    page.on('console',lambda msg:errors.append('console: '+msg.text) if msg.type=='error' else None)
                    await page.locator('.mood[data-mood="excited"]').click()
                    try:
                        await page.wait_for_function(
                          "()=>{const c=document.querySelector('#albedoRig');return c && !c.hidden}",
                          timeout=17000)
                    except Exception as exc:
                        await page.screenshot(path=str(images/'motion_failed.png'),full_page=True)
                        diagnostics=await page.evaluate("""async () => ({
                          feedback:document.querySelector('#feedback')?.innerText,
                          playback:document.querySelector('#playbackInfo')?.innerText,
                          rigHidden:document.querySelector('#albedoRig')?.hidden,
                          videoHidden:document.querySelector('#albedoVideo')?.hidden,
                          mood:document.querySelector('#moodLabel')?.innerText,
                          motion:window.__exodiaMotionDebug?.(),
                          sources:await Promise.all(['/assets/artwork/kiko_prime/manifest.json',
                            '/assets/rigs/kiko.json','/assets/artwork/kiko_prime/head.webp',
                            '/assets/artwork/kiko_prime/torso.webp'].map(async u=>{
                              try{return [u,(await fetch(u)).status]}catch(e){return [u,String(e)]}
                            }))
                        })""")
                        raise AssertionError(
                            f"Motion engine never activated: {diagnostics}, javascript errors={errors}"
                        ) from exc
                    canvas=page.locator('#albedoRig')
                    script="""canvas=>{const c=canvas.getContext('2d'),d=c.getImageData(0,0,canvas.width,canvas.height).data;
                      let nonzero=0,hash=0;for(let i=0;i<d.length;i+=137){if(d[i+3]>0)nonzero++;hash=(hash*33+(d[i]||0)+(d[i+1]||0)*2+(d[i+2]||0)*3+(d[i+3]||0)*5)>>>0;}
                      return {hash,nonzero};}"""
                    await page.wait_for_timeout(420)
                    first=await canvas.evaluate(script)
                    await page.screenshot(path=str(images/'excited_early.png'),full_page=False)
                    await page.wait_for_timeout(520)
                    later=await canvas.evaluate(script)
                    await page.screenshot(path=str(images/'excited_late.png'),full_page=False)
                    assert first["nonzero"]>1000,"Character rig rendered no meaningful pixels"
                    assert later["nonzero"]>1000,"Character vanished while animating"
                    assert first["hash"]!=later["hash"],"Character pixels remained static; effect-only animation rejected"
                    await page.locator('.mood[data-mood="sleeping"]').click()
                    await page.wait_for_timeout(500)
                    sleep=await canvas.evaluate(script)
                    await page.screenshot(path=str(images/'sleeping.png'),full_page=False)
                    assert sleep["hash"]!=later["hash"],"Sleeping state did not visibly change character"
                    assert await page.locator('#moodLabel').inner_text()=="SLEEPING"
                finally:await browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=4)
            except subprocess.TimeoutExpired:server.kill()
    asyncio.run(run())
