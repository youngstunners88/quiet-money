"""Quiet Money YouTube Posts MCP: the parts that need no browser and no network (what is ready, what was posted, what may be posted).

YouTube's API has no endpoint for Community (Posts tab) posts, so the server drives the owner's own signed-in browser profile on the owner's own
machine (browser.py). Nothing here touches a credential: the sign-in lives in a browser profile folder the owner created by logging in by hand.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("QM_REPO") or Path(__file__).resolve().parents[2])
LEDGER = REPO / "state" / "community_posts.jsonl"
MAX_PER_DAY = int(os.environ.get("QM_COMMUNITY_MAX_PER_DAY", "5"))
TEXT_MAX = 1500                                      # YouTube's limit for a post's text
DISCLOSURE = "Illustrated with AI."


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def channel_id() -> str:
    cfg = tomllib.loads((REPO / "studio.toml").read_text(encoding="utf-8"))
    return cfg["publish"]["youtube"]["channel_id"]


def comics(day: str) -> list[dict]:
    """Every comic folder of a day with its picture, the post text and the alt text."""
    out = []
    for folder in sorted((REPO / "distribution" / "comics" / day).glob("*/comic.json")):
        try:
            data = json.loads(folder.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pic = folder.parent / "picture.png"
        if pic.is_file():
            out.append({"slug": f"{day}/{folder.parent.name}", "picture": str(pic), "text": str(data.get("post") or ""), "alt": str(data.get("alt") or ""),
                        "title": str(data.get("title") or "")})
    return out


def read_ledger() -> list[dict]:
    rows = []
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue                              # a cut-off line is skipped, never a crash
    except OSError:
        pass
    return rows


def posted(slug: str) -> dict | None:
    return next((r for r in read_ledger() if r.get("slug") == slug and r.get("published")), None)


def posted_today(day: str | None = None) -> int:
    day = day or today_utc()
    return sum(1 for r in read_ledger() if r.get("published") and str(r.get("at", "")).startswith(day))


def record(slug: str, *, published: bool, note: str = "") -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"slug": slug, "published": published, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": note[:200]}
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in read_ledger() + [row]), encoding="utf-8")
    os.replace(tmp, LEDGER)                           # whole old file or whole new file, never half


def problems(item: dict) -> list[str]:
    """What stops a comic from being posted. Empty means clean."""
    out = []
    text = item["text"]
    if not text.strip():
        out.append("no post text")
    if len(text) > TEXT_MAX:
        out.append(f"text is {len(text)} characters (limit {TEXT_MAX})")
    if re.search(r"https?://", text):
        out.append("a link in the text (the offer rule allows none on picture posts)")
    if DISCLOSURE.lower() not in text.lower():
        out.append("the AI disclosure line is missing")
    if not Path(item["picture"]).is_file():
        out.append("picture file is missing")
    return out


def gate(item: dict, *, publish: bool, day: str | None = None) -> str | None:
    """The reason this post must not go out now, or None. A dry run (publish False) is only held back by a bad comic."""
    if why := problems(item):
        return "; ".join(why)
    if not publish:
        return None
    if os.environ.get("QM_COMMUNITY_APPROVED") != "1":
        return "publishing is off: the owner sets QM_COMMUNITY_APPROVED=1 on their own machine to allow it"
    if (REPO / "state" / "PAUSE").exists():
        return "state/PAUSE exists (the kill switch): nothing posts until it is lifted"
    if posted(item["slug"]):
        return "already posted"
    if posted_today(day) >= MAX_PER_DAY:
        return f"{MAX_PER_DAY} posts already went out today"
    return None
