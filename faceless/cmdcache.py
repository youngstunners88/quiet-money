"""Answers of slow, rarely-changing commands (`hermes --version`, `claude --version`), kept for a while in memory and on disk.

The command center rebuilds its overview every few seconds and the Autopilot timer builds it in a fresh process every five minutes.
A version string does not change between those, and asking for it cost most of the build (two Hermes commands took nine seconds).
The cache is keyed by the resolved program path and its arguments, holds only the command's printed text, and lives in
state/tmp (gitignored). A command that fails is not cached, so a tool that was just installed is seen on the next build.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time

from faceless.config import Paths
from faceless.fsutil import write_atomic

PATH = Paths.state / "tmp" / "cmd-cache.json"
_MEM: dict[str, tuple[float, str]] = {}


def _disk() -> dict:
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run(args: list[str], ttl: float, timeout: float = 8.0) -> str | None:
    """The command's stdout+stderr, at most `ttl` seconds old. None when the program is missing or the call fails."""
    exe = shutil.which(args[0])
    if not exe:
        return None
    key, now = " ".join([exe, *args[1:]]), time.time()
    hit = _MEM.get(key)
    if hit is None:
        row = _disk().get(key)
        if isinstance(row, list) and len(row) == 2:
            hit = _MEM[key] = (float(row[0]), str(row[1]))
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    text = ((r.stdout or "") + (r.stderr or "")).strip()
    if not text:
        return None
    _MEM[key] = (now, text)
    try:
        doc = _disk()
        doc[key] = [now, text[:4000]]
        PATH.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(PATH, json.dumps(doc))
    except OSError:
        pass
    return text
