"""The prospect machine: turns what real people wrote to us into the DM desk's prospect list. It reads, sorts and drafts; it never
contacts anyone (CLAUDE.md rule 9), and it uses no model: every step here is plain code, so a run costs 0 tokens.

    python -m faceless prospect                      collect, sort, write the list, draft through the DM desk
    python -m faceless prospect status               what is waiting, per source
    python -m faceless prospect add --handle @x --text "what they wrote" [--video "title or job id"] [--platform tiktok] [--kind comment|peer] [--name Ana] [--url ...]

Where people come from (each source is allowed to be absent; the run says which one was and why):
  * the drop folder `outbound/private/inbox/*.jsonl`: one JSON row per person, written by `prospect add`. Any agent can feed it: the
    phone driver reading the TikTok inbox, a research agent listing creators who cover the same subject.
  * comments under our own YouTube videos, through the connected YouTube account (the official API; needs the Composio key).

Only two kinds of people exist here, because the DM desk's openers are true only for them: someone who wrote under one of our videos
(`comment`), and a creator who covers the same subject (`peer`). A stranger found anywhere else is not a prospect.

Privacy: the repo is public. Rows, the day's list and the seen-set live in the gitignored `outbound/private/`; the journal gets counts.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faceless import config, dmdesk, events
from faceless.fsutil import read_jsonl, write_atomic

PRIVATE = dmdesk.DIR / "private"
INBOX = PRIVATE / "inbox"
LISTS = PRIVATE / "prospects"
SEEN = LISTS / "seen.jsonl"
KINDS = ("comment", "peer")
PLATFORMS = ("tiktok", "youtube", "instagram")
MAX_AGE_DAYS = 14                                   # a comment older than this is a cold start, not a conversation
MAX_TEXT = 500
HANDLE = re.compile(r"^@?[A-Za-z0-9._-]{2,40}$")
ORDER = {"asked": 0, "disagreed": 1, "shared": 2, "followed": 3, "peer": 4}   # who is most likely to answer, first

_QUESTION = re.compile(r"\?|^(how|what|why|when|where|which|who|can|could|should|would|does|do|is|are|did)\b", re.I)
_DISAGREE = re.compile(r"\b(wrong|not true|false|disagree|nope|nah|actually|bad advice|misleading|doesn'?t work|makes no sense|bs|but what about|"
                       r"that'?s not|you forgot|ignores?|except)\b", re.I)
_OWN = re.compile(r"\b(i|i'm|im|i've|ive|my|me|we|our|mine)\b", re.I)
_SPAM = re.compile(r"https?://|www\.|\b(dm me|check my|my page|follow me|follow back|promo|giveaway|whatsapp|telegram|crypto signal|invest with|"
                   r"sub4sub|f4f|earn \$|make \$\d)", re.I)
_WORD = re.compile(r"[A-Za-z]{2,}")


class Refused(RuntimeError):
    """The run cannot start; the message says why."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _key(row: dict) -> str:
    """One person saying one thing, as a hash: the seen-set never holds a handle or a sentence."""
    raw = f"{row['handle'].lower()}|{' '.join(row.get('text', '').lower().split())}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def clean(row: dict) -> dict:
    """A row as the machine keeps it, or ValueError naming what is wrong with it."""
    handle = str(row.get("handle") or "").strip()
    if not HANDLE.match(handle):
        raise ValueError("handle must be 2-40 letters, digits, dot, dash or underscore")
    kind = str(row.get("kind") or "comment").lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    platform = str(row.get("platform") or "tiktok").lower()
    if platform not in PLATFORMS:
        raise ValueError(f"platform must be one of {', '.join(PLATFORMS)}")
    text = " ".join(str(row.get("text") or "").split())[:MAX_TEXT]
    if len(_WORD.findall(text)) < 2:
        raise ValueError("text must be what the person wrote (or, for a peer, what their video is about): at least two words")
    url = str(row.get("url") or "").strip()
    if url and not url.startswith("https://"):
        raise ValueError("url must start with https://")
    return {"handle": handle.lstrip("@"), "name": " ".join(str(row.get("name") or "").split())[:40], "text": text, "kind": kind,
            "platform": platform, "video": " ".join(str(row.get("video") or "").split())[:120], "url": url[:300],
            "seen_at": str(row.get("seen_at") or events.now_iso())[:20]}


def add(row: dict, day: str | None = None) -> dict:
    """One row into the drop folder. This is the door every agent uses, so a malformed row never reaches the desk."""
    r = clean(row)
    day = day or config.today_utc().isoformat()
    path = INBOX / f"{r['platform']}-{day}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    have = {_key(x) for x in read_jsonl(path) if x.get("handle")} if path.exists() else set()
    if _key(r) in have:
        return {"added": False, "why": "already in today's file"}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"added": True, "file": path.name}


# ---------------------------------------------------------------- sources

def from_inbox() -> list[dict]:
    out = []
    for path in sorted(INBOX.glob("*.jsonl")) if INBOX.exists() else []:
        for raw in read_jsonl(path):
            try:
                out.append(clean(raw))
            except ValueError:
                continue                                    # a hand-written bad row is dropped, never guessed at
    return out


def from_youtube(api=None, limit: int = 100) -> list[dict]:
    """Top-level comments under our own videos, newest first. Raises ProviderUnavailable when the account is not connected."""
    if api is None:
        from faceless import ytchannel
        api = ytchannel.api
    me = (api("channels", part="id", mine="true").get("items") or [{}])[0].get("id")
    if not me:
        return []
    data = api("commentThreads", part="snippet", allThreadsRelatedToChannelId=me, maxResults=min(limit, 100), order="time", textFormat="plainText")
    out = []
    for item in data.get("items") or []:
        top = ((item.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}
        handle = str(top.get("authorDisplayName") or "").lstrip("@")
        if (top.get("authorChannelId") or {}).get("value") == me:
            continue                                        # our own pinned comment
        vid = (item.get("snippet") or {}).get("videoId") or ""
        try:
            out.append(clean({"handle": handle, "text": top.get("textOriginal") or "", "kind": "comment", "platform": "youtube",
                              "video": vid, "url": f"https://www.youtube.com/watch?v={vid}" if vid else "", "seen_at": top.get("publishedAt") or ""}))
        except ValueError:
            continue
    return out


def collect(youtube=None) -> tuple[list[dict], list[dict]]:
    """Every row from every source, plus one line per source saying what it gave (or why it gave nothing)."""
    rows, notes = [], []
    inbox = from_inbox()
    rows += inbox
    notes.append({"source": "drop folder", "rows": len(inbox), "note": "" if inbox else "empty: nothing has been added with `prospect add`"})
    try:
        yt = (youtube or from_youtube)()
        rows += yt
        notes.append({"source": "youtube comments", "rows": len(yt), "note": ""})
    except Exception as e:   # noqa: BLE001 - one absent source must not stop the others
        notes.append({"source": "youtube comments", "rows": 0, "note": f"unavailable: {config.redact(str(e))[:120]}"})
    _record_youtube(notes[-1])
    return rows, notes


YOUTUBE_RETRY_HOURS = 6                             # after a failed read the board stops offering the run for this long, then lets one run try again


def _record_youtube(note: dict) -> None:
    """Keep what the last real read of YouTube comments gave, so the board shows that and not merely that a key is present."""
    try:
        write_atomic(LISTS / "youtube-source.json", json.dumps({"t": events.now_iso(), "ok": not note["note"], "rows": note["rows"], "note": note["note"]}))
    except OSError:
        pass                                        # the record is a convenience for the board; a run never fails over it


def youtube_state() -> dict:
    """{"ok", "note"}: whether the board may count on YouTube comments, from the key and the last real read (no network)."""
    if not config.env("COMPOSIO_API_KEY", "COMPOSIO_API"):
        return {"ok": False, "note": "no Composio key on this machine"}
    try:
        last = json.loads((LISTS / "youtube-source.json").read_text(encoding="utf-8"))
        age = _now() - datetime.fromisoformat(str(last["t"]).replace("Z", "+00:00"))
    except (OSError, ValueError, KeyError, TypeError):
        return {"ok": True, "note": "a key is present; no read has been tried yet"}
    if last.get("ok"):
        return {"ok": True, "note": f"last read gave {last.get('rows', 0)} comment(s)"}
    if age > timedelta(hours=YOUTUBE_RETRY_HOURS):
        return {"ok": True, "note": f"last read failed ({last.get('note', '')}); due for another try"}
    return {"ok": False, "note": str(last.get("note") or "last read failed")}


# ---------------------------------------------------------------- sorting

def classify(row: dict) -> tuple[str | None, str]:
    """(segment, reason). None means there is nothing in what they wrote to answer, and the reason says so."""
    text = row["text"]
    if _SPAM.search(text):
        return None, "reads as promotion"
    if row["kind"] == "peer":
        return "peer", "covers the same subject"
    if len(_WORD.findall(text)) < 4:
        return None, "too short to answer (a reaction, not a sentence)"
    if _DISAGREE.search(text):
        return "disagreed", "pushed back"
    if _QUESTION.search(text):
        return "asked", "asked a question"
    if _OWN.search(text):
        return "shared", "wrote about their own situation"
    return None, "no question, no pushback, nothing about themselves"


def _seen() -> set[str]:
    return {r.get("key") for r in read_jsonl(SEEN)} if SEEN.exists() else set()


def _fresh(row: dict, today: str) -> bool:
    floor = (datetime.fromisoformat(today) - timedelta(days=MAX_AGE_DAYS)).date().isoformat()
    return row["seen_at"][:10] >= floor


def _first_name(name: str) -> str:
    first = (name.split() or [""])[0]
    return first.capitalize() if re.fullmatch(r"[A-Za-z]{2,20}", first) else ""


def _quote(text: str, room: int = 88) -> str:
    """Their own words, cut at a word so the desk's 90-character field never ends mid-word, and safe inside a quoted CSV cell."""
    text = text.replace('"', "'").replace("?", "").strip()    # the desk allows one question per message, and it is ours to ask
    if len(text) <= room:
        return text
    return text[:room].rsplit(" ", 1)[0].rstrip(",;:-") + "..."


def queue(rows: list[dict], today: str | None = None) -> tuple[list[dict], list[dict]]:
    """(ready, dropped): ready rows carry a segment and are ordered by who is likeliest to answer; dropped rows carry the reason."""
    today = today or config.today_utc().isoformat()
    seen, block, taken = _seen(), dmdesk.blocked(), set()
    ready, dropped = [], []
    for r in sorted(rows, key=lambda x: x["seen_at"], reverse=True):
        key, person = _key(r), dmdesk.handle_key(r["handle"])
        why = ("already handled" if key in seen else "on the block list" if person in block else "already in this run" if person in taken
               else f"older than {MAX_AGE_DAYS} days" if not _fresh(r, today) else "")
        seg = None
        if not why:
            seg, why = classify(r)
        if seg is None:
            dropped.append({"key": key, "why": why})
            continue
        taken.add(person)
        ready.append({**r, "segment": seg, "key": key})
    ready.sort(key=lambda x: ORDER[x["segment"]])
    return ready, dropped


def pending(youtube=None) -> dict:
    """What a run would find right now. Read-only: the command center and the mission board call this."""
    rows, notes = collect(youtube)
    ready, dropped = queue(rows)
    by = {}
    for r in ready:
        by[r["segment"]] = by.get(r["segment"], 0) + 1
    return {"ready": len(ready), "dropped": len(dropped), "bySegment": by, "sources": notes, "draftedToday": drafted_today()}


def board_state() -> dict:
    """The cheap view the command center polls: the drop folder only (no network), and what the last real read of YouTube comments gave."""
    ready, dropped = queue(from_inbox())
    yt = youtube_state()
    return {"ready": len(ready), "dropped": len(dropped), "draftedToday": drafted_today(), "youtube": yt["ok"], "youtubeNote": yt["note"],
            "addedToday": any(INBOX.glob(f"*-{config.today_utc().isoformat()}.jsonl"))}


def drafted_today(day: str | None = None) -> bool:
    day = day or config.today_utc().isoformat()
    return (dmdesk.DRAFTS / f"{day}.private.json").exists()


def _csv(ready: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["handle", "name", "context", "last interaction", "segment"])
    for r in ready:
        w.writerow([r["handle"], _first_name(r["name"]), _quote(r["text"]), (r["video"] or r["platform"])[:40], r["segment"]])
    return buf.getvalue()


def _mark(keys: list[tuple[str, str]]) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    with SEEN.open("a", encoding="utf-8") as f:
        for key, status in keys:
            f.write(json.dumps({"t": events.now_iso(), "key": key, "status": status}) + "\n")


def run(n: int = dmdesk.DEFAULT_BATCH, day: str | None = None, youtube=None) -> dict:
    """Collect, sort, write the day's list and hand it to the DM desk. One batch a day: the desk's private file is one file per day."""
    from faceless import safety
    why = safety.paused()
    if why:
        raise Refused(f"the studio is paused ({why})")
    day = day or config.today_utc().isoformat()
    if drafted_today(day):
        raise Refused("today's prospect batch is already drafted; the rest waits for tomorrow so no draft is overwritten")
    rows, notes = collect(youtube)
    ready, dropped = queue(rows, day)
    out = {"day": day, "sources": notes, "found": len(rows), "ready": len(ready), "dropped": len(dropped), "drafted": 0, "path": None, "list": None}
    _mark([(d["key"], "dropped") for d in dropped if d["why"] != "already handled"])
    if not ready:
        events.emit("PROSPECT_RUN", found=len(rows), ready=0, drafted=0)
        return out
    batch = ready[:max(1, min(n, dmdesk.MAX_PER_DAY))]
    path = LISTS / f"{day}.csv"
    write_atomic(path, _csv(batch))
    try:
        res = dmdesk.draft(len(batch), path, day)
    except dmdesk.DeskRefused as e:
        raise Refused(str(e)) from e
    made = {d["handle_hash"] for d in res["drafts"]}
    _mark([(r["key"], "drafted" if dmdesk.handle_key(r["handle"]) in made else "skipped") for r in batch])
    out.update(drafted=len(res["drafts"]), path=res["path"], list=path.name,
               skipped=[s["why"] for s in res["skipped"]], waiting=len(ready) - len(batch))
    events.emit("PROSPECT_RUN", found=len(rows), ready=len(ready), drafted=len(res["drafts"]))
    return out


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m faceless prospect")
    p.add_argument("action", nargs="?", default="run", choices=["run", "status", "add"])
    p.add_argument("-n", type=int, default=dmdesk.DEFAULT_BATCH)
    for flag in ("handle", "text", "name", "video", "platform", "kind", "url"):
        p.add_argument("--" + flag)
    a = p.parse_args(argv)
    if a.action == "add":
        try:
            print(json.dumps(add({k: getattr(a, k) for k in ("handle", "text", "name", "video", "platform", "kind", "url")})))
        except ValueError as e:
            print(f"refused: {e}")
            return 2
        return 0
    if a.action == "status":
        print(json.dumps(pending(), indent=1))
        return 0
    try:
        r = run(a.n)
    except Refused as e:
        print(f"refused: {e}")
        return 1
    for s in r["sources"]:
        print(f"  {s['source']}: {s['rows']} row(s)" + (f" ({s['note']})" if s["note"] else ""))
    print(f"{r['found']} found, {r['ready']} worth a message, {r['drafted']} drafted" + (f": {r['path']}" if r["path"] else "")
          + ". Nothing was sent; you send by hand.")
    return 0
