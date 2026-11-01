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
