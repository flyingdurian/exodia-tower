"""Real Chromium Frontshell visual and Albedo 8-way floor-interaction proof.

Uses only existing local FastAPI/SQLite APIs and browser-visible task metadata.
No provider/browser automation dispatched; 40 pending art frames remain hidden.
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


@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",
                    reason="Frontshell Chromium visual QA runs only in CI")
def test_frontshell_polish_and_chibi_navigation_desktop_tablet_mobile():
    async def run():
        from playwright.async_api import async_playwright
        port="8948"
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":port,"WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        output=ROOT/"app_data/qa_frontshell"
        output.mkdir(parents=True,exist_ok=True)
        host=f"http://127.0.0.1:{port}"
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        if (await client.get(host+"/api/build-info",timeout=.8)
                            ).status_code==200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(.2)
                else:
                    raise AssertionError("Frontshell QA host unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(
                    headless=True,args=["--no-sandbox"])
                try:
                    for width,height,name in [
                        (1440,960,"desktop"),(1024,768,"tablet"),
                        (390,844,"mobile")
                    ]:
                        page=await browser.new_page(viewport={
                            "width":width,"height":height},
                            is_mobile=name=="mobile",has_touch=name=="mobile")
                        errors=[]
                        writes=[]
                        page.on("pageerror",lambda exc:errors.append(str(exc)))
                        page.on("request",lambda request:(
                            writes.append((request.method,request.url))
                            if request.method not in ("GET","HEAD","OPTIONS")
                            else None))
                        try:
                            await page.goto(host+"/",wait_until="domcontentloaded")
                            await page.wait_for_function(
                                "()=>document.querySelector('#chibiOperations')?."
                                "dataset.ready==='1'",timeout=18000)
                            assert await page.locator(".frontshell-brief h1").is_visible()
                            assert await page.locator("#frontshellFocusToggle").is_visible()
                            assert await page.locator("#frontshellLiveSignal").is_visible()
                            assert await page.locator("#commandStatusStrip").is_visible()
                            assert await page.locator("#chibiOperations").is_visible()
                            assert await page.locator("#chibiFloor").is_visible()
                            assert await page.locator("[data-chibi-zone]").count()==5
                            assert "40 ART FRAMES PENDING" in (
                                await page.locator("#chibiArtStatus").inner_text())
                            assert await page.locator("#chibiFrame").is_hidden()
                            assert await page.locator("#chibiMarker").is_visible()
                            geometry=await page.evaluate("""()=>{
                              const width=document.documentElement.clientWidth;
                              return {width,
                                scroll:document.documentElement.scrollWidth,
                                grid:document.querySelector('.command-grid').
                                  getBoundingClientRect().width};
                            }""")
                            assert geometry["scroll"]<=geometry["width"]+3,geometry
                            if name=="desktop":
                                coords=await page.evaluate("""()=>{
                                  const box=s=>document.querySelector(s).
                                    getBoundingClientRect();
                                  return {left:box('.output-col').left,
                                    middle:box('.hero-col').left,
                                    right:box('.control-col').left};
                                }""")
                                assert coords["left"]<coords["middle"]<coords["right"],coords
                            else:
                                assert await page.locator("#chibiFloor").is_visible()
                            await page.screenshot(
                                path=str(output/f"frontshell_{name}.png"),
                                full_page=True)
                            await page.locator("#frontshellFocusToggle").click()
                            assert await page.locator(".app-shell").get_attribute(
                                "data-frontshell-focus")=="true"
                            assert await page.locator("#frontshellFocusToggle").get_attribute(
                                "aria-pressed")=="true"
                            assert await page.locator(".output-col").is_hidden()
                            await page.keyboard.press("Escape")
                            assert await page.locator(".app-shell").get_attribute(
                                "data-frontshell-focus")=="false"
                            assert await page.locator(".output-col").is_visible()
                            await page.locator('[data-chibi-zone="terminal"]').click()
                            assert await page.locator("#chibiActor").get_attribute(
                                "data-motion") in ("walk","idle")
                            assert (await page.locator("#chibiZoneState").inner_text())\
                                .startswith("TERMINAL")
                            await page.evaluate("""()=>{
                              window.dispatchEvent(new CustomEvent('exodia:command-task',{
                                detail:{taskId:'qa-albedo',agentId:'kiko',state:'failed',
                                updatedAt:'2026-11-06T23:50:01Z',
                                prompt:'DO_NOT_LEAK',answer:'SECRET'}
                              }));
                            }""")
                            assert await page.locator("#chibiOperations").get_attribute(
                                "data-behavior")=="failure"
                            assert "TASK NEEDS REVIEW" in (
                                await page.locator("#frontshellLiveSignal").inner_text())
                            assert "DO_NOT_LEAK" not in (
                                await page.locator("#frontshellLiveSignal").inner_text())
                            assert await page.locator("#chibiFrame").is_hidden()
                            await page.locator("#chibiMotionToggle").click()
                            assert await page.locator("#chibiMotionToggle").get_attribute(
                                "aria-pressed") in ("true","false")
                            assert not writes,writes
                            assert not errors,errors
                        finally:
                            await page.close()
                finally:
                    await browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    asyncio.run(run())
