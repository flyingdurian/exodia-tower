"""Chromium DOM smoke check for generated Gemini media in light + shadow trees."""
import asyncio,os,pytest
from app.automation.gemini_media import snapshot_media

@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="needs Playwright Chromium")
def test_generated_media_in_nested_shadow_and_light_dom():
    async def run():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                page=await browser.new_page()
                await page.set_content("""<model-response>
                  <img id="light" style="width:180px;height:140px" src="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='180'%20height='140'%3E%3C/svg%3E">
                  </model-response><generated-image id="shadow"></generated-image>""")
                await page.evaluate("""()=>{
                  const root=document.querySelector('#shadow').attachShadow({mode:'open'});
                  const img=document.createElement('img');
                  img.src="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='200'%20height='150'%3E%3C/svg%3E";
                  img.style.width='200px';img.style.height='150px';
                  root.append(img);
                }""")
                await page.wait_for_timeout(200)
                result=await snapshot_media(page)
                assert len(result)==2,result
                assert all(x['kind']=='image' for x in result)
                assert {int(x['width']) for x in result}=={180,200}
            finally:await browser.close()
    asyncio.run(run())


@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="needs Playwright Chromium")
def test_generated_image_screenshot_matches_shadow_dom_source(tmp_path):
    """Real Chromium: failed direct capture cannot select an unrelated thumbnail."""
    import struct
    from urllib.parse import quote
    from app.automation.gemini_media import store_media
    async def run():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                page=await browser.new_page()
                def svg(width,height):
                    source=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="red"/></svg>'
                    return 'data:image/svg+xml,'+quote(source)
                target=svg(180,140)
                await page.set_content('<generated-image id="shadow"></generated-image><img id="unrelated" width="320" height="210">')
                await page.evaluate("""(source) => {
                    const root=document.querySelector('#shadow').attachShadow({mode:'open'});
                    const image=document.createElement('img');
                    image.width=180;image.height=140;image.src=source;root.append(image);
                }""",target)
                await page.locator('generated-image img').wait_for(state='visible')
                await page.locator('#unrelated').evaluate('(img,src) => {img.src=src}',svg(320,210))
                await page.wait_for_function("document.querySelector('generated-image').shadowRoot.querySelector('img').complete")
                files=await store_media(page,[{'kind':'image','src':target}],tmp_path)
                assert len(files)==1,files
                assert files[0]['quality']=='preview'
                raw=(tmp_path/files[0]['url'].split('/')[-1]).read_bytes()
                assert raw[:8]==bytes.fromhex('89504e470d0a1a0a')
                assert struct.unpack('>II',raw[16:24])==(180,140)
            finally:await browser.close()
    asyncio.run(run())
