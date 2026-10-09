"""Composio: managed OAuth + 1,500 app toolkits (YouTube, TikTok, Instagram, Drive, Gmail...) behind one session.

The studio is single-tenant, so one stable Composio user id (studio.toml [composio].user_id) owns every
connection. Tools always run through a session (`session.execute`), never the legacy direct path.
Connections are made once with a Connect Link and persist for every later run, including CI.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache

from faceless import config, events, ledger
from faceless.providers import ProviderError, ProviderUnavailable


def _ensure_key() -> None:
    # The SDK reads COMPOSIO_API_KEY; some environments store the same project key as COMPOSIO_API.
    if not os.environ.get("COMPOSIO_API_KEY"):
        alias = config.env("COMPOSIO_API")
        if not alias:
            raise ProviderUnavailable("COMPOSIO_API_KEY not set")
        os.environ["COMPOSIO_API_KEY"] = alias


def user_id() -> str:
    return config.load().get("composio", {}).get("user_id", "quiet-money-studio")


@lru_cache(maxsize=1)
def session():
    _ensure_key()
    try:
        from composio import Composio
    except ImportError as e:
        raise ProviderUnavailable("composio not installed (pip install composio)") from e
    s = Composio().create(user_id=user_id())
    sid = str(getattr(s, "session_id", "") or "")
    # log a short fingerprint, never the session id itself (the journal is committed, possibly publicly)
    events.emit("COMPOSIO_SESSION", user=user_id(), session_hash=hashlib.sha1(sid.encode(), usedforsecurity=False).hexdigest()[:8])
    return s


def connected_toolkits() -> dict[str, str]:
    """{toolkit_slug: connected_account_id} for every active connection of the studio user."""
    out = {}
    res = session().toolkits(is_connected=True)
    for tk in getattr(res, "items", res) or []:
        conn = getattr(tk, "connection", None)
        if conn and getattr(conn, "is_active", False):
            out[tk.slug] = getattr(getattr(conn, "connected_account", None), "id", "")
    return out


def connect(toolkit: str):
    """Start the managed OAuth flow; returns the request (open .redirect_url, then .wait_for_connection())."""
    req = session().authorize(toolkit)
    events.emit("COMPOSIO_CONNECT_LINK", toolkit=toolkit)
    return req


def execute(tool_slug: str, arguments: dict | None = None, job: str | None = None) -> dict:
    """Run one tool through the session. Returns {"data", "log_id", "successful"}; raises on failure."""
    res = session().execute(tool_slug, arguments=arguments or {})
    data = res if isinstance(res, dict) else getattr(res, "model_dump", lambda: res.__dict__)()
    log_id = data.get("log_id") or (data.get("data") or {}).get("log_id") if isinstance(data, dict) else None
    ok = bool(data.get("successful", data.get("successfull", True))) and not data.get("error")
    events.emit("COMPOSIO_EXECUTE", tool=tool_slug, ok=ok, log_id=log_id, job=job)
    ledger.spend("composio", "calls", 1, job=job)
    if not ok:
        raise ProviderError(f"{tool_slug} failed (log {log_id}): {json.dumps(data.get('error'))[:300]}")
    return {"data": data.get("data", data), "log_id": log_id, "successful": ok}
