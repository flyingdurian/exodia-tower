"""Actual FastAPI + Chromium checks for Albedo technical-movement stage.

No synthetic character is presented as released art, and no signed-in provider is needed.
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

@pytest.mark.skipif(os.getenv('EXODIA_VISUAL_QA')!='1',reason='Real Chromium browser gate runs in CI')
def test_command_chibi_movement_and_live_status_desktop_mobile():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen([sys.executable,'main.py'],cwd=ROOT,env={**os.environ,'PORT':'8915'},
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        proof=ROOT/'app_data'/'qa_chibi';proof.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for attempt in range(90):
                    try:
                        if (await client.get('http://127.0.0.1:8915/api/build-info',timeout=.8)).status_code==200:break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError('Chibi QA app did not become ready')
            async with async_playwright() as p:
                opts={'headless':True,'args':['--no-sandbox']}
                if os.getenv('EXODIA_LOCAL_CHROMIUM'):
                    opts['executable_path']=os.environ['EXODIA_LOCAL_CHROMIUM']
                browser=await p.chromium.launch(**opts)
                try:
                    desktop=await browser.new_page(viewport={'width':1440,'height':960})
                    errors=[];desktop.on('pageerror',lambda exc:errors.append(str(exc)))
                    await desktop.goto('http://127.0.0.1:8915/',wait_until='domcontentloaded')
                    await desktop.wait_for_function("() => document.querySelector('#chibiOperations')?.dataset.ready==='1'",timeout=15000)
                    await desktop.wait_for_function("() => document.querySelector('#buildShortSha')?.textContent!=='unknown' || document.querySelector('#buildBadge')?.textContent.includes('unknown')",timeout=15000)
                    info=await (await desktop.request.get('http://127.0.0.1:8915/api/build-info')).json()
                    assert await desktop.locator('#buildBadge').inner_text()==info['label']
                    assert await desktop.locator('#buildChannel').inner_text()==info['channel']
                    assert await desktop.locator('#buildShortSha').inner_text()==info['short_sha']
                    assert '40 ART FRAMES PENDING' in await desktop.locator('#chibiArtStatus').inner_text()
                    assert await desktop.locator('#chibiFrame').is_hidden()
                    assert await desktop.locator('#chibiMarker').is_visible()
                    assert await desktop.locator('#summaryState').inner_text()
                    assert await desktop.locator('#summaryProvider').inner_text()
                    # Simulate *public* task status events: no provider automation or auth side effects.
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{state:'idle',agentId:'kiko'}}))")
                    await desktop.locator('.chibi-test-controls summary').click()
                    await desktop.locator('[data-chibi-go="terminal"]').click()
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='terminal' && window.__exodiaChibiRuntime?.controller.mode==='walk'",timeout=5000)
                    first=await desktop.locator('#chibiActor').evaluate('el => el.style.left')
                    await desktop.wait_for_function("first => document.querySelector('#chibiActor').style.left !== first",arg=first,timeout=3000)
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.arrived===true",timeout=8000)
                    assert await desktop.locator('#chibiActor').get_attribute('data-motion')=='idle'
                    assert 'TERMINAL' in await desktop.locator('#chibiZoneState').inner_text()
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{state:'answered',agentId:'kiko'}}))")
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='result'",timeout=3000)
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{state:'cancelled',agentId:'kiko'}}))")
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='home'",timeout=3000)
                    # Switching companions must never show Albedo on Riven's stage.
                    await desktop.locator('#companion').select_option('router')
                    await desktop.wait_for_function("() => document.querySelector('#chibiActor').hidden",timeout=3000)
                    # Polling a still-running Albedo task must never restore her
                    # chibi while the operator has selected another companion.
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{state:'running',agentId:'kiko'}}))")
                    assert await desktop.locator('#chibiActor').is_hidden()
                    await desktop.locator('#companion').select_option('kiko')
                    await desktop.wait_for_function("() => !document.querySelector('#chibiActor').hidden",timeout=3000)
                    assert not errors,errors
                    await desktop.screenshot(path=str(proof/'operations_albedo_chibi_DESKTOP.png'),full_page=True)
                    mobile=await browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                    await mobile.goto('http://127.0.0.1:8915/',wait_until='domcontentloaded')
                    await mobile.wait_for_function("() => document.querySelector('#chibiOperations')?.dataset.ready==='1'",timeout=15000)
                    assert await mobile.locator('#summaryAgent').count()==1
                    assert await mobile.locator('#chibiMarker').is_visible()
                    assert 'MOTION PROOF' in await mobile.locator('#chibiArtStatus').inner_text()
                    size=await mobile.evaluate("() => ({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth})")
                    assert size['scroll']<=size['viewport']+10,size
                    await mobile.screenshot(path=str(proof/'operations_albedo_chibi_MOBILE.png'),full_page=True)
                finally:await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=6)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    asyncio.run(run())
