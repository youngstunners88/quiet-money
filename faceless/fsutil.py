"""File helpers that survive a killed process.

A routine can be stopped at any moment (session limit, runner loss, a hung encoder killed by its timeout). `write_text` truncates the target first, so a
stop in the middle leaves a half-written JSON file, and a half-written job file used to crash every command that lists jobs. Write to a temp file in the
same folder and rename it over the target: a reader sees the old file or the new one, never a piece of either.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")   # dot-prefixed and .tmp: no `*.json` glob picks it up
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def read_jsonl(path: Path) -> list[dict]:
    """The JSON objects of an append-only log. A line that is cut off, not JSON, not an object, or not valid UTF-8 is skipped: one bad line (the
    kind a stopped process or a bad merge leaves) must never stop the spend ledger, the journal or a report from reading the rest."""
    import json
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out
