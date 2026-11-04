"""Real Chromium QA for existing FastAPI 33-state review workbench.

The screenshots show real SHA-verified independent artwork when present;
unavailable-art fallback remains truthful, with no synthetic substitution.
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
                    # Live canonical build marker, not a hardcoded UI version.
                    build = await (await page.request.get(
                        'http://127.0.0.1:8909/api/build-info')).json()
                    await page.wait_for_function(
                        "() => document.querySelector('#buildBadge')?.textContent.includes('EXODIA v')",
                        timeout=6000)
                    assert await page.locator('#buildBadge').inner_text() == build['label']
                    if os.getenv('GITHUB_SHA'):
                        assert build['commit_sha'] == os.environ['GITHUB_SHA'].lower()
                    # The actual command surface uses the same backend catalog.
                    command=await browser.new_page(viewport={'width':1440,'height':960})
                    await command.goto('http://127.0.0.1:8909/',wait_until='domcontentloaded')
                    await command.wait_for_function(
                        "() => document.querySelector('#model')?.options.length >= 10",
                        timeout=15000)
                    labels=await command.locator('#model option').all_text_contents()
                    assert labels[:7] == [
                        'ChatGPT (chronos)', 'Gemini (chronos)',
                        'DeepSeek (chronos)', 'Ollama (automatic local)',
                        'ChatGPT (api) — Not configured',
                        'Gemini (api) — Not configured',
                        'DeepSeek (api) — Not configured']
                    assert await command.locator('#model').input_value()=='chatgpt'
                    for provider in ('chatgpt:api','gemini:api','deepseek:api'):
                        assert await command.locator('#model option[value="'+provider+'"]').is_disabled()
                    await command.wait_for_function(
                        "() => document.querySelector('#buildBadge')?.textContent.includes('EXODIA v')",
                        timeout=6000)
                    assert await command.locator('#buildBadge').inner_text() == build['label']
                    # Live frontshell task controls and provider/session metadata.
                    assert await command.locator('#cancelActiveTask').count()==1
                    assert await command.locator('#cancelActiveTask').is_hidden()
                    await command.wait_for_function(
                        "() => document.querySelectorAll('#providerStatus strong').length === 6",
                        timeout=10000)
                    provider_text=await command.locator('#providerStatus').inner_text()
                    assert 'Not configured' in provider_text
                    assert 'Automatic reply' not in provider_text, 'Authentication must never be inferred from capability'
                    assert await command.locator('#engineChecked').inner_text()
                    await command.screenshot(path=str(proof/'command_version_providers_DESKTOP.png'))
                    await command.close()
                    command_mobile=await browser.new_page(viewport={'width':390,'height':844},
                                                         is_mobile=True,has_touch=True)
                    await command_mobile.goto('http://127.0.0.1:8909/',wait_until='domcontentloaded')
                    await command_mobile.wait_for_function(
                        "() => document.querySelector('#model')?.options.length >= 10",
                        timeout=15000)
                    assert await command_mobile.locator('#model').input_value()=='chatgpt'
                    await command_mobile.screenshot(
                        path=str(proof/'command_version_providers_MOBILE.png'),full_page=True)
                    await command_mobile.close()
                    assert await page.locator('.state-button').count()==33
                    review_state_response=await page.request.get(
                        'http://127.0.0.1:8909/api/albedo/state33/manifest')
                    review_state_manifest=await review_state_response.json()
                    corrected=review_state_manifest.get('owner_development_review_only_count',0)==4
                    expected_target_status=('REVIEW_ONLY_OWNER_ACCEPTED_NON_NATIVE'
                                            if corrected else 'CORRECTION_REQUIRED')
                    assert await page.locator('.state-button[data-owner-review="'+expected_target_status+'"]').count()==4
                    assert await page.locator('.state-button[data-owner-review="OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT"]').count()==29
                    for target in ('angered','awaiting_command','neutral','tantrum'):
                        node=page.locator('.state-button[data-state="'+target+'"]')
                        assert await node.get_attribute('data-owner-review')==expected_target_status
                    assert await page.locator('#ownerDevelopmentStatus').count()==1
                    assert await page.locator('.state-group-heading').count()==2
                    assert await page.locator('.state-button').first.get_attribute('data-state')=='idle'
                    assert await page.locator('.state-button[data-state="idle"]').count()==1
                    assert await page.locator('.state-button[data-state="tantrum"]').count()==1
                    frame=await page.locator('#portraitFrame').bounding_box()
                    await page.locator('.state-button[data-state="angered"]').click()
                    await page.wait_for_function(
                        "()=>window.__exodia33?.selected==='angered'",timeout=7000)
                    assert await page.locator('.hero').get_attribute('data-signal')=='strain_glitch'
                    if corrected:
                        assert 'RESAMPLED, NOT NATIVE' in await page.locator('#ownerDevelopmentStatus').inner_text()
                        assert 'RESAMPLED' in await page.locator('.state-button[data-state="angered"] .detail small').inner_text()
                    else:
                        assert 'Owner approved exact design SHA' in await page.locator('#ownerDevelopmentStatus').inner_text()
                        assert 'native rerender still required' in await page.locator('#ownerDevelopmentStatus').inner_text()
                        assert 'DESIGN APPROVED' in await page.locator('.state-button[data-state="angered"] .detail small').inner_text()
                    art_response=await page.request.get(
                        'http://127.0.0.1:8909/api/albedo/state33/manifest')
                    art_manifest=await art_response.json()
                    angered=art_manifest['states']['angered']
                    if angered['image_url']:
                        assert await page.locator('#artStatusTag').inner_text()==(
                            'OWNER_ACCEPTED_DEVELOPMENT_RESAMPLED_REVIEW_ONLY'
                            if corrected else 'INDEPENDENT_ART_UNAPPROVED_REVIEW')
                        await page.wait_for_function(
                          "()=>document.querySelector('#loadStatus')?.textContent.includes('SHA-VERIFIED')",
                          timeout=15000)
                        assert await page.locator('.portrait-preview-layer[src^="blob:"]').count()>=1
                        assert angered['owner_approved'] is False
                    else:
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
                    # Exercise EVERY defined state, not just two representative
                    # buttons. All 33 must remain selectable without moving
                    # the fixed portrait stage or inventing an image.
                    state_response=await page.request.get(
                        'http://127.0.0.1:8909/api/albedo/state33/manifest')
                    state_order=(await state_response.json())['state_order']
                    assert len(state_order)==33
                    for state_name in state_order:
                        await page.locator(
                            '.state-button[data-state="'+state_name+'"]').click()
                        await page.wait_for_function(
                            "(value)=>window.__exodia33?.selected===value",
                            arg=state_name,timeout=7000)
                        assert (await page.locator('#portraitFrame').bounding_box())['width']==frame['width']
                        assert await page.locator('#stateKey').inner_text()==state_name.upper()
                    assert await page.evaluate('window.__exodia33.inspected')==33
                    await page.locator('.state-button[data-state="pointing"]').click()
                    await page.wait_for_function(
                        "()=>window.__exodia33?.selected==='pointing'",timeout=7000)
                    # Let the genuine 240ms opacity crossfade FINISH before
                    # capturing a visual proof; earlier CI screenshots froze
                    # the text at partial transparency.
                    await page.wait_for_timeout(380)
                    assert await page.locator('.portrait-display-layer').evaluate_all(
                        "(els)=>els.some(x=>Number(getComputedStyle(x).opacity)>0.98)")
                    await page.screenshot(path=str(proof/'desktop_33_states_REAL_ART.png'))
                    # Exercise the real auto-cycle scheduler for a full 1→33
                    # sequence with timers accelerated ONLY inside this QA tab.
                    # Production remains a readable 4 seconds per state.
                    auto=await browser.new_page(viewport={'width':1300,'height':850})
                    await auto.add_init_script("""(() => {
                      const original=window.setInterval.bind(window);
                      window.setInterval=(fn,delay,...args)=>
                        original(fn,delay===4000?130:delay,...args);
                    })();""")
                    await auto.goto('http://127.0.0.1:8909/test-workbench',
                                    wait_until='domcontentloaded')
                    await auto.wait_for_function(
                        "()=>window.__exodia33?.selected==='idle'",timeout=15000)
                    await auto.locator('#autoCycle').check()
                    await auto.wait_for_function(
                        "()=>window.__exodia33?.autoAdvances>=33",timeout=15000)
                    assert await auto.evaluate('window.__exodia33.autoUniqueRequested')==33
                    assert await auto.evaluate('window.__exodia33.releaseEnabled') is False
                    await auto.locator('#autoCycle').uncheck()
                    await auto.close()
                    mobile=await browser.new_page(viewport={'width':390,'height':844},
                                                 device_scale_factor=1,
                                                 is_mobile=True,has_touch=True)
                    await mobile.goto('http://127.0.0.1:8909/test-workbench',
                                      wait_until='domcontentloaded')
                    await mobile.wait_for_function(
                        "()=>window.__exodia33?.selected==='idle'",timeout=15000)
                    assert await mobile.locator('.state-button').count()==33
                    assert await mobile.locator('.state-group-heading').count()==2
                    await mobile.locator('.state-button[data-state="celebrating"]').click()
                    await mobile.wait_for_function(
                        "()=>window.__exodia33?.selected==='celebrating'",timeout=7000)
                    assert await mobile.locator('.hero').get_attribute('data-signal')=='triumphant_halo'
                    manifest_response=await mobile.request.get(
                        'http://127.0.0.1:8909/api/albedo/state33/manifest')
                    art=(await manifest_response.json())['states']['celebrating']
                    if art['image_url']:
                        assert art['art_status']=='INDEPENDENT_ART_UNAPPROVED_REVIEW'
                        assert art['owner_approved'] is False
                        await mobile.wait_for_function(
                            "()=>document.querySelector('#loadStatus')?.textContent.includes('SHA-VERIFIED')",
                            timeout=7000)
                        assert await mobile.locator('.portrait-preview-layer[src^="blob:"]').count()>=1
                        assert art['sha256']=='cc4612e7565f6659e5349fdf20d9daa9c795fbb0e9a7fab87fd45c8e9c56c08e'
                        assert 'FAIL' in await mobile.locator('#geometryVerdict').inner_text()
                        assert '(688.1, 526.9)' in await mobile.locator('#irisDetail').inner_text()
                        assert '(520.0, 861.0)' in await mobile.locator('#shoulderDetail').inner_text()
                        assert 'NOT CERTIFIED' in await mobile.locator('#headWidth').inner_text()
                    else:
                        assert await mobile.locator('.portrait-missing-layer').filter(
                            has_text='CELEBRATING').is_visible()
                    assert not await mobile.locator('.portrait-loading').count()
                    mobile_state=await mobile.evaluate("""() => ({
                      scrollWidth:document.documentElement.scrollWidth,
                      viewportWidth:window.innerWidth,
                      count:window.__exodia33.inspected,
                      release:window.__exodia33.releaseEnabled})""")
                    assert mobile_state['release'] is False
                    assert mobile_state['scrollWidth']<=mobile_state['viewportWidth']+8
                    await mobile.wait_for_timeout(380)
                    await mobile.screenshot(path=str(proof/'mobile_33_states_REAL_ART.png'),
                                            full_page=True)
                    # A fake "available" Core-Five image with invalid SHA
                    # must never be shown or silently treated as approved art.
                    from json import dumps
                    tampered=await browser.new_page(viewport={'width':1280,'height':820})
                    result=await tampered.request.get(
                        'http://127.0.0.1:8909/api/albedo/state33/manifest')
                    injected=await result.json()
                    injected['states']['idle']['art_status']='CONCEPT_REVIEW_AVAILABLE'
                    injected['states']['idle']['image_url']='/api/albedo/core5/review-assets/idle'
                    injected['states']['idle']['sha256']='a'*64
                    async def mock_manifest(route):
                        await route.fulfill(status=200,content_type='application/json',
                                            body=dumps(injected))
                    async def corrupt_png(route):
                        await route.fulfill(status=200,content_type='image/png',
                                            body=b'not-an-image-and-invalid-hash')
                    await tampered.route('**/api/albedo/state33/manifest',mock_manifest)
                    await tampered.route('**/api/albedo/core5/review-assets/idle',corrupt_png)
                    await tampered.goto('http://127.0.0.1:8909/test-workbench',
                                        wait_until='domcontentloaded')
                    await tampered.wait_for_function(
                        "()=>document.querySelector('#artStatusTag')?.textContent==='ASSET INTEGRITY REJECTED'",
                        timeout=10000)
                    assert 'IMAGE REJECTED' in await tampered.locator('#loadStatus').inner_text()
                    assert await tampered.locator('.portrait-missing-layer').filter(
                        has_text='IDLE').is_visible()
                    assert await tampered.evaluate('window.__exodia33.releaseEnabled') is False
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
    asyncio.run(run())
