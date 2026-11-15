"""The command center's projection: one JSON document computed from the repo's real state. Reads only.

`python -m faceless overview` writes `state/overview.json` (atomic; derived, gitignored). The page and the LAN server show this document
and nothing else, so there is one source of truth: the files each section names in its `source`. A section whose source is missing is
`null`, and the page says "source missing"; a zero is printed only when the file exists and holds nothing. Nothing here is a forecast,
and nothing here writes a job, the ledger, an offer or a target. The buttons on the page act through `faceless/actions.py`; this module
only says what is true afterwards, and which action (if any) answers each alert.
"""

from __future__ import annotations

import json
import subprocess
import time
import tomllib
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


_DEVICE: dict = {"at": 0.0, "doc": None}


def device() -> dict:
    """Is a phone attached to adb on this computer? `attached` is None when adb is not installed or did not answer. Asked at most
    every 15 s."""
    if _DEVICE["doc"] is not None and time.monotonic() - _DEVICE["at"] < 15:
        return _DEVICE["doc"]
    try:
        r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=6)
        rows = [ln.split("\t") for ln in r.stdout.splitlines()[1:] if "\t" in ln]
        ready = [x[0] for x in rows if x[1].strip() == "device"]
        other = sorted({x[1].strip() for x in rows if x[1].strip() != "device"})
        doc = {"attached": bool(ready), "count": len(ready), "note": ("" if ready else ("phone seen but " + ", ".join(other) if other else "no phone answers adb"))}
    except (OSError, subprocess.SubprocessError):
        doc = {"attached": None, "count": 0, "note": "adb is not installed or did not answer"}
    _DEVICE.update(at=time.monotonic(), doc=doc)
    return doc


def phone_lane() -> dict | None:
    """The phone lane as the Non-stop rule sees it: the next job the gate lets through, what is held, what is blocked and why."""
    from faceless import phone
    if not (phone.home() / "jobs").exists():
        return None
    rows = phone.jobs()
    queued = [j for j in rows if j.get("status", "queued") == "queued"]
    why = {j["id"]: phone.gate(j) for j in queued}
    nxt = phone.next_job()
    reasons: dict[str, int] = {}
    for w in why.values():
        if w:
            reasons[w] = reasons.get(w, 0) + 1
    by: dict[str, int] = {}
    for j in queued:
        by[j["kind"]] = by.get(j["kind"], 0) + 1
    held = [j for j in rows if j.get("status") == "held"]
    on_branch = phone._branch_files()
    gone = [j["id"] for j in queued if why[j["id"]] is None and phone.media_missing(j, on_branch)] if on_branch is not None else []
    return {
        "mediaMissing": len(gone), "nextMediaMissing": bool(nxt and nxt["id"] in gone),
        "enabled": phone.cfg()["enabled"],
        "next": ({"id": nxt["id"], "kind": nxt["kind"], "day": nxt["day"], "recipe": nxt.get("recipe")} if nxt else None),
        "queued": len(queued), "queuedByKind": dict(sorted(by.items())),
        "runnable": sum(1 for w in why.values() if w is None),
        "blockedCount": sum(1 for w in why.values() if w), "blockedWhy": dict(sorted(reasons.items(), key=lambda kv: -kv[1])[:6]),
        "held": [{"id": j["id"], "kind": j["kind"], "day": j["day"], "why": config.redact(str(((j.get("history") or [{}])[-1]).get("note") or ""))[:160],
                  "gate": phone.gate({**j, "status": "queued"}) or ""} for j in sorted(held, key=lambda j: j["day"], reverse=True)[:20]],
        "heldCount": len(held),
        "device": device(),
        "source": "state/phone/jobs, state/phone/receipts.jsonl, studio.toml [phone], adb devices",
    }


def job_detail(jid: str) -> dict | None:
    """One job's own record for the page's step viewer: where it stopped, why, and which gates failed. Reads only."""
    from faceless import actions, phone
    from faceless.state import load_job
    if not actions.NAME.match(jid or ""):
        return None
    if (Paths.jobs / f"{jid}.json").is_file():
        try:
            job = load_job(jid)
        except (OSError, ValueError, TypeError):
            return {"id": jid, "kind": "video", "status": "unreadable", "history": [], "notes": [], "report": None, "source": f"state/jobs/{jid}.json"}
        report = None
        try:
            rep = json.loads((Paths.reports / f"{jid}.json").read_text(encoding="utf-8"))
            report = {"score": rep.get("score"), "passed": rep.get("passed"), "hardFailures": rep.get("hard_failures") or [],
                      "failed": [{"name": g.get("name"), "hard": bool(g.get("hard")), "detail": config.redact(str(g.get("detail") or ""))[:240], "fix": g.get("fix")}
                                 for g in rep.get("gates") or [] if not g.get("passed")]}
        except (OSError, ValueError):
            pass
        return {"id": job.id, "kind": "video", "status": job.status, "day": job.day, "pillar": job.pillar, "title": job.artifacts.get("title") or job.topic,
                "history": [{"from": h.get("from"), "to": h.get("to"), "ts": h.get("ts"), "error": config.redact(str(h.get("error") or ""))[:240],
                             "score": h.get("score")} for h in job.history[-14:]],
                "notes": [config.redact(str(n))[:240] for n in job.notes[-6:]], "scores": job.scores, "report": report,
                "canRetry": job.status in ("failed", "held", "planned", "scripted", "visualized"),
                "source": f"state/jobs/{jid}.json, gauntlet/reports/{jid}.json"}
    if phone.job_path(jid).is_file():
        try:
            job = phone.load(jid)
        except (OSError, ValueError):
            return None
        return {"id": jid, "kind": "phone", "phoneKind": job.get("kind"), "status": job.get("status", "queued"), "day": job.get("day"),
                "title": str(job.get("title") or job.get("text") or job.get("key") or "")[:120],
                "history": [{"ts": h.get("at"), "to": h.get("result"), "error": config.redact(str(h.get("note") or ""))[:240]} for h in (job.get("history") or [])[-14:]],
                "notes": [], "gate": phone.gate(job) or "", "report": None, "canRetry": False, "source": f"state/phone/jobs/{jid[:10]}/{jid}.json"}
    return None


DM_KEYS = ("id", "segment", "why", "title", "first", "follow_up_2", "follow_up_3", "after_reply_free", "after_reply_paid", "open_slots", "handle")


def dm_batches(today: str) -> dict | None:
    """Today's drafts, plus the earlier ones the owner has not finished with (still drafted, or sent and waiting for a reply), each
    with the status the record holds. Without this a draft written yesterday waits for ever where nobody sees it."""
    from faceless import dmdesk
    st = dmdesk.state() if dmdesk.LOG.exists() else {}
    open_days = {d["drafted_at"][:10] for d in st.values() if d["latest"] in ("drafted", "sent") and d["drafted_at"]}
    drafts, sources, private = [], [], False
    for day in sorted(open_days | {today}, reverse=True)[:5]:
        batch = dmdesk.todays(day)
        if not batch:
            continue
        kept = 0
        for d in batch.get("drafts") or []:
            latest = (st.get(d.get("id")) or {}).get("latest") or "drafted"
            if day != today and latest not in ("drafted", "sent"):
                continue
            drafts.append({**{k: d.get(k) for k in DM_KEYS}, "status": latest, "day": day})
            kept += 1
        if kept:
            private = private or bool(batch.get("private"))
            sources.append("outbound/drafts/" + day + (".private" if batch.get("private") else "") + ".json")
    if not drafts:
        return None
    return {"day": today, "private": private, "drafts": drafts, "source": ", ".join(sources) + "; state/outbound.jsonl"}


def targets(doc: dict) -> list[dict]:
    """Only the targets the owner wrote in studio.toml, each beside the real number. No revenue or audience target exists there, so
    none is drawn."""
    try:
        with open(Paths.config, "rb") as f:
            raw = tomllib.load(f)
    except (OSError, ValueError):
        return []
    out = []
    per_day = (raw.get("production") or {}).get("videos_per_day")
    if per_day and doc.get("jobs"):
        out.append({"id": "production.videos_per_day", "label": "Videos passed today", "target": per_day, "actual": doc["jobs"]["passedToday"],
                    "source": "studio.toml [production] videos_per_day; state/jobs"})
    ready_min = (raw.get("outbound") or {}).get("ready_min_per_day")
    if ready_min is not None:
        try:
            from faceless import outbound
            ready = outbound.desk()["ready"]
        except Exception:   # noqa: BLE001 - the target is still shown; the number is honest about being unknown
            ready = None
        out.append({"id": "outbound.ready_min_per_day", "label": "Service-desk drafts ready to send today", "target": ready_min, "actual": ready,
                    "source": "studio.toml [outbound] ready_min_per_day; channel/services/web3-video packages"})
    return out


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
            "closed": o.get("closed", 0), "waiting": len(p["packages_waiting"]), "waitingTop": p["packages_waiting"][:8],
            "source": "state/outbound-seen.json, state/outbound-outcomes.jsonl, channel/services/web3-video packages"}


def alerts(doc: dict) -> list[dict]:
    """Derived only: every alert is a fact already in the document, with the command or file that fixes it. An alert may carry
    `action` (the button that runs the fix through faceless/actions.py) or `tab` (where the buttons for it are).

    Order is the owner's: a pause first, then nothing ran today, failed jobs with their step, the held pile, outbound waiting on a
    person, the Hermes gateway when messaging is set up; everything else follows."""
    out = []
    j, sp, ob, of = doc.get("jobs"), doc.get("spend") or {}, doc.get("outbound"), doc.get("offers")
    ph, desk, hm = doc.get("phone"), doc.get("serviceDesk") or {}, doc.get("hermes") or {}

    def add(level: str, text: str, fix: str, src: str, action: dict | None = None, tab: str | None = None) -> None:
        out.append({"level": level, "text": text, "fix": fix, "source": src, **({"action": action} if action else {}), **({"tab": tab} if tab else {})})
    daily = {"name": "daily", "args": {}, "label": "Run today's batch"}
    daily_fix = "python -m faceless preflight, then python -m faceless daily --no-publish (packages; TikTok goes out through the phone lane)"
    if sp.get("paused"):
        add("stop", f"The studio is paused: {sp['paused']}", "Only you resume it: python -m faceless pause --resume", "state/PAUSE")
    if j is None:
        add("stop", "No job state found", "Run from the repo that owns state/jobs", "state/jobs")
    else:
        if j["unreadable"]:
            add("stop", f"{len(j['unreadable'])} job file(s) cannot be read", "python -m faceless preflight", "state/jobs")
        if not j["ranToday"]:
            add("warn", f"Nothing ran today (last run day: {j['lastRunDay'] or 'none'})", daily_fix, "state/jobs", daily)
        elif j["passedToday"] < 5:
            add("warn", f"{j['passedToday']} of today's {j['madeToday']} videos passed; the standard is five", "python -m faceless daily --no-publish (it resumes)", "state/jobs", daily)
        if j["failedCount"]:
            steps: dict[str, int] = {}
            for r in j["failed"]:
                steps[r["step"]] = steps.get(r["step"], 0) + 1
            top = max(steps, key=steps.get) if steps else "unknown"
            why = next((r["why"] for r in j["failed"] if r["step"] == top and r["why"]), "")
            add("warn" if j["failedLast7"] else "info",
                f"{j['failedCount']} failed job(s), {j['failedLast7']} in the last 7 days; most stopped at {top}" + (f": {why[:90]}" if why else ""),
                "Jobs tab: Retry runs python -m faceless retry <job_id>; View steps shows where it stopped", "state/jobs", tab="jobs")
        if j["heldCount"]:
            add("warn", f"{j['heldCount']} video(s) held for review ({j['heldLast7']} in the last 7 days): the bottleneck",
                "Jobs tab: Release re-runs the gates (python -m faceless retry <job_id>) and records why if it still cannot pass", "state/jobs", tab="jobs")
    waiting_dm, waiting_pkg = (ob or {}).get("blockedOnOwner") or 0, desk.get("waiting") or 0
    if waiting_dm or waiting_pkg:
        parts = ([f"{waiting_dm} DM draft(s)"] if waiting_dm else []) + ([f"{waiting_pkg} service-desk package(s)"] if waiting_pkg else [])
        add("warn", " and ".join(parts) + " wait for you to send by hand",
            "DMs tab: copy, send, then press Sent (python -m faceless dm log <id> sent)" + ("; packages: python -m faceless outbound next" if waiting_pkg else ""),
            "state/outbound.jsonl" + (", channel/services/web3-video packages" if waiting_pkg else ""), tab="dms")
    if hm.get("installed") and hm.get("messaging") and (hm.get("gateway") or {}).get("running") is False:
        add("warn", f"The Hermes gateway is down; messaging is set up for {', '.join(hm['messaging'])}", "hermes gateway run", "hermes gateway status, ~/.hermes/.env (names only)")
    if j is not None:
        if j["lastRun"] and j["lastRun"]["unfinished"]:
            add("warn", f"{j['lastRun']['unfinished']} video(s) of {j['lastRunDay']} stopped before the gauntlet", "python -m faceless daily --no-publish (it resumes)", "state/jobs", daily)
    if ph:
        if ph["runnable"] and ph["device"]["attached"] is False:
            add("warn", f"{ph['runnable']} phone job(s) can run but {ph['device']['note']}",
                "Phone: Wireless debugging on, same Wi-Fi, then adb connect <ip>:<port> (tools/phone-setup/TEST.md step 1)", "adb devices")
        elif ph["mediaMissing"]:
            add("warn", f"{ph['mediaMissing']} of {ph['runnable']} runnable phone job(s) have no media left (the media branch keeps 3 days; the videos are not on this disk)"
                + ("; one of them is at the head, so the lane is jammed" if ph["nextMediaMissing"] else ""),
                "python -m faceless phone park (holds them with the reason; Release brings one back after a re-stage)", "state/phone/jobs, origin/phone-media",
                {"name": "phone_park", "args": {}, "label": "Park jobs with no media"})
        elif ph["next"]:
            add("warn", f"{ph['runnable']} phone job(s) wait; next is {ph['next']['id']}", "python -m faceless phone next --push", "state/phone/jobs",
                {"name": "phone_next", "args": {}, "label": "Advance phone"})
        if ph["heldCount"]:
            add("info", f"{ph['heldCount']} phone job(s) are held after two failures", "Jobs tab: Release (python -m faceless phone requeue <id>)", "state/phone/jobs", tab="jobs")
    elif j is not None and j["tiktokQueued"]:
        add("warn", f"{j['tiktokQueued']} TikTok posts wait in the phone queue", "python -m faceless phone next --push", "state/phone/jobs",
            {"name": "phone_next", "args": {}, "label": "Advance phone"})
    if sp.get("ceilingUsd") and sp.get("todayUsd", 0) >= 0.8 * sp["ceilingUsd"]:
        add("warn", f"Spend today ${sp['todayUsd']:.2f} of the ${sp['ceilingUsd']:.2f} ceiling", "A refusal is the system working; raising a cap is yours", "state/ledger.jsonl")
    if ob and ob.get("followUpsDue"):
        add("warn", f"{ob['followUpsDue']} DM follow-up(s) are due", "DMs tab: send the follow-up, then press its button", "state/outbound.jsonl", tab="dms")
    if of and of["built"] > of["live"]:
        waiting = [i["id"] for i in of["items"] if not i["live"]]
        add("info", f"Built but not listed: {', '.join(waiting)}", f"Say the price in chat: list {waiting[0]} at $<price>", "channel/shop/catalog.json")
    if not (config.load().get("newsletter") or {}).get("form_action"):
        add("info", "The hub gives the checklist away without collecting an email", "Pick an email service; its form address goes in studio.toml [newsletter] form_action", "studio.toml")
    return out


def build(today: str | None = None) -> dict:
    from faceless import actions, agents, dmdesk, hermes, models, moneybrief, offer, receipts
    today = today or config.today_utc().isoformat()
    cash = receipts.summary(today)
    doc = {
        "generatedAt": _now(), "day": today, "staleAfterHours": STALE_HOURS, "source": source(),
        "jobs": jobs(today),
        "phone": phone_lane(),
        "outbound": dmdesk.funnel(today),
        "dms": dm_batches(today),
        "followUps": dmdesk.follow_ups(today),
        "cash": {"revenueMTD": cash["revenueMTD"], "netMTD": cash["netMTD"], "receipts": cash["receipts"], "receiptsAllTime": cash["receiptsAllTime"],
                 "byRail": cash["byRail"], "note": cash["note"], "sources": cash["sources"], "source": cash["source"]},
        "offers": offers(),
        "money": {"actions": moneybrief.actions(today)[:3], "brief": f"outbound/brief/{today}.md" if (moneybrief.DIR / f"{today}.md").exists() else None,
                  "source": "faceless/moneybrief.py (the money desk, state/outbound.jsonl, studio.toml)"},
        "spend": spend(),
        "serviceDesk": service_desk(),
        "hermes": hermes.build(),
        "agents": agents.build(),
        "models": models.build(),
        "links": {"hub": offer.hub_url()},
        "activity": actions.recent(8),                       # the newest clicks on this page, from the journal
    }
    doc["targets"] = targets(doc)                            # studio.toml holds no revenue or audience target, so none is drawn
    doc["alerts"] = alerts(doc)
    from faceless import missions
    try:
        from faceless import prospects
        doc["prospects"] = prospects.board_state()           # people waiting in the drop folder; local files only
    except Exception:   # noqa: BLE001 - a damaged drop file must not blank the board
        doc["prospects"] = None
    doc["missions"] = missions.board(doc)                    # the work board: derived to-do, who has what, done today
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
    from faceless import agents, hermes, models
    L.append(agents.summary(doc.get("agents")))
    L.append(models.summary(doc.get("models")))
    L.append(hermes.summary(doc.get("hermes")))
    L += [f"Alerts: {len(doc['alerts'])}"] + [f"  [{a['level']}] {a['text']} -> {a['fix']}" for a in doc["alerts"]]
    return "\n".join(L)
