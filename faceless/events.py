"""Append-only event journal: the studio's shared log.

Every stage writes one JSON line per event. Nothing is ever rewritten, so the journal
is the audit trail for what happened, what it cost, and why a decision was taken.
Single-line appends under 4 KB are atomic on Linux, so concurrent workers are safe.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from faceless.config import Paths

JOURNAL = Paths.state / "journal.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(kind: str, actor: str = "engine", **payload) -> dict:
    event = {"ts": now_iso(), "t": round(time.time(), 3), "actor": actor, "type": kind, **payload}
    line = json.dumps(event, ensure_ascii=False, default=str)
    if len(line) > 3800:  # keep appends atomic
        event = {k: v for k, v in event.items() if k in ("ts", "t", "actor", "type", "job")}
        event["truncated"] = True
        line = json.dumps(event, ensure_ascii=False)
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return event


def read(path: Path = JOURNAL, kind: str | None = None) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if kind is None or e.get("type") == kind:
            out.append(e)
    return out
