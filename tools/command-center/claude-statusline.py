#!/usr/bin/env python3
"""Claude Code status line that also records the subscription's real limit readings for the command center.

Claude Code runs this after each reply and passes session JSON on stdin. For Pro, Max and Ultra subscribers that JSON carries
`rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage` 0-100 and `resets_at` in epoch seconds): the only place the
plan's limit can be READ rather than estimated. This script saves those numbers, with a short history for a burn rate, to
~/.cache/quiet-money/claude-limits.json and prints one status line. It reads stdin and writes that one file; nothing else.
Standard library only, so the system python3 runs it. Install (user settings, ~/.claude/settings.json):
    "statusLine": {"type": "command", "command": "python3 ~/quiet-money/tools/command-center/claude-statusline.py"}
"""
import json
import os
import sys
import tempfile
import time

OUT = os.path.expanduser(os.environ.get("QM_CLAUDE_LIMITS", "~/.cache/quiet-money/claude-limits.json"))
KEEP = 80          # samples per window
MIN_GAP = 60       # seconds between kept samples, unless the percentage moved


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return 0
    rl = d.get("rate_limits") or {}
    now = time.time()
    parts = [f"[{(d.get('model') or {}).get('display_name') or '?'}]"]
    ctx = (d.get("context_window") or {}).get("used_percentage")
    if ctx is not None:
        parts.append(f"ctx {ctx:.0f}%")
    windows = {}
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        w = rl.get(key) or {}
        if isinstance(w.get("used_percentage"), (int, float)):
            windows[key] = {"used_percentage": float(w["used_percentage"]), "resets_at": w.get("resets_at")}
            parts.append(f"{label} {w['used_percentage']:.0f}%")
    if windows:
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        doc = {"t": now, "source": "Claude Code status line input (rate_limits)", "version": d.get("version"), "windows": {}}
        for key, w in windows.items():
            prev = (old.get("windows") or {}).get(key) or {}
            samples = [s for s in prev.get("samples") or [] if prev.get("resets_at") == w["resets_at"]]     # a new window starts a new history
            if not samples or now - samples[-1][0] >= MIN_GAP or samples[-1][1] != w["used_percentage"]:
                samples.append([round(now), w["used_percentage"]])
            doc["windows"][key] = {**w, "samples": samples[-KEEP:]}
        for key, prev in (old.get("windows") or {}).items():     # a window missing from this reply keeps its last reading and its own time
            if key not in doc["windows"]:
                doc["windows"][key] = {**prev, "stale_since": prev.get("stale_since") or old.get("t")}
        try:
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUT), prefix=".claude-limits-")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            os.replace(tmp, OUT)
        except OSError:
            pass
    print(" · ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
