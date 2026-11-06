"""Read-only, lifecycle-managed Riven A0 candidate watcher."""
from __future__ import annotations
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from app.fleet.riven_preflight import riven_a0_preflight

class RivenA0Watcher:
    def __init__(self, root, events=None, poll_seconds=0.65, stable_polls=2):
        if poll_seconds < 0.02 or not 1 <= stable_polls <= 10:
            raise ValueError("Invalid watch cadence")
        self.root = Path(root).resolve()
        self.folder = self.root / "app_data" / "riven_a0_inbox"
        self.events = events
        self.poll_seconds = poll_seconds
        self.stable_polls = stable_polls
        self._last_signature = None
        self._stable = 0
        self._processed = None
        self._next_retry = 0.0
        self._task = None
        self._status = dict(
            watcher_state="starting", intake_status="awaiting_manual_png",
            original_sha256=None, technical_source_pass=False,
            image_bound_annotation_consistency=False,
            owner_identity_approval="pending", production_release_enabled=False,
            native_production_certified=False,
            five_state_pilot="locked_pending_exact_sha_owner_approval",
            last_checked_utc=None)

    def snapshot(self):
        return deepcopy(self._status)

    def _signature(self):
        if not self.folder.is_dir():
            return ()
        entries = []
        for item in self.folder.iterdir():
            if item.suffix.lower() == ".png" or item.name.lower().endswith(".landmarks.json"):
                stat = item.lstat()
                entries.append((item.name, stat.st_size, stat.st_mtime_ns, stat.st_mode))
        return tuple(sorted(entries))

    async def poll_once(self):
        try:
            signature = await asyncio.to_thread(self._signature)
            if signature == self._last_signature:
                self._stable += 1
            else:
                self._last_signature = signature
                self._stable = 1
            if (self._stable < self.stable_polls or
                    signature == self._processed or monotonic() < self._next_retry):
                return self.snapshot()
            previous = self._status["intake_status"]
            inspected = await asyncio.to_thread(riven_a0_preflight, self.root)
            if await asyncio.to_thread(self._signature) != signature:
                self._stable = 0
                return self.snapshot()
            self._processed = signature
            self._next_retry = 0.0
            self._status = dict(inspected,
                watcher_state="running",
                last_checked_utc=datetime.now(timezone.utc).isoformat())
            if self.events and previous != inspected["intake_status"]:
                self.events.publish("art","Riven A0 preflight status",
                                    "status:"+inspected["intake_status"])
        except asyncio.CancelledError:
            raise
        except Exception:
            previous = self._status["intake_status"]
            self._status = dict(
                watcher_state="error", intake_status="preflight_unavailable",
                original_sha256=None, technical_source_pass=False,
                image_bound_annotation_consistency=False,
                owner_identity_approval="pending", production_release_enabled=False,
                native_production_certified=False,
                five_state_pilot="locked_pending_exact_sha_owner_approval",
                last_checked_utc=datetime.now(timezone.utc).isoformat())
            self._next_retry = monotonic() + max(2.0, self.poll_seconds * 4)
            if self.events and previous != "preflight_unavailable":
                self.events.publish("alert","Riven A0 preflight unavailable","riven_a0_check")
        return self.snapshot()

    async def run(self):
        while True:
            await self.poll_once()
            await asyncio.sleep(self.poll_seconds)

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name="riven-a0-watch")

    async def stop(self):
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
