"""Offer layer: every video that leaves the building carries exactly one offer, and the studio can see which one.

Production without a call to action is a dead post. The platforms decide what a link can do, and for short video they decide against us:
TikTok and Instagram make only the profile link tappable (captions and comments are plain text), and YouTube turned links in Shorts
descriptions and comments into plain text in 2023. So the offer is "link in bio", the bio link is ONE hub page on our own site
(`/links/`), and attribution comes from what is tappable:

  - the profile link of each platform (`utm_source` = the platform, `utm_medium` = bio): which platform converts
  - the hub card a visitor asks for (`o=<slug>`) and the day: which offer follows which videos
  - the asset wherever a link IS tappable (thread, LinkedIn post, pin, newsletter, long-form description): `utm_content` = the video id

Nothing here posts, creates a product, changes a price or calls a model. Copy comes from a few templates (the owner may override them in
`[offer.copy]`), every line passes the claim check, and a paid offer is only chosen when the owner has put its live listing URL in
`[offer.shop_urls]`: the engine never invents a URL. The ledger is `state/offers.jsonl` (append-only, merged by union like the other logs;
the latest row for a video wins). `status` is `draft` until the owner says the comment is pinned (`offer mark VIDEO pinned`).

    python -m faceless offer                       # coverage, profile links, what is missing
    python -m faceless offer --batch today         # make sure every passed video of the day has its pack and row (idempotent)
    python -m faceless offer check "some copy"     # the claim check on any text
    python -m faceless offer mark VIDEO pinned
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from faceless import config, events
from faceless.config import Paths
from faceless.prompts import COMPLIANCE_BANNED

OFFERS = Paths.state / "offers.jsonl"
STATUSES = ("draft", "pinned")
PLATFORMS = ("tiktok", "youtube", "instagram")
PINNED_MAX = 150                                   # TikTok's comment limit is the tightest of the three
FREE = "checklist"

DEFAULTS = {
    "hub_path": "/links/",
    "paid_every": 3,                               # at most one paid offer in this many videos: the free list comes first
    "match": {"story": ["money-reset-kit"], "math": ["debt-payoff-planner"], "psychology": ["money-reset-printables"],
              "myth": ["money-reset-kit"], "escape": ["rat-race-escape-planner"], "playbook": []},
    "shop_urls": {},
    "copy": {},
}

COPY = {
    "free": {"pinned": "Free 60-second money reset checklist is in my bio. Educational only, not financial advice.",
             "caption": "Free money reset checklist: link in bio.",
             "description": "Free 7-day Money Reset checklist + calculators: {url}"},
    "paid": {"pinned": "{short} is in my bio (paid). Educational only, not financial advice.",
             "caption": "{short}: link in bio (paid).",
             "description": "{short} (paid), and the free Money Reset checklist: {url}"},
}

# What a call to action must never say. Each is a promise about money, which the video gauntlet already refuses in scripts.
CLAIMS = [
    ("guarantee", r"\bguarantee[sd]?\b"),
    ("risk-free", r"\brisk[- ]free\b|\bno[- ]risk\b|\b100% safe\b|\bcan(?:'|’)?t lose\b|\bcannot lose\b"),
    ("income promise", r"\byou(?:'ll| will)\s+(?:make|earn|get|save|be|retire)\b|\bmake\s+\$?\d[\d,.]*\s*[km]?\s*(?:a|per|/|each)\s*(?:day|week|month|year)\b|\bpassive income\b"),
    ("get rich", r"\bget[- ]rich\b|\bmillionaire\b|\bquit your job\b|\bdouble your money\b|\bfinancial freedom in\b"),
    ("specific return", r"\b\d+(?:\.\d+)?\s*%\s*(?:returns?|apy|roi|profit|gains?)\b|\bearn\s+\$?\d"),
    ("debt relief promise", r"\b(?:erase|eliminate|wipe out|get out of|clear|fix)\s+(?:your\s+)?debt\b|\bdebt[- ]free\s+(?:in|by)\b"),
    ("advice claim", r"(?<!not )(?<!no )\bfinancial advice\b"),          # "not financial advice" is the required disclaimer
    ("buy call", r"\byou should (?:buy|invest|sell)\b|\bbuy this\b"),
]


# ---------------------------------------------------------------- settings and destinations

def settings() -> dict:
    cfg = config.load().get("offer", {})
    out = {**DEFAULTS, **{k: v for k, v in cfg.items() if k in DEFAULTS}}
    out["match"] = {**DEFAULTS["match"], **(cfg.get("match") or {})}
    return out


def catalog() -> dict[str, dict]:
    """The products on the shop catalog by slug: name, price, kind. Offers can only point at these."""
    path = Paths.root / "channel" / "shop" / "catalog.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {p["id"]: {"name": p.get("name", p["id"]), "price": p.get("price"), "kind": p.get("kind", "")} for p in data.get("products", []) if "id" in p}


def base() -> str:
    return str(config.load().get("site", {}).get("base_url", "")).rstrip("/")


def hub_url() -> str:
    b = base()
    return b + str(settings()["hub_path"]) if b else ""


def checklist_url() -> str:
    b = base()
    return b + "/money-reset/" if b else ""


def _part(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(value).lower()).strip("-")[:60]


def tracked(url: str, source: str, medium: str, campaign: str, content: str = "", focus: str = "") -> str:
    """`url` with the UTM parts (and, for the hub, the card to feature). Empty when there is no url: a link is never invented."""
    if not url:
        return ""
    q = {"utm_source": _part(source), "utm_medium": _part(medium), "utm_campaign": _part(campaign)}
    if content:
        q["utm_content"] = _part(content)
    if focus:
        q["o"] = _part(focus)
    return url + ("&" if "?" in url else "?") + urlencode(q)


def profile_links() -> dict[str, str]:
    """The URL to put in each platform's profile link field. Same page, tagged by platform."""
    return {p: tracked(hub_url(), p, "bio", "profile") for p in PLATFORMS}


def destinations() -> list[dict]:
    """The free checklist, plus every product whose live listing URL the owner has set. A product with no URL is not an offer yet."""
    out = [{"slug": FREE, "kind": "free", "name": "the free 7-day Money Reset", "short": "The free Money Reset checklist", "price": 0, "url": checklist_url()}]
    cat = catalog()
    for slug, url in (settings()["shop_urls"] or {}).items():
        p = cat.get(slug)
        if p and str(url).startswith("https://"):
            out.append({"slug": slug, "kind": "paid", "name": p["name"], "short": f"The {p['name']}" if not p["name"].lower().startswith("the ") else p["name"],
                        "price": p["price"], "url": str(url)})
    return out


# ---------------------------------------------------------------- the ledger

def rows() -> list[dict]:
    if not OFFERS.exists():
        return []
    out = []
    for line in OFFERS.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line) if line.strip() else None
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and r.get("video_id"):
            out.append(r)
    return out


def latest(all_rows: list[dict] | None = None) -> list[dict]:
    """One row per video (the newest), in the order the videos first appeared."""
    seen: dict[str, dict] = {}
    for r in all_rows if all_rows is not None else rows():
        seen[r["video_id"]] = r
    return list(seen.values())


def append_row(row: dict) -> None:
    OFFERS.parent.mkdir(parents=True, exist_ok=True)
    with open(OFFERS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- choosing and writing the offer

def choose(pillar: str, history: list[dict]) -> dict:
    """The free checklist builds the list, so it leads: a paid offer only comes after `paid_every - 1` free ones, only for a pillar
    that has a matching product with a live URL, and never the same product twice running. 'Do This Today' is always free."""
    dests = {d["slug"]: d for d in destinations()}
    free = dests[FREE]
    s = settings()
    gap = max(2, int(s["paid_every"])) - 1
    recent = history[-gap:]
    if len(recent) < gap or any(r.get("slug") != FREE for r in recent):
        return free
    last_paid = next((r.get("slug") for r in reversed(history) if r.get("slug") != FREE), None)
    for slug in s["match"].get(pillar, []):
        if slug in dests and slug != last_paid:
            return dests[slug]
    return free


def violations(text: str) -> list[str]:
    """Why a piece of copy cannot ship. Empty list means it is clean."""
    found = []
    low = text.lower()
    for name, rx in CLAIMS:
        if m := re.search(rx, low):
            found.append(f"{name}: {m.group(0).strip()!r}")
    found += [f"banned phrase: {p!r}" for p in COMPLIANCE_BANNED if p in low]
    return found


def _fill(template: str, dest: dict, url: str) -> str:
    return template.format(short=dest["short"], name=dest["name"], price=dest.get("price") or "", url=url)


def build(video_id: str, pillar_id: str, title: str = "", history: list[dict] | None = None, post_day: str = "", force: str = "") -> dict:
    """The offer for one video: destination, copy for the three places it appears, tracked links and a verdict. Pure: it touches no file.
    `problems` empty and status `draft` mean it can ship; `LINK_MISSING` means the site URL is not set and nothing was written.
    `force` names the destination a posted caption already carries, so a repair never changes what the video says."""
    hist = latest() if history is None else history
    dests = {d["slug"]: d for d in destinations()}
    dest = dests.get(force) or choose(pillar_id, hist)
    kind = "free" if dest["slug"] == FREE else "paid"
    hub = hub_url()
    problems: list[str] = []
    if not hub:
        return {"video_id": video_id, "pillar": pillar_id, "title": title, "slug": dest["slug"], "kind": kind, "status": "LINK_MISSING",
                "problems": ["[site] base_url is empty: no link to put in the offer"], "pinned_comment": "", "caption_line": "", "description_line": "",
                "url": "", "utm_campaign": dest["slug"], "utm_content": _part(video_id), "post_day": post_day}
    url = tracked(hub, "youtube", "short", dest["slug"], content=video_id, focus=dest["slug"])
    override = (settings()["copy"] or {}).get(kind) or {}
    copy = {}
    for field in ("pinned", "caption", "description"):
        text = _fill(str(override.get(field) or COPY[kind][field]), dest, url)
        bad = violations(text)
        if bad:                                           # an owner edit that makes a promise falls back to the safe line, and says so
            problems.append(f"{field} copy refused ({'; '.join(bad)}): used the built-in line")
            text = _fill(COPY[kind][field], dest, url)
        copy[field] = text
    if len(copy["pinned"]) > PINNED_MAX:
        problems.append(f"pinned comment is {len(copy['pinned'])} characters (limit {PINNED_MAX})")
    urls = set(re.findall(r"https?://\S+", copy["description"]))
    if len(urls) != 1:
        problems.append(f"the description line carries {len(urls)} links (exactly one allowed)")
    return {"video_id": video_id, "pillar": pillar_id, "title": title, "slug": dest["slug"], "kind": kind, "label": dest["name"], "status": "draft",
            "problems": problems, "pinned_comment": copy["pinned"], "caption_line": copy["caption"], "description_line": copy["description"],
            "url": url, "utm_campaign": _part(dest["slug"]), "utm_content": _part(video_id), "post_day": post_day}


TAGS = re.compile(r"^(?P<text>.*?)(?P<tags>(?:\s*#\w+)+)\s*$", re.S)


def put_in_caption(caption: str, line: str) -> str:
    """The call to action goes on its own line before the hashtags, which stay last."""
    if not line or line in caption:
        return caption
    m = TAGS.match(caption.strip())
    if m and m.group("text").strip():
        return f"{m.group('text').rstrip()}\n\n{line}\n\n{m.group('tags').strip()}"
    return f"{caption.strip()}\n\n{line}"


def apply_to_meta(meta: dict, offer: dict) -> dict:
    """Write the offer into what gets posted: the caption's call to action and the description's single link line."""
    if offer["status"] != "draft" or not offer["description_line"]:
        return meta
    meta["caption"] = put_in_caption(meta.get("caption", ""), offer["caption_line"])[:2150]
    meta["offer"] = {k: offer[k] for k in ("slug", "kind", "pinned_comment", "caption_line", "description_line", "url", "status", "problems",
                                           "utm_campaign", "utm_content")}
    return meta


def render_md(offer: dict, title: str = "") -> str:
    lines = [f"# Offer: {title or offer['title'] or offer['video_id']}", "",
             f"Video `{offer['video_id']}` · pillar `{offer['pillar']}` · destination **{offer['slug']}** ({offer['kind']}) · status **{offer['status']}**", "",
             "The engine wrote this and posted nothing. You pin the comment; say so with `python -m faceless offer mark %s pinned`." % offer["video_id"], ""]
    if offer["status"] == "LINK_MISSING":
        return "\n".join(lines + ["**LINK_MISSING**: set `[site] base_url` in studio.toml. No offer was written."]) + "\n"
    lines += ["## Pinned comment (%d of %d characters)" % (len(offer["pinned_comment"]), PINNED_MAX), "", offer["pinned_comment"], "",
              "## Already in the caption (last line before the hashtags)", "", offer["caption_line"], "",
              "## Already in the YouTube description (plain text on Shorts, tappable on a long video)", "", offer["description_line"], "",
              "## Profile links (set once per platform; same page, tagged by platform)", ""]
    lines += [f"- {p.title()}: {u}" for p, u in profile_links().items()]
    if offer["problems"]:
        lines += ["", "## Notes", ""] + [f"- {p}" for p in offer["problems"]]
    return "\n".join(lines) + "\n"


def record(video_id: str, folder: Path, offer: dict) -> dict:
    """Write OFFER.md next to the posting pack and one ledger row (once: the same offer is never logged twice). Returns {written, row}."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "OFFER.md").write_text(render_md(offer), encoding="utf-8")
    prior = next((r for r in reversed(rows()) if r["video_id"] == video_id), None)
    if prior and prior.get("slug") == offer["slug"] and prior.get("status") in (offer["status"], "pinned"):
        return {"written": False, "row": prior}
    row = {"t": events.now_iso(), "date": offer.get("post_day") or folder.parent.name, "video_id": video_id, "pillar": offer["pillar"],
           "destination": offer["kind"], "slug": offer["slug"], "utm_campaign": offer["utm_campaign"], "utm_content": offer["utm_content"],
           "status": offer["status"], "notes": "; ".join(offer["problems"])}
    append_row(row)
    events.emit("OFFER_RECORDED", job=video_id, slug=offer["slug"], status=offer["status"])
    return {"written": True, "row": row}


LEGACY_LINK = "Free 7-day Money Reset checklist + calculators:"


def repair_pack(folder: Path, offer: dict) -> bool:
    """A pack made before the offer layer existed: put the offer into its meta.json (caption line, description link line) and rewrite POST.md
    from it, so OFFER.md tells the truth. Packs that already carry an offer are left alone. Returns whether anything changed."""
    from zoneinfo import ZoneInfo
    from faceless.providers import publish
    folder = Path(folder)
    path = folder / "meta.json"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if meta.get("offer") or offer["status"] != "draft":
        return False
    lines = str(meta.get("description", "")).split("\n")
    at = next((i for i, ln in enumerate(lines) if ln.startswith(LEGACY_LINK)), None)
    if at is None:
        lines[1:1] = ["", offer["description_line"]] if len(lines) > 1 else ["", offer["description_line"]]
    else:
        lines[at] = offer["description_line"]
    meta["description"] = "\n".join(lines)
    apply_to_meta(meta, offer)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    m = re.match(r"slot(\d+)-", folder.name)
    try:
        when = datetime.fromisoformat(meta["post_at"]).astimezone(ZoneInfo(config.load()["publish"]["timezone"])).strftime("%Y-%m-%d %H:%M %Z")
    except (KeyError, ValueError):
        when = str(meta.get("post_at", ""))
    (folder / "POST.md").write_text(publish.render_post(int(m.group(1)) - 1 if m else 0, when, meta), encoding="utf-8")
    return True


def mark(video_id: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    prior = next((r for r in reversed(rows()) if r["video_id"] == video_id), None)
    if not prior:
        raise KeyError(f"no offer recorded for {video_id}")
    row = {**prior, "t": events.now_iso(), "status": status}
    append_row(row)
    return row


# ---------------------------------------------------------------- the daily batch and the report

def _passed_videos(day: str):
    """(job, pack folder) for every gauntlet-passed, packaged video whose post day or job day is `day`, or whose id is `day`."""
    from faceless.state import all_jobs
    for j in all_jobs():
        local = (j.artifacts.get("publish") or {}).get("local") or {}
        folder = Path(local["folder"]) if local.get("folder") else None
        if j.status not in ("packaged", "published") or not j.scores.get("passed") or not folder or not folder.exists():
            continue
        if day in (j.id, folder.parent.name, j.day):
            yield j, folder


def batch(day: str | None = None) -> dict:
    """Make sure every passed video of the day has an offer pack and a ledger row. Idempotent; the daily route runs it after the batch
    as a net under the packaging step. Returns counts and problems; a video without a usable offer is listed, never published silently."""
    want = day or date.today().isoformat()
    out = {"day": want, "videos": 0, "with_offer": 0, "written": 0, "problems": []}
    for j, folder in _passed_videos(want):
        out["videos"] += 1
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
        have = meta.get("offer")
        if have and (folder / "OFFER.md").exists() and any(r["video_id"] == j.id for r in rows()):
            out["with_offer"] += 1
            continue
        offer = build(j.id, j.pillar, meta.get("title", ""), post_day=folder.parent.name, force=(have or {}).get("slug", ""))
        if not have and repair_pack(folder, offer):
            out["repaired"] = out.get("repaired", 0) + 1
        res = record(j.id, folder, offer)
        out["written"] += int(res["written"])
        if offer["status"] != "draft" or offer["problems"]:
            out["problems"].append(f"{j.id}: " + ("; ".join(offer["problems"]) or offer["status"]))
        if offer["status"] == "draft":
            out["with_offer"] += 1
    return out


def status() -> dict:
    """Coverage and mix over the last 14 days of videos, plus how many offers still wait for the owner to pin them."""
    mine = latest()[-70:]
    by_slug: dict[str, int] = {}
    for r in mine:
        by_slug[r.get("slug", "?")] = by_slug.get(r.get("slug", "?"), 0) + 1
    return {"videos": len(mine), "by_slug": by_slug, "draft": sum(1 for r in mine if r.get("status") == "draft"),
            "pinned": sum(1 for r in mine if r.get("status") == "pinned"), "link_missing": sum(1 for r in mine if r.get("status") == "LINK_MISSING"),
            "hub": hub_url(), "paid_live": [d["slug"] for d in destinations() if d["kind"] == "paid"], "profile_links": profile_links()}


def unoffered(day: str | None = None) -> list[str]:
    """Ids of passed videos of the day with no usable offer: what preflight and the watchdog warn about."""
    want = day or date.today().isoformat()
    have = {r["video_id"] for r in latest() if r.get("status") in STATUSES}
    return [j.id for j, _ in _passed_videos(want) if j.id not in have]
