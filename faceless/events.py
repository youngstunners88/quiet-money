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

from faceless.config import Paths, redact
from faceless.fsutil import read_jsonl

JOURNAL = Paths.state / "journal.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(kind: str, actor: str = "engine", **payload) -> dict:
    event = {"ts": now_iso(), "t": round(time.time(), 3), "actor": actor, "type": kind, **payload}
    line = redact(json.dumps(event, ensure_ascii=False, default=str))   # the journal is committed publicly
    if len(line) > 3800:  # keep appends atomic
        event = {k: v for k, v in event.items() if k in ("ts", "t", "actor", "type", "job")}
        event["truncated"] = True
        line = redact(json.dumps(event, ensure_ascii=False))
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return event


def read(path: Path | None = None, kind: str | None = None) -> list[dict]:
    path = path or JOURNAL            # resolved per call so a redirected journal is honored
    return [e for e in read_jsonl(path) if kind is None or e.get("type") == kind]
