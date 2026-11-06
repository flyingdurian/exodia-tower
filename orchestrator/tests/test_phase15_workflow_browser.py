"""Live Chromium proof for manual-only EXODIA operator workflow diagnostics.

No external model, browser automation provider or social publishing is invoked.
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
                    reason="Real workflow console Chromium QA runs in CI")
def test_phase15_operator_workflow_console_desktop_mobile():
    async def run():
        from playwright.async_api import async_playwright
        proc=subprocess.Popen(
            [sys.executable,"main.py"],cwd=ROOT,
            env={**os.environ,"PORT":"8943","WEB_SESSIONS_ENABLED":"false"},
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
        )
        output=ROOT/"app_data/qa_workflows"
        output.mkdir(parents=True,exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                for _ in range(100):
                    try:
                        response=await client.get(
                            "http://127.0.0.1:8943/api/build-info",timeout=0.8)
                        if response.status_code==200:break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(.2)
                else:
                    raise AssertionError("Workflow review service unavailable")
            async with async_playwright() as p:
                browser=await p.chromium.launch(
                    headless=True,args=["--no-sandbox"])
                try:
                    desktop=await browser.new_page(
                        viewport={"width":1440,"height":900})
                    errors=[]
                    external=[]
                    desktop.on("pageerror",lambda exc: errors.append(str(exc)))
                    desktop.on("request",lambda req: (
                        external.append(req.url)
                        if not req.url.startswith("http://127.0.0.1:8943/")
                        else None))
                    await desktop.goto(
                        "http://127.0.0.1:8943/workflow-planner",
                        wait_until="domcontentloaded")
                    await desktop.wait_for_function(
                        "()=>document.querySelector('#workflowHealthStatus')?."
                        "textContent.includes('Local workflow health') || "
                        "document.querySelector('#workflowHealthStatus')?."
                        "textContent.includes('No operator workflows')",
                        timeout=15000)
                    assert await desktop.locator(
                        "#workflowOperationsPulse").is_visible()
                    await desktop.locator("#planTitle").fill(
                        "CI operator workflow · no provider dispatch")
                    await desktop.locator(
                        "#stepEditors input[name=label]").first.fill(
                        "Inspect verified local evidence")
                    await desktop.locator("#createPlan").click()
                    await desktop.wait_for_function(
                        "()=>document.querySelector('#selectedPlan h2')?."
                        "textContent.includes('CI operator workflow')",
                        timeout=12000)
                    assert await desktop.locator(
                        "#planSteps article").count()==1
                    assert "external execution disabled" in (
                        await desktop.locator("#progressStatus").inner_text())
                    assert await desktop.locator("#confirmReview").is_disabled()
                    assert "no external action" in (
                        await desktop.locator("body").inner_text()).lower() or (
                        "no tasks were sent" in
                        (await desktop.locator("#notice").inner_text()).lower())
                    await desktop.screenshot(
                        path=str(output/"phase15_workflow_desktop.png"),
                        full_page=True)
                    assert not external, external
                    assert not errors, errors
                    mobile=await browser.new_page(
                        viewport={"width":390,"height":844},
                        is_mobile=True,has_touch=True)
                    mobile_errors=[]
                    mobile.on("pageerror",lambda exc: mobile_errors.append(str(exc)))
                    await mobile.goto(
                        "http://127.0.0.1:8943/workflow-planner",
                        wait_until="domcontentloaded")
                    await mobile.wait_for_function(
                        "()=>document.querySelector('#workflowHealthStatus')?."
                        "textContent.includes('Local workflow health')",
                        timeout=15000)
                    assert await mobile.locator(
                        "#workflowOperationsPulse").is_visible()
                    assert await mobile.locator("#planForm").is_visible()
                    sizes=await mobile.evaluate(
                        "()=>({scroll:document.documentElement.scrollWidth,"
                        "visible:document.documentElement.clientWidth})")
                    assert sizes["scroll"] <= sizes["visible"]+2,sizes
                    await mobile.screenshot(
                        path=str(output/"phase15_workflow_mobile.png"),
                        full_page=True)
                    assert not mobile_errors,mobile_errors
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
