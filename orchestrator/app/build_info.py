"""One canonical build identity for API and every EXODIA frontshell."""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess

APP_VERSION = "0.3.0"
ROOT = Path(__file__).resolve().parent.parent.parent

def build_info() -> dict:
    raw = (os.getenv("EXODIA_BUILD_SHA") or os.getenv("GITHUB_SHA") or "").strip()
    if not raw:
        try:
            result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                    capture_output=True, text=True, timeout=1, check=True)
            raw = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    commit = raw.lower() if re.fullmatch(r"[0-9a-fA-F]{40}", raw) else None
    channel = os.getenv("EXODIA_BUILD_CHANNEL", "development").strip().lower()
    if channel not in ("development", "release", "local"):
        channel = "local"
    marker = "dev" if channel == "development" else "release" if channel == "release" else "local"
    short = commit[:12] if commit else "unknown"
    return {"version": APP_VERSION, "channel": channel,
            "commit_sha": commit, "short_sha": short,
            "label": f"EXODIA v{APP_VERSION}-{marker} · {short}",
            "verified_commit": commit is not None}
