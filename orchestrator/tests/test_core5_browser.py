"""Actual Chromium desktop/mobile workbench QA with synthetic-only media fixtures.

Images injected here are CI test fixtures, NOT native Albedo art or a visual
quality proof. The server routes and production lockdown run unmodified.
"""
import asyncio
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
STATES=('idle','working','explaining','monitoring','pointing')
ARTIFACT=ROOT/'app_data'/'qa_core5'

def image_fixture(index):
    picture=Image.new('RGB',(1536,1920),(25+index*15,31+index*9,71+index*18))
    d=ImageDraw.Draw(picture)
    d.ellipse((400,300,1020,840),fill=(93+index*10,40+index*6,150+index*15))
    d.rectangle((220+index*25,930,1250,1670-index*38),
                outline=(200,180,230),width=35)
    d.text((550,1190),f'QA TEST {index+1}',fill='white')
    buf=BytesIO();picture.save(buf,format='PNG');return buf.getvalue()

@pytest.mark.skipif(os.getenv('EXODIA_VISUAL_QA')!='1',reason='requires Chromium')
def test_core5_live_workbench_desktop_mobile_state_and_sha():
    async def run():
        from playwright.async_api import async_playwright
        assets={state:image_fixture(i) for i,state in enumerate(STATES)}
        records={}
        for state in STATES:
            records[state]={
                'label':state.capitalize(),
                'availability':'unapproved_concept_review',
                'image_url':'/api/albedo/core5/review-assets/'+state,
                'sha256':hashlib.sha256(assets[state]).hexdigest(),
                'source_filename':state+'_CI_SYNTHETIC_NOT_ALBEDO.png',
                'source_sha256':'a'*64,'canvas':[1536,1920],
                'source_canvas':[1122,1402],
                'production_status':'pending_production_art',
                'owner_approved':False,'native_master':False,
                'measurements':{'eye_y':633.6,'shoulder_y':980,
                    'eye_delta':0,'shoulder_delta':0,
                    'head_width_px':690 if state=='working' else 614.4,
                    'numeric_provisional_pass':True}}
        fake={'schema':'exodia.core5-live-workbench/v2',
              'release_enabled':False,'mode':'review_only','state_order':list(STATES),
              'all_five_loaded':True,'production_masters_loaded':0,
              'generated_28_states':0,'states':records}
        ARTIFACT.mkdir(parents=True,exist_ok=True)
        proc=subprocess.Popen([sys.executable,'main.py'],cwd=ROOT,
            env={**os.environ,'PORT':'8898'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            ready=False
            async with httpx.AsyncClient() as client:
                for _ in range(60):
                    try:
                        if (await client.get('http://127.0.0.1:8898/core5-review',timeout=.7)).status_code==200:
                            ready=True;break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
            assert ready
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
                try:
                    for mode,viewport in [('desktop',{'width':1500,'height':960}),
                                          ('mobile',{'width':390,'height':844})]:
                        page=await browser.new_page(viewport=viewport)
                        async def route_manifest(route):
                            await route.fulfill(status=200,content_type='application/json',body=json.dumps(fake))
                        async def route_png(route):
                            name=route.request.url.rsplit('/',1)[-1]
                            if name not in assets:
                                await route.fulfill(status=404,body='missing');return
                            await route.fulfill(status=200,content_type='image/png',body=assets[name])
                        await page.route('**/api/albedo/core5/review-manifest',route_manifest)
                        await page.route('**/api/albedo/core5/review-assets/*',route_png)
                        await page.goto('http://127.0.0.1:8898/core5-review',wait_until='domcontentloaded')
                        await page.wait_for_function(
                            "() => document.querySelector('#stateTitle')?.textContent?.includes('RELAXED')",
                            timeout=15000)
                        assert await page.locator('#emptyPreview').is_hidden()\n                        base=await page.locator('#portraitFrame').bounding_box()
                        assert base is not None
                        for state in STATES:
                            await page.get_by_role('button',name=state.capitalize()).click()
                            await page.wait_for_function(
                                "v => document.querySelector('#sourceFile')?.textContent?.startsWith(v)",
                                arg=state,timeout=12000)
                            bbox=await page.locator('#portraitFrame').bounding_box()
                            assert abs(bbox['width']-base['width'])<1.1
                            assert abs(bbox['height']-base['height'])<1.1
                            assert await page.locator('#portraitFrame img').count()==2
                            assert await page.locator('#assetClass').text_content()=='UNAPPROVED · RESAMPLED CONCEPT'
                            assert await page.locator('#previewSha').text_content()==records[state]['sha256']
                        assert await page.locator('#visited').text_content()=='5 / 5 states inspected'
                        assert 'LOCKED' in await page.locator('#lockLabel').text_content()
                        assert (await page.locator('body').evaluate(
                            '(el) => el.scrollWidth')) <= viewport['width']+2
                        await page.screenshot(path=str(ARTIFACT/('core5_'+mode+'_SYNTHETIC_QA.png')),
                                              full_page=True)
                        await page.close()
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()
    asyncio.run(run())
