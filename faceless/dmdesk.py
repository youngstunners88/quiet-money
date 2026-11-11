"""The DM desk: drafts the owner's direct messages, one person and one reason each. It never sends, and has no way to.

`python -m faceless dm` writes `outbound/drafts/<day>.md` (and a `.json` twin the command center reads): ready-to-copy first messages
with two follow-ups each, every one built on a number from a real Quiet Money video (the `facts` of a passed script). The owner sends by
hand and records what happened with `python -m faceless dm log <draft> sent`; `state/outbound.jsonl` is the append-only record.

Rules held in code, not in a prompt:
  * at most 20 drafts a day, one message per person per 3 days, no handle twice in a batch, a block list, nothing while `state/PAUSE` exists
  * no link in the first message or in either follow-up; a link appears only in the after-they-reply line, and only the hub page or a
    live listing from studio.toml `[offer] shop_urls`
  * 280 characters at most per message; every line passes the offer layer's claim check and a list of phrases a person can smell
  * a draft made without a prospect list carries open slots (`[first name]`, `[their words]`): it is not sendable until the owner fills
    them from what that person actually wrote. A message that could go to 100 people unchanged is wrong.

Privacy: the repo is public. Drafts made from a prospect list go to `outbound/drafts/<day>.private.md` (gitignored), the log stores a
handle only as a hash, and the block list lives in the gitignored `outbound/private/`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from faceless import config, events, offer
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

DIR = Paths.root / "outbound"
DRAFTS = DIR / "drafts"
BLOCKLIST = DIR / "private" / "blocklist.txt"
LOG = Paths.state / "outbound.jsonl"
STATUSES = ("drafted", "sent", "replied", "clicked", "bought", "dead")
MAX_PER_DAY = 20
DEFAULT_BATCH = 10
REST_DAYS = 3                                       # one message per person per three days
MAX_CHARS = 280
FOLLOW_UP_DAYS = (3, 7)
SLOT_ROOM = 45                                      # characters kept free in a draft with open slots

SEGMENTS = {
    "asked": "asked a question under",
    "shared": "wrote about their own situation under",
    "disagreed": "pushed back on the number in",
    "followed": "followed right after engaging with",
    "peer": "makes videos on the same subject as",
}
OPENERS = {
    "asked": "{name}, you asked {their} under our \"{title}\" video. The number behind it: {fact} {question}",
    "shared": "{name}, you wrote {their} under \"{title}\". The number we used there: {fact} {question}",
    "disagreed": "{name}, you pushed back on \"{title}\" ({their}). Fair. This is the math we used, so you can check it: {fact} Where does it break for you?",
    "followed": "{name}, you followed after \"{title}\" and said {their}. The number from that one: {fact} {question}",
    "peer": "{name}, your video on {their} covers the same ground as our \"{title}\". We used this number: {fact} What did your comments say about it?",
}
FOLLOW_2 = "{name}, one more line from the same video, then I'll leave it: {rule} No reply needed."
FOLLOW_3 = "{name}, last note from me. If \"{title}\" left a question unanswered, send it and we'll answer it in a video. Thanks for watching either way."
REPLY_FREE = "Glad that was useful. The free 7-day checklist that goes with it is here: {url} It's a checklist, not financial advice."
REPLY_PAID = "If you want the worksheet version of that video, it's this one (paid, ${price}): {url} Education only, no promised result."

# What a person can smell from the first line. Each of these makes a message generic, salesy or falsely familiar.
SMELLS = re.compile(
    r"quick question|i help (?:people|creators|you)|hope (?:you(?:'re| are)|this finds)|hey there|hey guys|love your (?:content|work|page)|"
    r"big fan|just wanted to reach out|pick your brain|circle back|touch base|make money|side hustle secrets|dm me|check out my|"
    r"limited spots|guaranteed", re.I)
URL = re.compile(r"https?://\S+|\bwww\.\S+|\b[\w-]+\.(?:com|io|co|net|org|ly|me)\b", re.I)


class DeskRefused(RuntimeError):
    """The desk will not draft: the studio is paused, the day's cap is reached, or a line failed a rule."""


def _now() -> datetime:
    return datetime.fromisoformat(events.now_iso().replace("Z", "+00:00"))


def handle_key(handle: str) -> str:
    """A handle as the committed log stores it: a short hash, so a public repo never lists who was written to."""
    h = (handle or "").strip().lstrip("@").lower()
    return "h:" + hashlib.sha256(h.encode("utf-8")).hexdigest()[:12] if h else ""


def blocked() -> set[str]:
    try:
        lines = BLOCKLIST.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {handle_key(x) for x in lines if x.strip() and not x.startswith("#")}


def rows() -> list[dict]:
    return read_jsonl(LOG)


def _append(row: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- what a message is built from: one passed video

def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(Paths.root))
    except ValueError:
        return str(path)


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _is_number_line(text: str) -> bool:
    """A complete calculation a stranger can check: two figures and the verb that relates them."""
    return len(re.findall(r"\d[\d,.]*", text)) >= 2 and bool(re.search(r"=|\b(?:equals?|yields?|grows?|doubles?|totals?|costs?|becomes?|takes?)\b", text, re.I))


def _sig(fact: str) -> tuple:
    """The figures of a line, so the same calculation worded twice is used once in a batch."""
    return tuple(sorted(set(re.findall(r"\d[\d,]*(?:\.\d+)?", fact))))


def sources(limit: int = 200) -> list[dict]:
    """Passed videos, newest first, each reduced to what a message may quote: its title, one verified number line, its closing rule and
    the question the video already asks. A video with no fact that survives the claim check is skipped, not paraphrased."""
    from faceless.state import all_jobs
    out = []
    jobs = [j for j in all_jobs() if j.status in ("published", "packaged") and (j.scores or {}).get("passed")]
    for j in sorted(jobs, key=lambda j: (j.day, j.id), reverse=True):
        try:
            s = json.loads((Paths.final / f"{j.id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # A number is quoted whole or not at all: a line is never cut to fit, because half a calculation is a false one (rule 1).
        facts = [_clean(f.get("claim")) for f in s.get("facts") or [] if isinstance(f, dict)]
        facts = sorted((f if f.endswith((".", "!", "?")) else f + "." for f in facts
                        if f and _is_number_line(f) and not offer.violations(f) and not URL.search(f)), key=len)
        says = [_clean(b.get("say")) for b in s.get("beats") or [] if isinstance(b, dict)]
        rules = [x for x in says if x and len(x) <= 130 and "follow" not in x.lower() and not x.endswith("?") and not offer.violations(x)]
        question, title = _clean(s.get("first_comment")), _clean(s.get("title") or j.topic)
        if not facts or not rules or not question.endswith("?") or len(question) > 90 or len(title) > 60 or offer.violations(question):
            continue
        out.append({"job": j.id, "pillar": j.pillar, "title": title, "facts": facts, "fact": facts[0], "rule": rules[-1], "question": question})
        if len(out) >= limit:
            break
    return out


def reply_lines(pillar: str) -> dict:
    """The only lines that may carry a link, for after the person replies: the hub (free checklist), and the series' product when it has a
    live listing. URLs come from the offer layer and studio.toml; nothing here writes one by hand."""
    hub = offer.tracked(offer.hub_url(), "dm", "dm", "checklist")
    out = {"free": REPLY_FREE.format(url=hub)}
    cfg = offer.settings()
    live = cfg.get("shop_urls") or {}
    cat = offer.catalog()
    for slug in (cfg.get("match") or {}).get(pillar, []):
        if slug in live and float((cat.get(slug) or {}).get("price") or 0) > 0:
            price = (config.load().get("shop", {}).get("approved", {}).get(slug) or {}).get("price") or cat[slug].get("price")
            out["paid"] = REPLY_PAID.format(price=f"{float(price):g}", url=offer.tracked(live[slug], "dm", "dm", slug))
            out["paid_product"] = slug
            break
    return out


def allowed_url(url: str) -> bool:
    live = (offer.settings().get("shop_urls") or {}).values()
    bare = url.split("?", 1)[0].split("#", 1)[0].rstrip(".,)")
    return bare.rstrip("/") == offer.hub_url().rstrip("/") or any(bare.rstrip("/") == str(u).rstrip("/") for u in live)


def lint(draft: dict) -> list[str]:
    """Why a draft may not go out. An empty list means it passed."""
    bad = []
    for key in ("first", "follow_up_2", "follow_up_3"):
        text = draft.get(key) or ""
        if len(text) > MAX_CHARS:
            bad.append(f"{key}: {len(text)} characters (max {MAX_CHARS})")
        if URL.search(text):
            bad.append(f"{key}: carries a link")
        if SMELLS.search(text):
            bad.append(f"{key}: generic or salesy phrase ({SMELLS.search(text).group(0)!r})")
        bad += [f"{key}: {v}" for v in offer.violations(text)]
    if (draft.get("first") or "").count("?") != 1:
        bad.append("first: exactly one question")
    for key in ("after_reply_free", "after_reply_paid"):
        text = draft.get(key) or ""
        if len(text) > MAX_CHARS + 120:                      # the tracked link is long; the words around it are short
            bad.append(f"{key}: too long")
        for u in re.findall(r"https?://\S+", text):
            if not allowed_url(u):
                bad.append(f"{key}: {u.split('?')[0]} is not the hub or a live listing in studio.toml")
        bad += [f"{key}: {v}" for v in offer.violations(text.replace("not financial advice", ""))]
    return bad


def compose(src: dict, segment: str, name: str = "", their: str = "", used: set | None = None) -> dict | None:
    """One draft from one video, or None when no whole fact of that video fits (the caller then takes the next video)."""
    slots = []
    if not name:
        name = "[first name]"
        slots.append("first name")
    if not their:
        their = "[their words]"
        slots.append("their words")
    budget = MAX_CHARS - (SLOT_ROOM if slots else 0)       # open slots get longer once filled: leave room for the person's own words
    fill = {"name": name, "their": their, "title": src["title"], "question": src["question"], "rule": src["rule"]}
    first = next((t for t in (OPENERS[segment].format(fact=f, **fill) for f in src.get("facts") or [src["fact"]] if _sig(f) not in (used or ()))
                  if len(t) <= budget), None)
    if first is None:
        return None
    fill["fact"] = next(f for f in src.get("facts") or [src["fact"]] if f in first)
    if used is not None:
        used.add(_sig(fill["fact"]))
    links = reply_lines(src["pillar"])
    d = {"segment": segment, "video": src["job"], "title": src["title"],
         "why": f"{SEGMENTS[segment]} \"{src['title']}\"", "first": first,
         "follow_up_2": FOLLOW_2.format(**fill), "follow_up_3": FOLLOW_3.format(**fill),
         "after_reply_free": links["free"], "after_reply_paid": links.get("paid", ""), "open_slots": slots}
    return d


# ---------------------------------------------------------------- prospects and limits

def read_prospects(path: Path) -> list[dict]:
    """handle, name, context, last interaction, segment: a CSV with that header, or the same five values per line without one."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    fields = ["handle", "name", "context", "last_interaction", "segment"]
    if "handle" not in lines[0].lower():
        lines.insert(0, ",".join(fields))
    out = []
    for r in csv.DictReader(io.StringIO("\n".join(lines))):
        r = {(k or "").strip().lower().replace(" ", "_"): " ".join((v or "").split()) for k, v in r.items()}
        if r.get("handle"):
            seg = (r.get("segment") or "").lower()
            out.append({"handle": r["handle"].lstrip("@"), "name": r.get("name", "")[:40], "context": r.get("context", "")[:90],
                        "last_interaction": r.get("last_interaction", "")[:40], "segment": seg if seg in SEGMENTS else "shared"})
    return out


def recent_contact(key: str, today: str) -> bool:
    floor = (datetime.fromisoformat(today) - timedelta(days=REST_DAYS)).date().isoformat()
    return any(r.get("handle") == key and str(r.get("t") or "")[:10] > floor and r.get("status") in ("drafted", "sent") for r in rows())


def drafted_on(day: str) -> int:
    return sum(1 for r in rows() if r.get("status") == "drafted" and str(r.get("t") or "")[:10] == day)


def _match(src: list[dict], context: str, i: int) -> dict:
    words = set(re.findall(r"[a-z]{4,}", context.lower()))
    scored = sorted(src, key=lambda s: -len(words & set(re.findall(r"[a-z]{4,}", (s["title"] + " " + s["fact"]).lower()))))
    best = scored[0]
    return best if words & set(re.findall(r"[a-z]{4,}", (best["title"] + " " + best["fact"]).lower())) else src[i % len(src)]


def draft(n: int = DEFAULT_BATCH, prospects: Path | None = None, day: str | None = None) -> dict:
    """Write the day's drafts. Returns what was written and what was skipped, with the reason for each skip."""
    from faceless import safety
    why = safety.paused()
    if why:
        raise DeskRefused(f"the studio is paused ({why}); the DM desk drafts nothing until the owner resumes it")
    day = day or config.today_utc().isoformat()
    room = MAX_PER_DAY - drafted_on(day)
    if room <= 0:
        raise DeskRefused(f"{MAX_PER_DAY} drafts already made today; the cap is there so every message stays personal")
    src = sources()
    if not src:
        raise DeskRefused("no passed video with a verified number to build a message on (script-lab/final has no usable facts)")
    private = prospects is not None
    md = DRAFTS / (f"{day}.private.md" if private else f"{day}.md")
    twin = md.with_suffix(".json")
    if not private and twin.exists():                        # one template batch a day: running twice must not use up the cap
        return {"day": day, "path": _rel(md), "drafts": json.loads(twin.read_text(encoding="utf-8"))["drafts"],
                "skipped": [], "already": True}
    people = read_prospects(prospects) if private else [None] * n
    block, seen, drafts, skipped = blocked(), set(), [], []
    used, taken = set(), set()
    segs = list(SEGMENTS)
    for i, p in enumerate(people):
        if len(drafts) >= min(n, room):
            skipped += [{"handle_hash": handle_key(x["handle"]), "why": "over today's batch or the daily cap"} for x in people[i:] if x]
            break
        if p:
            key = handle_key(p["handle"])
            reason = ("on the block list" if key in block else "already in this batch" if key in seen
                      else f"written to in the last {REST_DAYS} days" if recent_contact(key, day) else "")
            if reason:
                skipped.append({"handle_hash": key, "why": reason})
                continue
            seen.add(key)
            order = [_match(src, p["context"], i)] + src
            d = next((x for x in (compose(s_, p["segment"], p["name"] or "@" + p["handle"], p["context"] and f"\"{p['context']}\"", used)
                                  for s_ in order) if x), None)
            if d:
                d["handle"] = "@" + p["handle"]
        else:
            key = ""
            fresh = [s_ for s_ in src if s_["job"] not in taken]
            d = (next((x for x in (compose(s_, segs[i % len(segs)], used=used) for s_ in fresh) if x), None)
                 or next((x for x in (compose(s_, segs[i % len(segs)]) for s_ in fresh) if x), None))   # the channel repeats a few figures: a new video may reuse one
        if d is None:
            skipped.append({"handle_hash": key, "why": "no passed video left with a whole number line that fits"})
            continue
        taken.add(d["video"])
        problems = lint(d)
        if problems:
            skipped.append({"handle_hash": key, "why": "; ".join(problems)})
            continue
        d["id"] = f"dm-{day}-{drafted_on(day) + len(drafts) + 1:02d}"
        d["handle_hash"] = key
        drafts.append(d)
    if not drafts:
        return {"day": day, "path": None, "drafts": [], "skipped": skipped, "already": False}
    write_atomic(md, markdown(day, drafts, private))
    write_atomic(twin, json.dumps({"day": day, "private": private, "drafts": drafts}, indent=1, ensure_ascii=False))
    for d in drafts:
        _append({"t": events.now_iso(), "handle": d["handle_hash"] or None, "segment": d["segment"], "draft_id": d["id"],
                 "status": "drafted", "notes": d["video"]})
    return {"day": day, "path": _rel(md), "drafts": drafts, "skipped": skipped, "already": False}


def markdown(day: str, drafts: list[dict], private: bool) -> str:
    L = [f"# DMs to send by hand ({day})", "",
         f"{len(drafts)} drafts. You send them; nothing here is sent for you. One person, one message, one reason. "
         "No link in the first message or the follow-ups: the link line is only for after they reply.", ""]
    if not private:
        L += ["**These carry open slots.** No prospect list was given, so each draft names the video and the reason, and leaves "
              "`[first name]` and `[their words]` for you to fill from what that person actually wrote. If you cannot fill both, do not send it.", ""]
    for d in drafts:
        who = d.get("handle") or "(pick one person who fits the reason)"
        L += [f"## {d['id']}  {who}", "", f"Why this person: {d['why']}.", "", "First message"
              + (f" ({len(d['first'])} characters with the slots as written)" if d["open_slots"] else f" ({len(d['first'])} characters)") + ":", "",
              "```", d["first"], "```", "", f"Follow-up 2, day {FOLLOW_UP_DAYS[0]}, only if no reply:", "", "```", d["follow_up_2"], "```", "",
              f"Follow-up 3, day {FOLLOW_UP_DAYS[1]}, then stop:", "", "```", d["follow_up_3"], "```", "",
              "After they reply (the only place a link goes):", "", "```", d["after_reply_free"], "```", ""]
        if d.get("after_reply_paid"):
            L += ["Or, if they ask for more than the checklist:", "", "```", d["after_reply_paid"], "```", ""]
        L += ["After you send it:", "", "```bash", f"python -m faceless dm log {d['id']} sent" + ("" if d.get("handle") else " --handle @theirhandle"), "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- what happened: the owner's record

def log(draft_id: str, status: str, handle: str = "", notes: str = "") -> dict:
    if status not in STATUSES[1:]:
        raise ValueError(f"status is one of {', '.join(STATUSES[1:])}")
    known = [r for r in rows() if r.get("draft_id") == draft_id]
    if not known:
        raise ValueError(f"no draft {draft_id} in state/outbound.jsonl")
    key = handle_key(handle) or next((r.get("handle") for r in reversed(known) if r.get("handle")), None)
    if "@" in notes or URL.search(notes):
        raise ValueError("notes stay free of handles and links: the log is committed to a public repo")
    row = {"t": events.now_iso(), "handle": key, "segment": known[0].get("segment"), "draft_id": draft_id, "status": status, "notes": notes[:200]}
    _append(row)
    return row


def state() -> dict[str, dict]:
    """Each draft with every status it reached and when it was first sent."""
    out: dict[str, dict] = {}
    for r in rows():
        did = r.get("draft_id")
        if not did or r.get("status") not in STATUSES:
            continue
        d = out.setdefault(did, {"draft_id": did, "segment": r.get("segment"), "reached": [], "latest": "", "drafted_at": "", "sent_at": "", "handle": None})
        d["reached"].append(r["status"])
        d["latest"] = r["status"]
        d["handle"] = r.get("handle") or d["handle"]
        if r["status"] == "drafted" and not d["drafted_at"]:
            d["drafted_at"] = str(r.get("t") or "")
        if r["status"] == "sent" and not d["sent_at"]:
            d["sent_at"] = str(r.get("t") or "")
    return out


def funnel(today: str | None = None) -> dict | None:
    """Drafted, sent, replied, clicked, bought. None when the log does not exist: the page then says the source is missing, not zero."""
    if not LOG.exists():
        return None
    today = today or config.today_utc().isoformat()
    st = list(state().values())
    fresh = (datetime.fromisoformat(today) - timedelta(days=REST_DAYS)).date().isoformat()

    def reached(*names: str) -> int:
        return sum(1 for d in st if set(d["reached"]) & set(names))
    return {
        "drafted": len(st), "draftedToday": sum(1 for d in st if d["drafted_at"][:10] == today),
        "sent": reached("sent", "replied", "clicked", "bought"), "replied": reached("replied", "clicked", "bought"),
        "clicked": reached("clicked", "bought"), "bought": reached("bought"), "dead": reached("dead"),
        "blockedOnOwner": sum(1 for d in st if d["latest"] == "drafted" and d["drafted_at"][:10] >= fresh),
        "followUpsDue": len(follow_ups(today)), "source": "state/outbound.jsonl",
    }


def follow_ups(today: str | None = None) -> list[dict]:
    """Messages sent three or more days ago with no reply recorded: which follow-up is due."""
    today = today or config.today_utc().isoformat()
    out = []
    for d in state().values():
        if d["latest"] != "sent" or not d["sent_at"]:
            continue
        age = (datetime.fromisoformat(today) - datetime.fromisoformat(d["sent_at"][:10])).days
        if age >= FOLLOW_UP_DAYS[0]:
            out.append({"draft_id": d["draft_id"], "days_since_sent": age, "send": "follow_up_3" if age >= FOLLOW_UP_DAYS[1] else "follow_up_2"})
    return sorted(out, key=lambda x: -x["days_since_sent"])


def todays(day: str | None = None) -> dict | None:
    """The day's drafts as the command center shows them (the private batch when there is one)."""
    day = day or config.today_utc().isoformat()
    for name in (f"{day}.private.json", f"{day}.json"):
        try:
            return json.loads((DRAFTS / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return None


def weekly(today: str | None = None, min_sent: int = 30) -> dict:
    """Sent to reply to click to sale, as counts. A rate is printed only once enough were sent to mean something."""
    f = funnel(today) or {"sent": 0, "replied": 0, "clicked": 0, "bought": 0}
    sent = f["sent"]
    return {"sent": sent, "replied": f["replied"], "clicked": f["clicked"], "bought": f["bought"],
            "reply_rate": round(f["replied"] / sent, 3) if sent >= min_sent else None,
            "verdict": ("no signal yet: nothing sent" if not sent else f"too few to judge ({sent} sent, {min_sent} needed)" if sent < min_sent
                        else "kill: no reply in 30 sends" if not f["replied"] else "keep")}
