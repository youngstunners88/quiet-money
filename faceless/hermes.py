"""Hermes agent status for the command center: version, gateway and the newest sessions. Reads only.

The command center is a projection, so this module never starts, stops or messages Hermes. It reads the installed version and gateway
state from the CLI and the session list from `~/.hermes/state.db`, opened read-only. Session *content* is never read; only the label,
source, model, timestamps and message count are shown.

Nothing here is a health claim beyond what the CLI and the database say. If Hermes is not installed, `build()` returns None and the page
says "source missing" instead of drawing a zero.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "~/.hermes/state.db, hermes --version, hermes gateway status"
_CACHE: dict[str, tuple[float, dict | None]] = {}
_TTL = 15.0


def home() -> Path:
    return Path(os.environ.get("QM_HERMES_HOME") or (Path.home() / ".hermes")).expanduser()


def _run(args: list[str], timeout: float = 8.0) -> str | None:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (r.stdout or "") + (r.stderr or "")
    return text.strip() or None


def _parse_version(text: str | None) -> dict:
    """'Hermes Agent v0.21.6+777.g71d34ba (2026.9.24) · stable · local 71d34bad1045' -> fields, never guessed."""
    out = {"version": None, "release": None, "channel": None, "updateAvailable": False}
    if not text:
        return out
    first = text.splitlines()[0]
    m = re.search(r"\bv\d[\w.+-]*", first)
    if m:
        out["version"] = m.group(0)
    m = re.search(r"\(([^)]+)\)", first)
    if m:
        out["release"] = m.group(1).strip()
    for part in (p.strip() for p in first.split("·")):
        if part in ("stable", "preview", "beta"):
            out["channel"] = part
    out["updateAvailable"] = "update available" in text.lower()
    return out


def _gateway(text: str | None) -> dict:
    """The CLI's own words: running, not running, or unknown. No inference from process names."""
    if text is None:
        return {"running": None, "state": "unknown"}
    low = text.lower()
    if "not running" in low or "✗" in text:
        return {"running": False, "state": "not running"}
    if "running" in low or "✓" in text:
        return {"running": True, "state": "running"}
    return {"running": None, "state": "unknown"}


PLATFORMS = ("telegram", "discord", "whatsapp", "slack", "signal", "weixin", "matrix", "feishu", "dingtalk", "line", "email")


def messaging(h: Path) -> list[str]:
    """Which messaging platforms have a credential NAME set in ~/.hermes/.env. Only the names are looked at; no value is read into
    the result. This is how the command center knows whether a gateway that is down matters."""
    try:
        lines = (h / ".env").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    found = set()
    for line in lines:
        m = re.match(r"\s*(?:export\s+)?([A-Z][A-Z0-9_]*)=\s*\S", line)
        if not m:
            continue
        name = m.group(1).lower()
        for plat in PLATFORMS:
            if name.startswith(plat + "_") and any(w in name for w in ("token", "secret", "key", "password", "session")):
                found.add(plat)
    return sorted(found)


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    return text or None


def sessions(db: Path | None = None, limit: int = 8) -> list[dict] | None:
    """The newest sessions, read-only. None when the database is absent; [] when it holds no sessions."""
    path = Path(db or (home() / "state.db"))
    if not path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3)
    except sqlite3.Error:
        return None
    try:
        rows = con.execute(
            "select id, display_name, source, model, started_at, ended_at, message_count "
            "from sessions order by coalesce(started_at, '') desc limit ?", (limit,)
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return [{"id": str(r[0]), "name": (r[1] or "").strip() or None, "source": r[2] or None, "model": r[3] or None,
             "startedAt": _iso(r[4]), "endedAt": _iso(r[5]), "messages": r[6] or 0} for r in rows]


def build(home_dir: Path | str | None = None, run=_run) -> dict | None:
    h = Path(home_dir).expanduser() if home_dir else home()
    if not h.exists():
        return None
    key = str(h)
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    version_text = run(["hermes", "--version"])
    gateway_text = run(["hermes", "gateway", "status"])
    doc = {
        "installed": version_text is not None,
        "home": str(h),
        "desktop": (Path.home() / ".local" / "share" / "applications" / "hermes-desktop.desktop").exists(),
        **_parse_version(version_text),
        "gateway": _gateway(gateway_text),
        "messaging": messaging(h),
        "sessions": sessions(h / "state.db"),
        "launch": {"scheme": "hermes://", "command": "hermes chat", "gateway": "hermes gateway run"},
        "source": SOURCE,
    }
    _CACHE[key] = (time.monotonic(), doc)
    return doc


def summary(doc: dict | None) -> str:
    if not doc:
        return "Hermes: not found (~/.hermes)"
    g = doc.get("gateway") or {}
    return (f"Hermes {doc.get('version') or 'unknown version'} ({doc.get('channel') or 'channel unknown'}), "
            f"gateway {g.get('state') or 'unknown'}, {len(doc.get('sessions') or [])} recent session(s)")
