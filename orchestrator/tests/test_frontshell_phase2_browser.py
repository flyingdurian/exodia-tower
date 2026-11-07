"""Phase 2 real FastAPI + Chromium: responsive telemetry, safe console, layout restore.

Only GET read-model snapshots and a local event WebSocket. No provider
dispatch, SQLite mutation or production art registration is permitted here.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.getenv("EXODIA_VISUAL_QA")!="1",
                    reason="Chromium Phase 2 contract runs in CI")
def test_frontshell_phase2_telemetry_terminal_layout_and_persistence():
    async def run():
        from playwright.async_api import async_playwright
        port="8957"
        proc=subprocess.Popen([sys.executable,"main.py"],cwd=ROOT,
                              env={**os.environ,"PORT":port},
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        host=f"http://127.0.0.1:{port}"
        proof=ROOT/"app_data/qa_frontshell_phase2"
        proof.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(110):
                    try:
                        if (await client.get(host+"/api/build-info",timeout=.8)
                            ).status_code==200:break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.2)
                else:raise AssertionError("Phase 2 visual QA host unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True,
                                                args=["--no-sandbox"])
                try:
                    for width,height,name in [
                        (1440,960,"desktop"),
                        (1024,768,"tablet"),
                        (390,844,"mobile")
                    ]:
                        page=await browser.new_page(
                            viewport={"width":width,"height":height},
                            is_mobile=name=="mobile",has_touch=name=="mobile")
                        errors=[];writes=[]
                        page.on("pageerror",lambda error:errors.append(str(error)))
                        page.on("request",lambda req:(
                            writes.append((req.method,req.url)) if
                            req.method not in ("GET","HEAD","OPTIONS") else None
                        ))
                        try:
                            await page.goto(host+"/",wait_until="domcontentloaded")
                            await page.wait_for_function(
                                "() => document.querySelector('#fsTelemetry')?.dataset.ready==='1'",
                                timeout=20000)
                            await page.wait_for_function(
                                "() => !!window.__exodiaPhase2Layout && "
                                "!!window.__exodiaPhase2Telemetry && "
                                "document.querySelector('#chibiOperations')?.dataset.ready==='1'",
                                timeout=18000)
                            await page.wait_for_function(
                                "() => document.querySelector('#fsTelemetry')?.dataset.link==='connected'",
                                timeout=15000)
                            assert await page.locator(".fs-provider-card").count()==4
                            for provider in ["chatgpt","gemini","deepseek","ollama"]:
                                tile=page.locator(
                                    f'.fs-provider-card[data-provider="{provider}"]')
                                assert await tile.is_visible()
                                assert await tile.locator(".fs-chart-trace").count()==1
                                assert await tile.locator(".fs-socket-badge").inner_text()\
                                    =="EVENTS LIVE"
                                assert await tile.locator(".fs-provider-session").inner_text()
                                assert await tile.locator(".fs-active-count").inner_text()
                            assert "NOT verified" in (
                                await page.locator(".fs-telemetry-note").inner_text())
                            summary=await page.evaluate("""() => ({
                              providerWs:window.__exodiaPhase2Telemetry.summary().
                                remoteProviderSocketsVerified,
                              link:window.__exodiaPhase2Telemetry.summary().link
                            })""")
                            assert summary=={"providerWs":False,"link":"connected"}
                            await page.screenshot(
                                path=str(proof/f"phase2_{name}_overview.png"),
                                full_page=True)

                            # A deterministic intercepted GET updates the real
                            # stream without creating or modifying SQLite tasks.
                            async def stub_tasks(route):
                                await route.fulfill(
                                    status=200,content_type="application/json",
                                    body=json.dumps({"tasks":[
                                        {"id":"qa-read-only","provider":"chatgpt",
                                         "state":"running"}
                                    ]}))
                            await page.route("**/api/command/tasks",stub_tasks)
                            await page.locator("#fsTelemetryRefresh").click()
                            await page.wait_for_function(
                                "() => document.querySelector("
                                "'.fs-provider-card[data-provider=chatgpt] .fs-active-count')"
                                "?.textContent==='1'",timeout=12000)
                            line=await page.locator(
                                ".fs-provider-card[data-provider=chatgpt] "
                                ".fs-chart-trace").get_attribute("d")
                            assert line and "L" in line, line
                            assert await page.evaluate(
                                "() => window.__exodiaPhase2Telemetry."
                                "summary().remoteProviderSocketsVerified") is False
                            await page.unroute("**/api/command/tasks")

                            # Terminal history and syntax highlighting are
                            # browser-only; unsupported shell commands fail.
                            await page.locator("#fsTerminalToggle").click()
                            assert await page.locator("#fsOperatorTerminal").evaluate(
                                "(el) => el.open")
                            entry=page.locator("#fsTerminalInput")
                            await entry.fill("providers")
                            assert await page.locator(
                                "#fsTerminalSyntax .fs-token-keyword").count()==1
                            await entry.press("Enter")
                            assert await page.locator("#fsOperatorTerminal").get_attribute(
                                "data-last-command")=="providers"
                            assert "No individual provider WebSocket" in (
                                await page.locator("#fsTerminalLog").inner_text())
                            await entry.press("ArrowUp")
                            assert await entry.input_value()=="providers"
                            await entry.press("ArrowDown")
                            assert await entry.input_value()==""
                            await entry.fill("rm -rf /")
                            await entry.press("Enter")
                            assert await page.locator("#fsOperatorTerminal").get_attribute(
                                "data-last-command")=="rejected"
                            assert "only allowlisted" in (
                                await page.locator("#fsTerminalStatus").inner_text()).lower()
                            await page.locator('[data-terminal-quick="status"]').click()
                            assert "Production release: DISABLED" in (
                                await page.locator("#fsTerminalLog").inner_text())

                            # Reorder, minimize, expand and refresh (browser local).
                            await page.locator(
                                '.hero-col [data-layout-action="left"]').click()
                            order=await page.evaluate(
                                "() => window.__exodiaPhase2Layout.layout.order")
                            assert order==["hero","output","control"],order
                            await page.locator(
                                '.control-col [data-layout-action="minimize"]').click()
                            assert await page.locator("#dispatch").is_hidden()
                            await page.locator(
                                '.control-col [data-layout-action="minimize"]').click()
                            assert await page.locator("#dispatch").is_visible()
                            await page.locator(
                                '.hero-col [data-layout-action="expand"]').click()
                            assert await page.locator(".output-col").is_hidden()
                            await page.locator(
                                '.hero-col [data-layout-action="expand"]').click()
                            assert await page.locator(".output-col").is_visible()
                            await page.reload(wait_until="domcontentloaded")
                            await page.wait_for_function(
                                "() => !!window.__exodiaPhase2Layout && "
                                "document.querySelector('#fsTelemetry')?.dataset.ready==='1'",
                                timeout=18000)
                            assert await page.evaluate(
                                "() => window.__exodiaPhase2Layout.layout.order"
                            )==["hero","output","control"]
                            await page.locator("#fsLayoutReset").click()
                            assert await page.evaluate(
                                "() => window.__exodiaPhase2Layout.layout.order"
                            )==["output","hero","control"]
                            geom=await page.evaluate("""() => ({
                              content:document.documentElement.clientWidth,
                              scroll:document.documentElement.scrollWidth
                            })""")
                            assert geom["scroll"]<=geom["content"]+5,geom
                            assert not writes,writes
                            assert not errors,errors
                            await page.screenshot(
                                path=str(proof/f"phase2_{name}_reset.png"),
                                full_page=True)
                        finally:
                            await page.close()
                finally:await browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=7)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=5)
    asyncio.run(run())
