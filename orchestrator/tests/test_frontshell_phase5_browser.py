"""Phase 5 actual Chromium: directional gaze, keyboard route, reduced motion, and art lock."""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="Chromium QA gate")
def test_chibi_polish_keyboard_idle_and_technical_art_lock():
    async def run():
        from playwright.async_api import async_playwright
        port="8961"
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":port,"WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        host=f"http://127.0.0.1:{port}"
        out=ROOT/"app_data/qa_frontshell_phase5"
        out.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        if (await client.get(host+"/api/build-info",timeout=.8)).status_code==200:
                            break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError("Chibi polish host unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for width,height,name,reduced in [
                        (1440,900,"desktop",False),
                        (1024,768,"tablet",False),
                        (390,844,"mobile_reduced",True)
                    ]:
                        page=await browser.new_page(viewport={"width":width,"height":height},
                            reduced_motion="reduce" if reduced else "no-preference")
                        errors=[];writes=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.on("request",lambda r:writes.append((r.method,r.url))
                            if r.method not in ("GET","HEAD","OPTIONS") else None)
                        await page.goto(host+"/",wait_until="domcontentloaded")
                        await page.wait_for_function(
                            "()=>document.querySelector('#chibiOperations')?.dataset.ready==='1'",
                            timeout=16000)
                        assert await page.locator("#chibiFrame").is_hidden()
                        assert "PENDING" in await page.locator("#chibiArtStatus").inner_text()
                        assert await page.locator("#chibiRouteLine").count()==1
                        assert await page.locator("#chibiActivityReadout").count()==1
                        runtime=await page.evaluate("""() => ({
                          art:window.__exodiaChibiRuntime.controller.manifest.asset_status,
                          released:window.__exodiaChibiRuntime.controller.manifest.production_release_enabled,
                          heading:window.__exodiaChibiRuntime.controller.heading
                        })""")
                        assert runtime["art"]=="pending_production_frames"
                        assert runtime["released"] is False
                        if reduced:
                            assert await page.locator("#chibiMotionToggle").get_attribute(
                                "aria-pressed")=="false"
                        else:
                            before=await page.evaluate(
                                "() => window.__exodiaChibiRuntime.controller.position.x")
                            await page.locator("#chibiFloor").focus()
                            await page.keyboard.press("ArrowRight")
                            await page.wait_for_function(
                                "before => window.__exodiaChibiRuntime.controller.target.x>before",
                                arg=before,timeout=3500)
                            assert await page.locator("#chibiRouteLine").get_attribute("d")
                            await page.evaluate("""() => {
                               const r=window.__exodiaChibiRuntime;
                               r.controller.finish();
                               r.choreography.setBehavior('success');
                               r.choreography.tick(1.1);
                               r.controller.faceIdle(r.choreography.snapshot().heading);
                             }""")
                            assert await page.evaluate(
                                "() => window.__exodiaChibiRuntime.choreography.snapshot().artReleased"
                            ) is False
                        assert await page.locator("#chibiFrame").is_hidden()
                        geometry=await page.evaluate("""() => ({
                          width:document.documentElement.clientWidth,
                          scroll:document.documentElement.scrollWidth})""")
                        assert geometry["scroll"]<=geometry["width"]+5,geometry
                        assert not errors,errors
                        assert not writes,writes
                        await page.screenshot(
                            path=str(out/f"phase5_{name}.png"),full_page=True)
                        await page.close()
                finally:await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=6)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    asyncio.run(run())
