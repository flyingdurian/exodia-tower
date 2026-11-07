"""Phase 3 real Chromium operator diagnostics and visual accessibility proof."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="Chromium QA runs in CI")
def test_phase3_live_drilldowns_and_staleness():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":"8958","WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        url="http://127.0.0.1:8958"
        output=ROOT/"app_data/qa_frontshell_phase3"
        output.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        if (await client.get(url+"/api/build-info",timeout=.8)).status_code==200:
                            break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError("Phase 3 local server failed to start")
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for width,height,name in [
                        (1440,900,"desktop"),(1024,768,"tablet"),(390,844,"mobile")
                    ]:
                        page=await browser.new_page(viewport={"width":width,"height":height})
                        errors=[]; writes=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.on("request",lambda r:writes.append(r.url)
                            if r.method not in ("GET","HEAD","OPTIONS") else None)
                        await page.goto(url+"/",wait_until="domcontentloaded")
                        await page.wait_for_function(
                            "() => !!window.__exodiaPhase3Diagnostics && "
                            "!!window.__exodiaPhase2Telemetry && "
                            "document.querySelector('#fsProviderDrilldown')",
                            timeout=18000)
                        assert await page.locator(".fs-provider-card").count()==4
                        await page.locator(".fs-provider-card[data-provider=gemini]").click()
                        assert "Gemini" in await page.locator("#fsProviderDrilldown h3").inner_text()
                        # Deliberately emit only sanitized records, no task actions.
                        await page.evaluate("""() => window.dispatchEvent(
                          new CustomEvent('exodia:frontshell-observation',{
                           detail:{observedAt:Date.now(),link:'connected',
                           tasks:[{key:'qa-phase3',provider:'gemini',state:'running',
                             agent:'liu_bei',label:'Task 01'}]}
                          }))""")
                        assert "RUNNING" in await page.locator(
                            "#fsProviderDrilldown .fs-diagnostic-item").first.inner_text()
                        await page.evaluate("""() => window.dispatchEvent(
                          new CustomEvent('exodia:frontshell-observation',{
                           detail:{observedAt:Date.now()+1000,link:'connected',
                           tasks:[{key:'qa-phase3',provider:'gemini',state:'failed',
                             agent:'liu_bei',label:'Task 01'}]}
                          }))""")
                        assert "FAILED" in await page.locator(
                            "#fsProviderDrilldown .fs-diagnostic-item").first.inner_text()
                        before=await page.evaluate(
                            "() => window.__exodiaPhase3Diagnostics.events.length")
                        assert before>=2
                        await page.evaluate("""() => window.dispatchEvent(
                          new CustomEvent('exodia:frontshell-observation',{
                           detail:{observedAt:Date.now()+2000,link:'connected',
                           tasks:[{key:'qa-phase3',provider:'gemini',state:'failed',
                             agent:'liu_bei',label:'Task 01'}]}
                          }))""")
                        assert await page.evaluate(
                            "() => window.__exodiaPhase3Diagnostics.events.length")==before
                        await page.evaluate("""() => window.dispatchEvent(
                          new CustomEvent('exodia:frontshell-link',{
                            detail:{link:'disconnected'}}))""")
                        assert "DISCONNECTED" in await page.locator(
                            ".fs-diagnostic-freshness").inner_text()
                        await page.locator(".fs-drilldown-close").click()
                        assert await page.locator(".fs-drilldown-grid").is_hidden()
                        await page.locator(".fs-provider-card[data-provider=chatgpt]").focus()
                        await page.keyboard.press("Enter")
                        assert "ChatGPT" in await page.locator("#fsProviderDrilldown h3").inner_text()
                        assert await page.locator(".fs-drilldown-grid").is_visible()
                        assert not writes,writes
                        assert not errors,errors
                        size=await page.evaluate("""() => ({
                         page:document.documentElement.clientWidth,
                         scroll:document.documentElement.scrollWidth})""")
                        assert size["scroll"]<=size["page"]+5,size
                        await page.screenshot(path=str(output/f"phase3_{name}.png"),full_page=True)
                        await page.close()
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=6)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    asyncio.run(run())
