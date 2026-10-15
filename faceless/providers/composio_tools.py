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
from faceless.providers import ProviderError, ProviderUnavailable, http


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
        err = json.dumps(data.get("error"))
        if "exceeded your" in err and "quota" in err:       # a spent daily quota is a wait until the midnight-Pacific reset, not a defect
            raise ProviderUnavailable(f"{tool_slug}: YouTube quota used up; it resets at midnight Pacific")
        raise ProviderError(f"{tool_slug} failed (log {log_id}): {err[:300]}")
    return {"data": data.get("data", data), "log_id": log_id, "successful": ok}


YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _start_youtube_session(account_id: str, body: dict, size: int):
    from composio import Composio

    params = [
        {"name": "uploadType", "type": "query", "value": "resumable"},
        {"name": "part", "type": "query", "value": "snippet,status"},
        {"name": "X-Upload-Content-Type", "type": "header", "value": "video/mp4"},
        {"name": "X-Upload-Content-Length", "type": "header", "value": str(size)},
    ]
    return Composio().tools.proxy(YOUTUBE_UPLOAD_URL, "POST", body=body, connected_account_id=account_id, parameters=params)


def youtube_upload(video_path: str, title: str, description: str, tags: list[str] | None = None, *, expected_channel_id: str,
                   category_id: str = "27", privacy: str = "public", synthetic: bool = True, publish_at: str | None = None,
                   language: str = "en", job: str | None = None) -> dict:
    """Upload one video to YouTube through the studio's Composio connection, sending the bytes ourselves.

    The `YOUTUBE_UPLOAD_VIDEO` tool reported success but YouTube later marked two uploads "processing abandoned"
    (the video arrived cut short). Here Composio only authorises a resumable session; the whole file goes straight
    to Google in one request, so the byte count is known. The connection is checked first: the upload refuses to start
    unless the connected channel is `expected_channel_id`. The AI-content declaration is always set from `synthetic`.
    `publish_at` (UTC, "2026-10-12T15:30:00Z") uploads it private and lets YouTube make it public at that time.
    Quota and rate refusals raise ProviderUnavailable (wait for the reset); other refusals raise ProviderError.
    Opening a session makes YouTube create the video at once (empty, "Processing will begin shortly"), so never open one you will not finish.
    Returns {"video_id", "channel_id", "privacy"}.
    """
    _ensure_key()
    account_id = connected_toolkits().get("youtube")
    if not account_id:
        raise ProviderUnavailable("no YouTube connection: run `python -m faceless composio connect youtube`")
    mine = execute("YOUTUBE_LIST_CHANNELS", {"mine": True, "part": "id"}, job=job)["data"].get("items", [])
    channels = {c.get("id") for c in mine}
    if expected_channel_id not in channels:
        raise ProviderError(f"the YouTube connection acts as {sorted(channels)}, not {expected_channel_id}; nothing was uploaded")
    with open(video_path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        body = {
            "snippet": {"title": title, "description": description, "tags": tags or [], "categoryId": category_id,
                        "defaultLanguage": language, "defaultAudioLanguage": language},
            "status": {"privacyStatus": "private" if publish_at else privacy, "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": synthetic},
        }
        if publish_at:
            body["status"]["publishAt"] = publish_at
        started = _start_youtube_session(account_id, body, size)
        code = int(getattr(started, "status", 200) or 200)
        if code in (403, 429):
            raise ProviderUnavailable(f"YouTube refused the upload session (HTTP {code}): quota or rate limit; it resets at midnight Pacific")
        if code >= 400:
            raise ProviderError(f"YouTube refused the upload session (HTTP {code})")
        location = (getattr(started, "headers", None) or {}).get("location", "")
        if not location.startswith("https://www.googleapis.com/upload/youtube/"):
            raise ProviderError("YouTube did not return an upload session")
        try:
            r = http().put(location, data=f, headers={"Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=900)
        except Exception:
            # opening the session already made YouTube create an empty video ("Processing will begin shortly"); say so, so it gets cleaned up
            events.emit("YOUTUBE_SESSION_ORPHAN", job=job, note="upload session opened but the bytes never arrived: delete the empty video on the channel")
            raise
    if r.status_code in (403, 429):
        raise ProviderUnavailable(f"YouTube refused the upload (HTTP {r.status_code}): quota or rate limit; it resets at midnight Pacific")
    if r.status_code not in (200, 201):
        raise ProviderError(f"YouTube upload failed with HTTP {r.status_code}")
    out = r.json()
    events.emit("YOUTUBE_UPLOAD", video_id=out.get("id"), channel=out.get("snippet", {}).get("channelId"), bytes=size, job=job)
    return {"video_id": out.get("id"), "channel_id": out.get("snippet", {}).get("channelId"), "privacy": out.get("status", {}).get("privacyStatus")}
