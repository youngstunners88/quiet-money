"""The command center's projection: one JSON document computed from the repo's real state. Reads only.

`python -m faceless overview` writes `state/overview.json` (atomic; derived, gitignored). The page and the LAN server show this document
and nothing else, so there is one source of truth: the files each section names in its `source`. A section whose source is missing is
`null`, and the page says "source missing"; a zero is printed only when the file exists and holds nothing. Nothing here is a forecast,
and nothing here writes a job, the ledger, an offer or a target.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone

from faceless import config
from faceless.config import Paths
from faceless.fsutil import write_atomic

OUT = Paths.state / "overview.json"
STALE_HOURS = 24
PASSED = ("published", "packaged")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=Paths.root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def source() -> dict:
    status = _git("status", "--porcelain")
    return {"repo": str(Paths.root), "commit": _git("rev-parse", "--short", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": None if status is None else bool(status)}


def _step(job) -> dict:
    """Where a job stopped and why, from its own history."""
    last = job.history[-1] if job.history else {}
    why = last.get("error") or (job.notes[-1] if job.notes else "")
    return {"id": job.id, "day": job.day, "pillar": job.pillar, "title": job.artifacts.get("title") or job.topic,
            "step": last.get("from") or job.status, "why": config.redact(str(why))[:220], "score": (job.scores or {}).get("gauntlet")}


def jobs(today: str) -> dict | None:
    from faceless import phone
    from faceless.state import scan_jobs
    if not Paths.jobs.exists():
        return None
    every, unreadable = scan_jobs()
    every = [j for j in every if not j.id.startswith("host-")]
    by: dict[str, int] = {}
    for j in every:
        by[j.status] = by.get(j.status, 0) + 1
    mine = [j for j in every if j.day == today]
    last_day = max((j.day for j in every), default=None)
    recent = (datetime.fromisoformat(today) - timedelta(days=7)).date().isoformat()
    newest = sorted(every, key=lambda j: (j.day, (j.history[-1].get("ts") if j.history else "") or ""), reverse=True)[:20]
    posts = [r for r in phone.receipts() if r.get("result") == "posted"]
    queue = phone.jobs()
    return {
        "total": len(every), "byStatus": dict(sorted(by.items())),
        "held": [_step(j) for j in sorted(every, key=lambda j: j.day, reverse=True) if j.status == "held"][:30],
        "failed": [_step(j) for j in sorted(every, key=lambda j: j.day, reverse=True) if j.status == "failed"][:30],
        "heldCount": by.get("held", 0), "failedCount": by.get("failed", 0),
        "heldLast7": sum(1 for j in every if j.status == "held" and j.day > recent),
        "failedLast7": sum(1 for j in every if j.status == "failed" and j.day > recent),
        "ranToday": bool(mine), "madeToday": len(mine),
        "passedToday": sum(1 for j in mine if j.status in PASSED and (j.scores or {}).get("passed")),
        "heldToday": sum(1 for j in mine if j.status == "held"), "failedToday": sum(1 for j in mine if j.status == "failed"),
        "lastRunDay": last_day,
        "lastRun": ({"made": sum(1 for j in every if j.day == last_day),
                     "passed": sum(1 for j in every if j.day == last_day and j.status in PASSED and (j.scores or {}).get("passed")),
                     "held": sum(1 for j in every if j.day == last_day and j.status == "held"),
                     "failed": sum(1 for j in every if j.day == last_day and j.status == "failed"),
                     "unfinished": sum(1 for j in every if j.day == last_day and j.status not in (*PASSED, "held", "failed"))} if last_day else None),
        "postedToday": sum(1 for r in posts if str(r.get("at") or "")[:10] == today),
        "postedTikTokToday": sum(1 for r in posts if r.get("kind") == "tiktok" and str(r.get("at") or "")[:10] == today),
        "postedTikTokAllTime": sum(1 for r in posts if r.get("kind") == "tiktok"),
        "lastPostAt": max((str(r.get("at") or "") for r in posts), default=None),
        "tiktokQueued": sum(1 for q in queue if q.get("kind") == "tiktok" and q.get("status", "queued") == "queued"),
        "newest": [{"id": j.id, "day": j.day, "status": j.status, "pillar": j.pillar, "title": j.artifacts.get("title") or j.topic,
                    "score": (j.scores or {}).get("gauntlet")} for j in newest],
        "unreadable": unreadable,
        "source": "state/jobs/*.json, state/phone/receipts.jsonl, state/phone/jobs",
    }


def offers() -> dict | None:
    """Which products have a live listing URL (the only proof one is on sale), and at what approved price."""
    try:
        cat = json.loads((Paths.root / "channel" / "shop" / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    cfg = config.load()
    live = (cfg.get("offer") or {}).get("shop_urls") or {}
    approved = (cfg.get("shop") or {}).get("approved") or {}
    items = [{"id": p["id"], "name": p.get("name") or p["id"], "live": p["id"] in live, "url": live.get(p["id"]),
              "price": (approved.get(p["id"]) or {}).get("price") if p["id"] in live else None, "catalogPrice": p.get("price")}
             for p in cat.get("products", []) if isinstance(p, dict) and p.get("id")]
    return {"live": sum(1 for i in items if i["live"]), "built": len(items), "items": items,
            "source": "channel/shop/catalog.json, studio.toml [offer] shop_urls and [shop.approved]"}


def spend() -> dict:
    from faceless import ledger, safety
    return {"todayUsd": round(ledger.usd_total(), 4), "ceilingUsd": safety.ceiling(), "paused": safety.paused(),
            "source": "state/ledger.jsonl, studio.toml [safety], state/PAUSE"}


def service_desk() -> dict | None:
    try:
        from faceless import outbound
        p = outbound.pipeline()
    except Exception:   # noqa: BLE001 - a second desk's trouble must not blank the page
        return None
    o = p["outcomes"]
    return {"projectsSeen": p["projects_seen"], "sent": o.get("sent", 0), "replies": sum(v for k, v in o.items() if k.startswith("reply")),
            "closed": o.get("closed", 0), "source": "state/outbound-seen.json, state/outbound-outcomes.jsonl"}


def alerts(doc: dict) -> list[dict]:
    """Derived only: every alert is a fact already in the document, with the command or file that fixes it."""
    out = []
    j, sp, ob, of = doc.get("jobs"), doc.get("spend") or {}, doc.get("outbound"), doc.get("offers")

    def add(level: str, text: str, fix: str, src: str) -> None:
        out.append({"level": level, "text": text, "fix": fix, "source": src})
    if sp.get("paused"):
        add("stop", f"The studio is paused: {sp['paused']}", "Only you resume it: python -m faceless pause --resume", "state/PAUSE")
    if j is None:
        add("stop", "No job state found", "Run from the repo that owns state/jobs", "state/jobs")
    else:
        if j["unreadable"]:
            add("stop", f"{len(j['unreadable'])} job file(s) cannot be read", "python -m faceless preflight", "state/jobs")
        if not j["ranToday"]:
            add("warn", f"No daily run yet today (last run day: {j['lastRunDay'] or 'none'})", "python -m faceless preflight, then python -m faceless daily", "state/jobs")
        elif j["passedToday"] < 5:
            add("warn", f"{j['passedToday']} of today's {j['madeToday']} videos passed; the standard is five", "python -m faceless daily (it resumes)", "state/jobs")
        if j["lastRun"] and j["lastRun"]["unfinished"]:
            add("warn", f"{j['lastRun']['unfinished']} video(s) of {j['lastRunDay']} stopped before the gauntlet", "python -m faceless daily (it resumes)", "state/jobs")
        if j["failedLast7"]:
            add("warn", f"{j['failedLast7']} video(s) failed in the last 7 days", "Jobs tab shows the step; skill faceless-unblock", "state/jobs")
        if j["heldLast7"]:
            add("info", f"{j['heldLast7']} video(s) held for review in the last 7 days", "python -m faceless gauntlet <job_id>; skill faceless-gauntlet", "state/jobs")
        if j["tiktokQueued"]:
            add("warn", f"{j['tiktokQueued']} TikTok posts wait in the phone queue", "On your computer: python -m faceless phone status (skill faceless-phone-host)", "state/phone/jobs")
    if sp.get("ceilingUsd") and sp.get("todayUsd", 0) >= 0.8 * sp["ceilingUsd"]:
        add("warn", f"Spend today ${sp['todayUsd']:.2f} of the ${sp['ceilingUsd']:.2f} ceiling", "A refusal is the system working; raising a cap is yours", "state/ledger.jsonl")
    if ob and ob.get("followUpsDue"):
        add("warn", f"{ob['followUpsDue']} DM follow-up(s) are due", "Open the DMs tab; then python -m faceless dm log <id> ...", "state/outbound.jsonl")
    if ob and ob.get("blockedOnOwner"):
        add("info", f"{ob['blockedOnOwner']} DM draft(s) wait for you to send by hand", "DMs tab: copy, send, log", "state/outbound.jsonl")
    if of and of["built"] > of["live"]:
        waiting = [i["id"] for i in of["items"] if not i["live"]]
        add("info", f"Built but not listed: {', '.join(waiting)}", f"Say the price in chat: list {waiting[0]} at $<price>", "channel/shop/catalog.json")
    if not (config.load().get("newsletter") or {}).get("form_action"):
        add("info", "The hub gives the checklist away without collecting an email", "Pick an email service; its form address goes in studio.toml [newsletter] form_action", "studio.toml")
    return out


def build(today: str | None = None) -> dict:
    from faceless import dmdesk, moneybrief, offer, receipts
    today = today or config.today_utc().isoformat()
    cash = receipts.summary(today)
    batch = dmdesk.todays(today)
    doc = {
        "generatedAt": _now(), "day": today, "staleAfterHours": STALE_HOURS, "source": source(),
        "jobs": jobs(today),
        "outbound": dmdesk.funnel(today),
        "dms": ({"day": batch.get("day"), "private": bool(batch.get("private")),
                 "drafts": [{k: d.get(k) for k in ("id", "segment", "why", "title", "first", "follow_up_2", "follow_up_3", "after_reply_free", "after_reply_paid", "open_slots", "handle")}
                            for d in batch.get("drafts") or []], "source": "outbound/drafts/" + today + (".private" if batch.get("private") else "") + ".json"}
                if batch else None),
        "followUps": dmdesk.follow_ups(today),
        "cash": {"revenueMTD": cash["revenueMTD"], "netMTD": cash["netMTD"], "receipts": cash["receipts"], "receiptsAllTime": cash["receiptsAllTime"],
                 "byRail": cash["byRail"], "note": cash["note"], "sources": cash["sources"], "source": cash["source"]},
        "offers": offers(),
        "money": {"actions": moneybrief.actions(today)[:3], "brief": f"outbound/brief/{today}.md" if (moneybrief.DIR / f"{today}.md").exists() else None,
                  "source": "faceless/moneybrief.py (the money desk, state/outbound.jsonl, studio.toml)"},
        "spend": spend(),
        "serviceDesk": service_desk(),
        "targets": [],                                       # studio.toml holds no revenue or audience target; none is drawn until the owner sets one there
        "links": {"hub": offer.hub_url()},
    }
    doc["alerts"] = alerts(doc)
    return doc


def write(today: str | None = None) -> dict:
    doc = build(today)
    write_atomic(OUT, json.dumps(doc, indent=1, ensure_ascii=False))
    return doc


def summary(doc: dict) -> str:
    j, c, ob = doc["jobs"], doc["cash"], doc["outbound"]
    L = [f"Command center overview, {doc['generatedAt']} ({doc['source']['branch']} @ {doc['source']['commit']}{', uncommitted changes' if doc['source']['dirty'] else ''})"]
    if j:
        L += [f"Jobs: {j['total']} total; " + ", ".join(f"{k} {v}" for k, v in j["byStatus"].items()),
              f"Today ({doc['day']}): ran {'yes' if j['ranToday'] else 'no'}, passed {j['passedToday']}, held {j['heldToday']}, failed {j['failedToday']}, posted by phone {j['postedToday']}"]
    else:
        L.append("Jobs: source missing (state/jobs)")
    L.append(f"Money: ${c['revenueMTD']:.2f} this month from {c['receipts']} receipts" + (f" ({c['note']})" if c["note"] else ""))
    L.append("DMs: " + (f"{ob['drafted']} drafted, {ob['sent']} sent, {ob['replied']} replied, {ob['bought']} bought" if ob else "source missing (state/outbound.jsonl)"))
    L += [f"Alerts: {len(doc['alerts'])}"] + [f"  [{a['level']}] {a['text']} -> {a['fix']}" for a in doc["alerts"]]
    return "\n".join(L)
