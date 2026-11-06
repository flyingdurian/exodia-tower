"""Real temporary-file tests for Riven's automatic local A0 scanner."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw

from app.api import server
from app.fleet.riven_watcher import RivenA0Watcher
from app.monitoring.logger import EventLog
from tools.riven_native_identity_gate import ROOT, PILOT_MANIFEST, LOCKED, sha256
from tools.riven_manual_dropin import POINTS, stamp_patches, template_for


@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "orchestrator"
    (root / "frontend/companions/source_masters").mkdir(parents=True)
    (root / "app/companions").mkdir(parents=True)
    (tmp_path / "assets/review/riven_pilot").mkdir(parents=True)
    shutil.copyfile(ROOT / "frontend/companions/source_masters/router.png",
                    root / "frontend/companions/source_masters/router.png")
    shutil.copyfile(ROOT / "app/companions/roster.json",
                    root / "app/companions/roster.json")
    shutil.copyfile(PILOT_MANIFEST, tmp_path / "assets/review/riven_pilot/pilot_manifest.json")
    return root


def synthetic_native_source(path):
    """Test-only colored pixels, deliberately not author-approved Riven art."""
    im = Image.new("RGB", LOCKED)
    draw = ImageDraw.Draw(im)
    for y in range(0, LOCKED[1], 64):
        for x in range(0, LOCKED[0], 64):
            draw.rectangle((x, y, x + 63, y + 63),
                           fill=((x * 3 + y) % 256, (y * 7 + x) % 256, (x + y) // 7 % 256))
    im.save(path)


async def until(predicate, timeout=6.0):
    end = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < end:
        if predicate():
            return
        await asyncio.sleep(0.025)
    raise AssertionError("Riven watcher failed to reach expected stable state")


def test_auto_detects_native_and_sidecar_changes_without_owner_approval(sandbox):
    async def run():
        event_log = EventLog()
        watch = RivenA0Watcher(sandbox, event_log, poll_seconds=0.02, stable_polls=2)
        watch.start()
        try:
            await until(lambda: watch.snapshot()["watcher_state"] == "running")
            assert watch.folder.is_dir()
            assert watch.snapshot()["intake_status"] == "awaiting_manual_png"
            candidate = watch.folder / "riven_A0_native.png"
            await asyncio.to_thread(synthetic_native_source, candidate)
            await until(lambda: watch.snapshot()["technical_source_pass"] is True)
            state = watch.snapshot()
            assert state["original_sha256"] == sha256(candidate)
            assert state["intake_status"] == "awaiting_image_bound_annotations"
            assert state["owner_identity_approval"] == "pending"
            assert state["production_release_enabled"] is False
            sidecar = candidate.with_suffix(".landmarks.json")
            assert sidecar.is_file()
            annotations = json.loads(sidecar.read_text("utf-8"))
            assert annotations["source_sha256"] == sha256(candidate)
            assert all(annotations["landmarks"][k] is None for k in POINTS)
            assert "source_authenticity_verified" not in state or (
                state["source_authenticity_verified"] is False)
            # Synthetic landmarks are geometric checks only; they do not
            # certify that the marked pixels are real human eyes.
            annotations["landmarks"] = {
                "left_iris_center": [610, 634], "right_iris_center": [902, 634],
                "left_shoulder_joint": [505, 980], "right_shoulder_joint": [1035, 980],
                "head_left": [461, 620], "head_right": [1075.4, 620],
            }
            sidecar.write_text(json.dumps(annotations), encoding="utf-8")
            await asyncio.to_thread(stamp_patches, candidate, sidecar)
            await until(lambda: watch.snapshot()["image_bound_annotation_consistency"] is True)
            assert watch.snapshot()["owner_identity_approval"] == "pending"
            with Image.open(candidate) as src:
                changed = src.copy()
            changed.putpixel((80, 80), (4, 222, 17))
            await asyncio.to_thread(changed.save, candidate)
            new_sha = sha256(candidate)
            await until(lambda: watch.snapshot()["original_sha256"] == new_sha)
            assert not watch.snapshot()["image_bound_annotation_consistency"]
            assert watch.snapshot()["production_release_enabled"] is False
            assert candidate.exists()
            serialized = json.dumps(event_log.latest(100))
            assert str(sandbox) not in serialized
            assert "riven_A0_native.png" not in serialized
        finally:
            await watch.stop()
        assert watch._task is None
    asyncio.run(run())


def test_partial_copy_recovers_when_complete(sandbox):
    async def run():
        watch = RivenA0Watcher(sandbox, poll_seconds=0.02, stable_polls=2)
        watch.start()
        try:
            candidate = watch.folder / "riven_A0_native.png"
            candidate.write_bytes(b"not a complete PNG yet")
            await until(lambda: watch.snapshot()["intake_status"] == "source_rejected")
            assert watch.snapshot()["production_release_enabled"] is False
            await asyncio.to_thread(synthetic_native_source, candidate)
            await until(lambda: watch.snapshot()["technical_source_pass"] is True)
            assert watch.snapshot()["original_sha256"] == sha256(candidate)
        finally:
            await watch.stop()
    asyncio.run(run())


def test_corrupt_policy_fails_closed_then_recovers_without_mutating_registry(sandbox):
    async def run():
        log = EventLog()
        watch = RivenA0Watcher(sandbox, log, poll_seconds=0.02, stable_polls=2)
        policy = sandbox.parent / "assets/review/riven_pilot/pilot_manifest.json"
        original = policy.read_bytes()
        watch.start()
        try:
            await until(lambda: watch.snapshot()["watcher_state"] == "running")
            manifest = json.loads(policy.read_text("utf-8"))
            manifest["production_release_enabled"] = True
            policy.write_text(json.dumps(manifest), encoding="utf-8")
            await until(lambda: watch.snapshot()["intake_status"] == "preflight_unavailable")
            assert watch.snapshot()["owner_identity_approval"] == "pending"
            assert watch.snapshot()["production_release_enabled"] is False
            assert "production_lock_changed" not in json.dumps(log.latest())
            policy.write_bytes(original)
            await until(lambda: watch.snapshot()["watcher_state"] == "running", timeout=8.0)
            assert watch.snapshot()["production_release_enabled"] is False
        finally:
            await watch.stop()
    asyncio.run(run())


def test_watcher_status_endpoint_requires_local_header(sandbox, monkeypatch):
    async def run():
        mock = RivenA0Watcher(sandbox, poll_seconds=0.02)
        monkeypatch.setattr(server, "riven_a0_watcher", mock)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url="http://testserver",
        ) as client:
            denied = await client.get("/api/fleet/riven-a0/watch-status")
            assert denied.status_code == 403
            accepted = await client.get(
                "/api/fleet/riven-a0/watch-status",
                headers={"x-exodia-client": "exodia-dashboard"},
            )
            assert accepted.status_code == 200
            payload = accepted.json()
            assert payload["intake_status"] == "awaiting_manual_png"
            assert payload["owner_identity_approval"] == "pending"
            assert payload["production_release_enabled"] is False
            assert str(sandbox) not in accepted.text
    asyncio.run(run())



def test_linked_intake_directory_does_not_scan_or_chmod_external_folder(sandbox, tmp_path):
    async def run():
        external = tmp_path / "unrelated_user_folder"
        external.mkdir()
        (external / "private_note.txt").write_text("DO_NOT_READ_USER_FILE", encoding="utf-8")
        (sandbox / "app_data").mkdir()
        link = sandbox / "app_data/riven_a0_inbox"
        try:
            link.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Filesystem cannot create directory symbolic links")
        original_mode = external.stat().st_mode
        watch = RivenA0Watcher(sandbox, poll_seconds=0.02, stable_polls=2)
        watch.start()
        try:
            await until(lambda: watch.snapshot()["watcher_state"] == "error")
            assert watch.snapshot()["original_sha256"] is None
            assert watch.snapshot()["owner_identity_approval"] == "pending"
            assert watch.snapshot()["production_release_enabled"] is False
            assert external.stat().st_mode == original_mode
            assert (external / "private_note.txt").read_text("utf-8") == "DO_NOT_READ_USER_FILE"
        finally:
            await watch.stop()
    asyncio.run(run())
