"""Phase 4 real Chromium: allowlisted local command palette and saved workspaces."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",reason="Chromium QA in CI")
def test_phase4_palette_presets_and_activity_notices():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":"8959","WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        url="http://127.0.0.1:8959"
        proof=ROOT/"app_data/qa_frontshell_phase4"
        proof.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        if (await client.get(url+"/api/build-info",timeout=.8)).status_code==200:
                            break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError("Phase 4 local server unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for width,height,name in [
                        (1440,900,"desktop"),(1024,768,"tablet"),(390,844,"mobile")
                    ]:
                        page=await browser.new_page(viewport={"width":width,"height":height})
                        errors=[];writes=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.on("request",lambda r:writes.append((r.method,r.url))
                            if r.method not in ("GET","HEAD","OPTIONS") else None)
                        await page.goto(url+"/",wait_until="domcontentloaded")
                        await page.wait_for_function(
                            "() => !!window.__exodiaPhase4Palette && "
                            "!!window.__exodiaPhase2Layout",timeout=18000)
                        assert await page.locator(".fs-palette-launch").is_visible()
                        assert await page.locator(".fs-presets-select").is_visible()
                        await page.keyboard.press("Control+k")
                        assert await page.locator("#fsOperatorPalette").evaluate("(el)=>el.open")
                        await page.locator("#fsPaletteSearch").fill("investigation")
                        assert await page.locator("#fsPaletteResults [role=option]").count()==1
                        await page.screenshot(path=str(proof/f"phase4_{name}_palette.png"),
                            full_page=True)
                        await page.locator("#fsPaletteSearch").press("Enter")
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Layout.layout.expanded")=="output"
                        assert await page.locator(".hero-col").is_hidden()
                        await page.keyboard.press("Control+k")
                        await page.locator("#fsPaletteSearch").fill("save current workspace")
                        await page.locator('[data-action="slot-save-1"]').click()
                        assert await page.evaluate("""()=>
                          window.localStorage.getItem('exodia.frontshell.presets.v1')
                            .includes('custom1')""")
                        await page.locator(".fs-presets-select").select_option("command")
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Layout.layout.expanded") is None
                        await page.locator(".fs-presets-select").select_option("custom1")
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Layout.layout.expanded")=="output"
                        await page.evaluate("""() => window.dispatchEvent(
                           new CustomEvent('exodia:command-task',{
                             detail:{taskId:'qa-error',agentId:'liu_bei',
                               state:'failed',prompt:'DO_NOT_DISPLAY_SECRET',
                               answer:'SECRET_RESPONSE'}
                           }))""")
                        assert "LIU BEI · TASK FAILED" in (
                            await page.locator("#fsOperatorNotices").inner_text())
                        assert "DO_NOT_DISPLAY_SECRET" not in (
                            await page.locator("#fsOperatorNotices").inner_text())
                        await page.reload(wait_until="domcontentloaded")
                        await page.wait_for_function(
                            "() => !!window.__exodiaPhase4Palette && "
                            "!!window.__exodiaPhase2Layout",timeout=18000)
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Layout.layout.expanded")=="output"
                        await page.locator(".fs-presets-select").select_option("command")
                        assert await page.evaluate(
                            "() => window.__exodiaPhase2Layout.layout.expanded") is None
                        assert not errors,errors
                        assert not writes,writes
                        geometry=await page.evaluate("""() => ({
                            width:document.documentElement.clientWidth,
                            scroll:document.documentElement.scrollWidth})""")
                        assert geometry["scroll"]<=geometry["width"]+5,geometry
                        await page.screenshot(path=str(proof/f"phase4_{name}_restored.png"),
                            full_page=True)
                        await page.close()
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=6)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    asyncio.run(run())
