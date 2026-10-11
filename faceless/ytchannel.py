"""The YouTube channel as code: what the channel page says, how it is found, and which series it holds.

`studio.toml [youtube]` is the wanted state (description, keywords, language, banner, one playlist per series). `plan()` diffs it against the
live channel, `apply()` makes the live channel match, and running it twice changes nothing. Everything goes through the studio's Composio
connection by the raw API (the connection can only see the one channel it was authorised for; `expected_channel_id` guards that).

Not possible through the API, so the owner does them in Studio once: the profile picture (`channel/brand-kit/avatar.png`), the channel links,
and pinning a comment.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

from faceless import config, events
from faceless.config import STUDIO
from faceless.providers import ProviderError, ProviderUnavailable

API = "https://www.googleapis.com/youtube/v3/"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/"


def _account() -> str:
    from faceless.providers import composio_tools as ct
    ct._ensure_key()
    acct = ct.connected_toolkits().get("youtube")
    if not acct:
        raise ProviderUnavailable("no YouTube connection: run `python -m faceless composio connect youtube`")
    return acct


def _proxy(url: str, method: str, body=None, headers: dict | None = None, **query):
    from composio import Composio
    account = _account()      # also puts the Composio key in place, which the client needs at construction
    params = [{"name": k, "type": "query", "value": str(v)} for k, v in query.items()]
    params += [{"name": k, "type": "header", "value": str(v)} for k, v in (headers or {}).items()]
    return Composio().tools.proxy(url, method, body=body, connected_account_id=account, parameters=params)


def api(path: str, method: str = "GET", body=None, **query) -> dict:
    """One YouTube Data API call; raises ProviderUnavailable on a quota refusal and ProviderError on any other refusal."""
    r = _proxy(API + path, method, body, **query)
    code = int(r.status or 0)
    data = r.data if isinstance(r.data, dict) else (json.loads(r.data) if r.data else {})
    events.emit("YOUTUBE_API", path=path, method=method, status=code)
    if code in (403, 429) and "quota" in json.dumps(data).lower():
        raise ProviderUnavailable("YouTube quota used up; it resets at midnight Pacific")
    if code >= 400:
        raise ProviderError(f"YouTube {method} {path} failed with HTTP {code}: {config.redact(json.dumps(data))[:300]}")
    return data


def upload_banner(path: Path) -> str:
    """Send the banner image (a resumable session we finish ourselves) and return YouTube's URL for it."""
    data = path.read_bytes()
    started = _proxy(UPLOAD + "channelBanners/insert", "POST", None, headers={"X-Upload-Content-Type": "image/png",
                     "X-Upload-Content-Length": len(data)}, uploadType="resumable")
    loc = (getattr(started, "headers", None) or {}).get("location", "")
    if int(started.status or 0) >= 400 or not loc.startswith("https://www.googleapis.com/upload/youtube/"):
        raise ProviderError(f"YouTube would not open a banner upload (HTTP {started.status})")
    r = requests.put(loc, data=data, headers={"Content-Type": "image/png"}, timeout=120)
    if r.status_code not in (200, 201):
        raise ProviderError(f"banner upload failed with HTTP {r.status_code}")
    return r.json()["url"]


def keywords_field(words: list[str]) -> str:
    """YouTube wants space-separated keywords with multi-word ones in quotes; the whole field is capped at 500 characters."""
    out, size = [], 0
    for w in words:
        item = f'"{w}"' if " " in w else w
        if size + len(item) + 1 > 500:
            break
        out.append(item)
        size += len(item) + 1
    return " ".join(out)


def desired() -> dict:
    cfg = config.load().get("youtube", {})
    from faceless import offer
    hub = offer.profile_links().get("youtube", "")
    return {
        "description": cfg.get("description", "").strip().replace("{hub}", hub),
        "keywords": keywords_field(cfg.get("keywords", [])),
        "language": cfg.get("language", "en"),
        "trailer": cfg.get("trailer", ""),
        "banner": cfg.get("banner", ""),
        "playlists": cfg.get("playlists", []),
        "channel_id": config.load()["publish"].get("youtube", {}).get("channel_id", ""),
    }


def live(channel_id: str) -> dict:
    d = api("channels", part="snippet,brandingSettings,statistics", mine="true")
    items = [i for i in d.get("items", []) if i["id"] == channel_id]
    if not items:
        raise ProviderError(f"the YouTube connection does not act as {channel_id}; changed nothing")
    item = items[0]
    lists = api("playlists", part="snippet", mine="true", maxResults=50).get("items", [])
    sections = api("channelSections", part="snippet,contentDetails", mine="true").get("items", [])
    return {"item": item, "playlists": {p["snippet"]["title"]: p["id"] for p in lists}, "sections": sections}


def plan(want: dict, now: dict) -> list[str]:
    ch = now["item"].get("brandingSettings", {}).get("channel", {})
    todo = []
    if ch.get("description", "") != want["description"]:
        todo.append("description")
    if ch.get("keywords", "") != want["keywords"]:
        todo.append("keywords")
    if ch.get("defaultLanguage", "") != want["language"]:
        todo.append("language")
    if want["trailer"] and ch.get("unsubscribedTrailer", "") != want["trailer"]:
        todo.append("trailer")
    if want["banner"] and not now["item"].get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl"):
        todo.append("banner")
    todo += [f"playlist: {p['title']}" for p in want["playlists"] if p["title"] not in now["playlists"]]
    ids = {now["playlists"].get(p["title"]) for p in want["playlists"]} - {None}
    have = {pid for s in now["sections"] for pid in (s.get("contentDetails", {}).get("playlists") or [])}
    if want["playlists"] and (len(ids) < len(want["playlists"]) or not ids <= have):   # a playlist still to be made also needs the section
        todo.append("series section")
    return todo


def apply(want: dict, now: dict, todo: list[str]) -> list[str]:
    """Do what `plan` listed. Returns what was done. Stops at the first failure so nothing half-applied is hidden."""
    done = []
    item = now["item"]
    branding = json.loads(json.dumps(item.get("brandingSettings", {})))
    ch = branding.setdefault("channel", {})
    ch.setdefault("title", item["snippet"]["title"])
    touch = False
    for key, field in (("description", "description"), ("keywords", "keywords"), ("language", "defaultLanguage"), ("trailer", "unsubscribedTrailer")):
        if key in todo:
            ch[field] = want[key]
            touch = True
    if "banner" in todo:
        branding.setdefault("image", {})["bannerExternalUrl"] = upload_banner(STUDIO / want["banner"])
        touch = True
    if touch:
        api("channels", "PUT", {"id": item["id"], "brandingSettings": branding}, part="brandingSettings")
        done += [t for t in todo if t in ("description", "keywords", "language", "trailer", "banner")]
    ids = dict(now["playlists"])
    for p in want["playlists"]:
        if f"playlist: {p['title']}" in todo:
            made = api("playlists", "POST", {"snippet": {"title": p["title"], "description": p["description"], "defaultLanguage": want["language"]},
                                              "status": {"privacyStatus": "public"}}, part="snippet,status")
            ids[p["title"]] = made["id"]
            done.append(f"playlist: {p['title']}")
    if "series section" in todo:
        api("channelSections", "POST", {"snippet": {"type": "multiplePlaylists", "style": "horizontalRow", "title": "The series", "position": 0},
                                        "contentDetails": {"playlists": [ids[p["title"]] for p in want["playlists"] if p["title"] in ids]}},
            part="snippet,contentDetails")
        done.append("series section")
    events.emit("YOUTUBE_CHANNEL_APPLIED", done=done)
    return done


def fingerprint() -> str:
    """Short hash of the wanted state, for the report."""
    return hashlib.sha1(json.dumps(desired(), sort_keys=True, default=str).encode(), usedforsecurity=False).hexdigest()[:8]


_cache: dict[str, str] = {}


def playlist_id(pillar: str) -> str | None:
    """Playlist id of a pillar's series, found by its title (cached for the run). None if the series has no playlist yet."""
    want = {p["pillar"]: p["title"] for p in config.load().get("youtube", {}).get("playlists", [])}
    title = want.get(pillar)
    if not title:
        return None
    if not _cache:
        for p in api("playlists", part="snippet", mine="true", maxResults=50).get("items", []):
            _cache[p["snippet"]["title"]] = p["id"]
    return _cache.get(title)


def add_to_series(video_id: str, pillar: str) -> bool:
    """Put a video in its series playlist. Returns whether it was added."""
    pid = playlist_id(pillar)
    if not pid:
        return False
    api("playlistItems", "POST", {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}, part="snippet")
    return True


def verify(videos: dict[str, dict], now=None) -> tuple[list[str], list[dict]]:
    """Read back the true state of videos we scheduled: {video_id: {"job": id, "post_at": iso}}.
    Returns (problems, stats rows). A success response at upload time is not proof; YouTube can drop a video minutes later
    ("processing abandoned") or an empty one can be left behind, so this is run after every daily batch and again later."""
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    problems, rows = [], []
    if not videos:
        return problems, rows
    ids = list(videos)
    found = {}
    for i in range(0, len(ids), 50):
        d = api("videos", part="status,processingDetails,contentDetails,statistics", id=",".join(ids[i:i + 50]))
        found.update({v["id"]: v for v in d.get("items", [])})
    for vid, info in videos.items():
        v, who = found.get(vid), info.get("job", vid)
        if not v:
            problems.append(f"{who} ({vid}): not found on the channel (deleted, or processing was abandoned)")
            continue
        st, pd, cd = v.get("status", {}), v.get("processingDetails", {}), v.get("contentDetails", {})
        if st.get("uploadStatus") in ("failed", "rejected", "deleted"):
            problems.append(f"{who} ({vid}): upload {st['uploadStatus']} ({st.get('failureReason') or st.get('rejectionReason') or 'no reason given'})")
        if pd.get("processingStatus") == "failed":
            problems.append(f"{who} ({vid}): processing failed ({pd.get('processingFailureReason', 'no reason given')})")
        if cd.get("duration") == "P0D" and pd.get("processingStatus") != "processing":
            problems.append(f"{who} ({vid}): empty video (zero duration)")
        publish = datetime.fromisoformat(info["post_at"]) if info.get("post_at") else None
        if publish and publish <= now and st.get("privacyStatus") == "private" and not st.get("publishAt"):
            problems.append(f"{who} ({vid}): still private after its slot time")
        s = v.get("statistics", {})
        rows.append({"job": who, "video": vid, "privacy": st.get("privacyStatus"), "processing": pd.get("processingStatus"),
                     "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)), "comments": int(s.get("commentCount", 0))})
    return problems, rows
