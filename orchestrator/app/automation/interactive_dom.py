"""Reusable DOM streaming watcher for websites that permit programmatic access.

The watcher is not enabled for consumer ChatGPT/Gemini/DeepSeek sessions.
It is intended for pages owned by the operator or explicitly allowing automation.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from time import monotonic


class DOMResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class StreamWatchConfig:
    response_selector: str
    stop_selector: str | None = None
    timeout_seconds: float = 120.0
    stable_seconds: float = 2.0
    poll_seconds: float = 0.4


async def watch_response_stream(page, config: StreamWatchConfig, *, initial_count=0, initial_text="") -> str:
    """Wait for a *new* answer and observe stable text after generation has ended.

    Unlike simple 'two equal samples', this requires evidence of a new response, so
    an older response cannot accidentally be returned before the model has started.
    """
    if not config.response_selector:
        raise ValueError("response selector is required")
    if config.timeout_seconds <= 0 or config.stable_seconds <= 0 or config.poll_seconds <= 0:
        raise ValueError("timeouts must be positive")
    started=monotonic()
    last_text=""
    stable_since=None
    new_output_seen=False
    while monotonic()-started < config.timeout_seconds:
        matches=page.locator(config.response_selector)
        count=await matches.count()
        text=(await matches.last.inner_text(timeout=5000)).strip() if count else ""
        if text and (count>initial_count or text != initial_text):
            new_output_seen=True
        generating=False
        if config.stop_selector:
            generating=await page.locator(config.stop_selector).is_visible()
        if new_output_seen and text:
            if text!=last_text:
                last_text=text
                stable_since=monotonic()
            elif stable_since is not None and not generating and monotonic()-stable_since>=config.stable_seconds:
                return text
        else:
            stable_since=None
        await asyncio.sleep(config.poll_seconds)
    raise DOMResponseError("No completed new response detected before timeout.")
