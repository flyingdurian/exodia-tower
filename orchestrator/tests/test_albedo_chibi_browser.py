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
                    await desktop.wait_for_function(
                        "() => document.querySelector('#model')?.options.length >= 10 && document.querySelector('#companion')?.options.length===10 && document.querySelectorAll('#providerStatus strong').length===6",
                        timeout=15000)
                    info=await (await desktop.request.get('http://127.0.0.1:8915/api/build-info')).json()
                    await desktop.wait_for_function(
                        "label => document.querySelector('#buildBadge')?.textContent === label",
                        arg=info['label'],timeout=15000)
                    assert await desktop.locator('#buildBadge').text_content()==info['label']
                    assert await desktop.locator('#buildChannel').text_content()==info['channel']
                    assert await desktop.locator('#buildShortSha').text_content()==info['short_sha']
                    assert not await desktop.locator('#developerDrawer').evaluate('(el) => el.open')
                    assert not await desktop.locator('#diagnosticText').is_visible()
                    assert await desktop.locator('#chibiOperations').is_visible()
                    # A short answer may not stretch to the height of the entire operations floor.
                    response_rect=await desktop.locator('.response').bounding_box()
                    assert response_rect and response_rect['height'] < 460, response_rect
                    assert '40 ART FRAMES PENDING' in await desktop.locator('#chibiArtStatus').inner_text()
                    assert await desktop.locator('#chibiFrame').is_hidden()
                    assert await desktop.locator('#chibiMarker').is_visible()
                    assert await desktop.locator('#summaryState').inner_text()
                    assert await desktop.locator('#summaryProvider').inner_text()
                    # Simulate *public* task status events: no provider automation or auth side effects.
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{state:'idle',agentId:'kiko'}}))")
                    await desktop.locator('#developerToggle').click()
                    assert await desktop.locator('#developerDrawer').evaluate('(el) => el.open')
                    assert await desktop.locator('#diagnosticText').is_visible()
                    await desktop.locator('.chibi-test-controls summary').click()
                    await desktop.locator('[data-chibi-go="terminal"]').click()
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='terminal' && window.__exodiaChibiRuntime?.controller.mode==='walk'",timeout=5000)
                    first=await desktop.locator('#chibiActor').evaluate('el => el.style.left')
                    await desktop.wait_for_function("first => document.querySelector('#chibiActor').style.left !== first",arg=first,timeout=3000)
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.arrived===true",timeout=8000)
                    assert await desktop.locator('#chibiActor').get_attribute('data-motion')=='idle'
                    assert 'TERMINAL' in await desktop.locator('#chibiZoneState').inner_text()
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{taskId:'qa-task',state:'answered',agentId:'kiko',updatedAt:'2026-11-04T10:00:03Z'}}))")
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='result'",timeout=3000)
                    assert await desktop.locator('#chibiBehaviorCue').inner_text() == 'Response received'
                    assert await desktop.locator('#chibiOperations').get_attribute('data-behavior') == 'success'
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{taskId:'qa-task',state:'cancelled',agentId:'kiko',updatedAt:'2026-11-04T10:00:05Z'}}))")
                    await desktop.wait_for_function("() => window.__exodiaChibiRuntime?.controller.zone==='home'",timeout=3000)
                    assert 'local cancellation' in (await desktop.locator('#chibiBehaviorCue').inner_text()).lower()
                    await desktop.evaluate("() => window.dispatchEvent(new CustomEvent('exodia:command-task',{detail:{taskId:'qa-task',state:'running',agentId:'kiko',updatedAt:'2026-11-04T10:00:04Z'}}))")
                    assert await desktop.locator('#chibiOperations').get_attribute('data-task-phase') == 'cancelled'
                    # Switching companions must never show Albedo on Riven's stage.
                    await desktop.locator('#companion').select_option('router')
                    await desktop.wait_for_function("() => document.querySelector('#chibiActor').hidden",timeout=3000)
                    # Switching selected companion must NOT erase the selected historical task.
                    if await desktop.locator('.task-item.active').count():
                        assert await desktop.locator('#summaryTask').inner_text() != 'No task selected'
                    assert await desktop.locator('#summarySelectedCompanion').inner_text() == 'Riven'
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
                    await mobile.wait_for_function(
                        "() => document.querySelector('#model')?.options.length >= 10 && document.querySelector('#companion')?.options.length===10 && document.querySelectorAll('#providerStatus strong').length===6",
                        timeout=15000)
                    await mobile.wait_for_function(
                        "() => window.__exodiaDevelopmentPortraitStage?.status === 'verified'",
                        timeout=20000)
                    assert await mobile.locator('#summaryAgent').count()==1
                    assert await mobile.locator('#summarySelectedCompanion').inner_text() == 'Albedo'
                    assert await mobile.locator('#chibiMarker').is_visible()
                    assert not await mobile.locator('#developerDrawer').evaluate('(el) => el.open')
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
