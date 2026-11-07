"""Phase 6 real Chromium release gate: responsive visual QA, offline recovery and no writes."""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="Phase 6 visual QA in CI")
def test_release_cockpit_reconnect_offline_a11y_and_visual_stability():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":"8962","WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        host="http://127.0.0.1:8962"
        proof=ROOT/"app_data/qa_frontshell_phase6"
        proof.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        if (await client.get(host+"/api/build-info",timeout=.8)).status_code==200:
                            break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError("RC host unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for w,h,name in [(1440,900,"desktop"),(1024,768,"tablet"),
                                     (390,844,"mobile")]:
                        context=await browser.new_context(viewport={"width":w,"height":h})
                        page=await context.new_page()
                        errors=[];writes=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.on("request",lambda r:writes.append((r.method,r.url))
                            if r.method not in ("GET","HEAD","OPTIONS") else None)
                        await page.goto(host+"/",wait_until="domcontentloaded")
                        await page.wait_for_function(
                            "() => !!window.__exodiaPhase6Readiness && "
                            "document.querySelector('#fsTelemetry')?.dataset.ready==='1'",
                            timeout=16000)
                        assert await page.locator("#fsReliability").is_visible()
                        assert await page.locator(".fs-release-item").count()==4
                        assert await page.locator(".fs-skip").count()==1
                        assert "NOT RELEASED" in await page.locator(
                            '.fs-release-item[data-check="art"]').inner_text()
                        assert "PENDING" in await page.locator(
                            '.fs-release-item[data-check="operator"]').inner_text()
                        assert await page.evaluate(
                            "() => window.__exodiaPhase6Readiness.health.providerAuthenticationVerified"
                        ) is False
                        assert await page.evaluate(
                            "() => window.__exodiaPhase6Readiness.health.productionArtworkReleased"
                        ) is False
                        await page.screenshot(path=str(proof/f"phase6_{name}_online.png"),
                            full_page=True)
                        # Simulate browser connectivity dropping, without any POST.
                        await context.set_offline(True)
                        await page.wait_for_function(
                            "() => document.querySelector('#fsReliability')?.dataset.freshness==='offline'",
                            timeout=12000)
                        assert "LOCAL NETWORK OFFLINE" in await page.locator(
                            '.fs-release-item[data-check="stream"]').inner_text()
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Telemetry.readiness.providerWebSocketsVerified"
                        ) is False
                        await page.screenshot(path=str(proof/f"phase6_{name}_offline.png"),
                            full_page=True)
                        await context.set_offline(False)
                        await page.wait_for_function(
                            "() => document.querySelector('#fsReliability')?.dataset.freshness!=='offline'",
                            timeout=14000)
                        await page.locator("#fsTelemetryRefresh").click()
                        await page.wait_for_function(
                            "() => document.querySelector('#fsTelemetry')?.dataset.ready==='1'",
                            timeout=15000)
                        assert await page.locator("#fsProviderDrilldown").is_visible()
                        assert await page.locator("#fsOperatorPalette").count()==1
                        size=await page.evaluate("""() => ({
                           width:document.documentElement.clientWidth,
                           scroll:document.documentElement.scrollWidth})""")
                        assert size["scroll"]<=size["width"]+5,size
                        assert not writes,writes
                        assert not errors,errors
                        await context.close()
                finally:await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=6)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    asyncio.run(run())
