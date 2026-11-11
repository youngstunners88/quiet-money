"""The daily money brief: three things the owner can do in fifteen minutes each, today's DMs, the follow-ups that are due, what changed
since yesterday, and what could not be done and why. `python -m faceless money` writes `outbound/brief/<day>.md` and
`channel/empire/INCOME-RAILS.md`; the command center's Money tab shows the three actions.

Everything is read from the engine's own state (the money desk, the DM log, receipts, jobs, the phone lane). The order of the actions
is a judgment about distance to cash and says so; no amount is forecast, because no rail has sold anything yet and a guess printed
next to real numbers reads as one of them. Nothing here sends, lists, prices or posts.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from faceless import config
from faceless.config import Paths
from faceless.fsutil import write_atomic

DIR = Paths.root / "outbound" / "brief"
RAILS_MD = Paths.root / "channel" / "empire" / "INCOME-RAILS.md"
MAX_MINUTES = 15


def _catalog() -> dict:
    """The shop catalog by product id, each entry as written (name, price, price_test)."""
    import json
    try:
        data = json.loads((Paths.root / "channel" / "shop" / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {p["id"]: p for p in data.get("products", []) if isinstance(p, dict) and p.get("id")}


def actions(today: str | None = None) -> list[dict]:
    """Owner steps of fifteen minutes or less, nearest to a first sale first. Each names where its fact came from."""
    from faceless import cash, dmdesk, receipts
    today = today or config.today_utc().isoformat()
    cfg = config.load()
    live = (cfg.get("offer") or {}).get("shop_urls") or {}
    out = []
    due = dmdesk.follow_ups(today)
    if due:
        out.append({"title": f"Send {len(due)} follow-up{'s' if len(due) != 1 else ''} that are due", "minutes": min(MAX_MINUTES, 2 * len(due)),
                    "how": "Each is in the drafts file of the day it was written: " + ", ".join(f"{d['draft_id']} ({d['send'].replace('_', ' ')})" for d in due[:8])
                           + ". A reply moves it on: `python -m faceless dm log <id> replied`; after follow-up 3 with no reply: `dm log <id> dead`.",
                    "why": "a person who already heard from you is the shortest path to a reply", "source": "state/outbound.jsonl"})
    batch = dmdesk.todays(today)
    if batch and batch.get("drafts"):
        n = min(5, len(batch["drafts"]))
        name = f"{today}.private.md" if batch.get("private") else f"{today}.md"
        out.append({"title": f"Fill in and send {n} of today's {len(batch['drafts'])} DMs", "minutes": MAX_MINUTES,
                    "how": f"Open outbound/drafts/{name}. For each, pick one person who fits the stated reason, replace the slots with their own words, send it by hand, "
                           "then run the log line under it. Skip any you cannot make personal.",
                    "why": "the only rail where today's work can produce a conversation today", "source": f"outbound/drafts/{name}"})
    waiting = [p for pid, p in _catalog().items() if pid not in live]
    if waiting:
        p = waiting[0]
        out.append({"title": f"Say the price for {p.get('name', p['id'])}", "minutes": 2,
                    "how": f"Reply in chat with one line: \"list {p['id']} at ${p.get('price')}\" (the catalog's test prices are "
                           f"{', '.join('$' + str(x) for x in p.get('price_test') or [p.get('price')])}). The listing pack is built; publishing follows your yes.",
                    "why": "a built product with no listing cannot sell", "source": "channel/shop/catalog.json, studio.toml [offer] shop_urls"})
    if live and not receipts.rows():
        out.append({"title": "Check Gumroad for sales and record any", "minutes": 3,
                    "how": "Open Gumroad > Sales. For each real sale: `python -m faceless receipts add --rail gumroad --gross <amount> --product <id> --ref <order number>`. "
                           "No sale yet is a real answer too: it stays $0.",
                    "why": f"{len(live)} listings are live and this checkout has no Gumroad read connection, so sales here are only what you record",
                    "source": "state/receipts.jsonl, analytics/sales.jsonl"})
    if not (cfg.get("newsletter") or {}).get("form_action"):
        out.append({"title": "Pick the email service so the free checklist can collect an address", "minutes": MAX_MINUTES,
                    "how": "Create a free account with an email service, copy its public form address, and send it in chat; it goes in studio.toml "
                           "[newsletter] form_action and the hub and checklist pages then show the signup form.",
                    "why": "the hub page gives the checklist away without asking for an email, so no list is being built",
                    "source": "studio.toml [newsletter] form_action"})
    for r in cash.desk()["rails"]:
        if r.get("kind") == "gig" and r.get("state") == "ready":
            folder = "brand-kit" if r.get("id") == "S1" else "studio"
            out.append({"title": f"Start the {r['rail']} listing", "minutes": MAX_MINUTES,
                        "how": f"On Fiverr, create a gig and paste the title, category and description from channel/services/{folder}/GIG.md. Save as draft; "
                               "the tiers and pictures are the second fifteen minutes.",
                        "why": "the gig copy and samples are built; a marketplace brings its own buyers", "source": f"channel/services/{folder}/GIG.md"})
            break
    return out


def changes(today: str | None = None) -> dict:
    """What moved between yesterday and today, counted from dated records only."""
    from faceless import dmdesk, phone, receipts
    from faceless.state import all_jobs
    today = today or config.today_utc().isoformat()
    yday = (datetime.fromisoformat(today) - timedelta(days=1)).date().isoformat()
    jobs = all_jobs()

    def day(d: str) -> dict:
        mine = [j for j in jobs if j.day == d and not j.id.startswith("host-")]
        posts = [r for r in phone.receipts() if str(r.get("at") or "")[:10] == d and r.get("result") == "posted"]
        dm = [r for r in dmdesk.rows() if str(r.get("t") or "")[:10] == d]
        rec = [r for r in receipts.rows() if r["day"] == d]
        return {"videosMade": len(mine), "passed": sum(1 for j in mine if j.status in ("published", "packaged") and (j.scores or {}).get("passed")),
                "held": sum(1 for j in mine if j.status == "held"), "failed": sum(1 for j in mine if j.status == "failed"),
                "postedByPhone": len(posts), "postedTikTok": sum(1 for r in posts if r.get("kind") == "tiktok"),
                "dmsDrafted": sum(1 for r in dm if r.get("status") == "drafted"), "dmsSent": sum(1 for r in dm if r.get("status") == "sent"),
                "replies": sum(1 for r in dm if r.get("status") == "replied"), "clicks": sum(1 for r in dm if r.get("status") == "clicked"),
                "receipts": len(rec), "revenue": round(sum(r["gross"] for r in rec), 2)}
    return {"today": day(today), "yesterday": day(yday), "days": [yday, today],
            "source": "state/jobs, state/phone/receipts.jsonl, state/outbound.jsonl, state/receipts.jsonl"}


def could_not(today: str | None = None) -> list[str]:
    """What stands between the agent and the work, each read from a setting or a state file."""
    from faceless import phone, shop
    cfg = config.load()
    out = []
    if not shop.token_present():
        out.append("Pull Gumroad sales: no Gumroad read token in this environment, so revenue is only what is recorded in state/receipts.jsonl.")
    if not (cfg.get("newsletter") or {}).get("form_action"):
        out.append("Collect emails or send the weekly issue: studio.toml [newsletter] form_action and postal_address are empty.")
    try:
        from faceless import etsy
        if etsy.status()["state"] != "ready":
            out.append("Create Etsy drafts: the Etsy rail is not connected (the listing packs are built).")
    except Exception:   # noqa: BLE001 - a status read must never stop the brief
        pass
    try:
        queued = sum(1 for j in phone.jobs() if j.get("kind") == "tiktok" and j.get("status", "queued") == "queued")
        if queued:
            out.append(f"Post to TikTok: {queued} TikTok posts are queued for the phone lane and wait for the phone host on your computer.")
    except Exception:   # noqa: BLE001
        pass
    out.append("Send any message, list a product, set a price or post anywhere new: those are yours by rule 9; the drafts and packs are ready.")
    return out


def rails() -> list[dict]:
    """Every income rail by distance to cash: its artifact, what blocks it, the owner's step and its kill rule. 'First dollar' stays unknown
    until a receipt exists on that rail; a date printed here would be invented."""
    from faceless import dmdesk, receipts
    cfg = config.load()
    live = (cfg.get("offer") or {}).get("shop_urls") or {}
    cat = _catalog()
    by = receipts.summary()["byRail"]
    waiting = [pid for pid in cat if pid not in live]
    f = dmdesk.funnel() or {}

    def first(rail: str) -> str:
        return f"earned ${by[rail]['gross']:.2f} this month" if rail in by else "unknown: no receipt on this rail yet"
    return [
        {"rail": "1. Paid products on Gumroad", "artifact": "channel/shop/*/gumroad/, studio.toml [offer] shop_urls",
         "blocker": (f"{len(live)} listings live; not listed: {', '.join(waiting)}" if waiting else f"{len(live)} listings live") + "; traffic to them is the open question",
         "owner": f"say the price for {waiting[0]}" if waiting else "none", "first": first("gumroad"),
         "kill": "zero sales after 200 listing views, or refunds above 10% (PLAN.md)"},
        {"rail": "2. Warm DM > free checklist > list", "artifact": "outbound/drafts/, state/outbound.jsonl, the hub page",
         "blocker": ("no email form on the hub: the checklist is given without an address" if not (cfg.get("newsletter") or {}).get("form_action") else "none")
                    + f"; {f.get('sent', 0)} DMs sent so far",
         "owner": "send today's DMs by hand; pick an email service", "first": "unknown: a list earns only through a later product sale",
         "kill": "no reply in 30 personal sends, or under 1 signup per 1,000 views after 60 days"},
        {"rail": "3. Fiverr brand-kit gig", "artifact": "channel/services/brand-kit/GIG.md, gallery/, samples/",
         "blocker": "the gig is not published on Fiverr (owner's account)", "owner": "create the gig and paste GIG.md", "first": first("fiverr"),
         "kill": "fewer than 1 order in 30 days of an active gig (PLAN.md)"},
        {"rail": "4. Affiliates", "artifact": "channel/monetization.md (programs named, none joined)",
         "blocker": "no affiliate program joined and no link exists; [channel] has_affiliate_links stays false until one does",
         "owner": "name one tool you actually use and can recommend honestly; join its program", "first": first("affiliate"),
         "kill": "no click in 60 days after the first link is on the hub"},
        {"rail": "5. Etsy printables", "artifact": "channel/shop/money-reset-printables/etsy/, CHECKLIST.md",
         "blocker": "no Etsy listing; the rail is not connected", "owner": "follow CHECKLIST.md by hand (about 15 minutes) or connect the Etsy rail",
         "first": first("etsy"), "kill": "rejected twice for the same reason, or zero sales after 200 views"},
        {"rail": "6. Email: 7-day sequence and weekly issue", "artifact": "channel/offers/autoresponder/, `python -m faceless kit --issue`",
         "blocker": "no email service, no form address, no postal address: the issue is marked NOT SENDABLE", "owner": "pick the service; give a postal address",
         "first": "unknown: email earns only through a product sale", "kill": "under 1 signup per 1,000 views after 60 days (PLAN.md)"},
    ]


def rails_markdown(rows: list[dict], day: str) -> str:
    L = [f"# Income rails by distance to cash ({day})", "",
         "Written by `python -m faceless money` from the engine's state. No projection is printed: 'first dollar' is unknown until a rail has a receipt in "
         "`state/receipts.jsonl` or `analytics/sales.jsonl`. Views, clicks and replies are not income.", "",
         "| rail | artifact | blocker | owner action | first dollar | kill rule |", "|---|---|---|---|---|---|"]
    L += [f"| {r['rail']} | {r['artifact']} | {r['blocker']} | {r['owner']} | {r['first']} | {r['kill']} |" for r in rows]
    return "\n".join(L) + "\n"


def brief(today: str | None = None) -> dict:
    from faceless import dmdesk, receipts
    today = today or config.today_utc().isoformat()
    batch = dmdesk.todays(today)
    return {"day": today, "actions": actions(today)[:3], "dms": {"count": len((batch or {}).get("drafts") or []),
            "path": (f"outbound/drafts/{today}{'.private' if (batch or {}).get('private') else ''}.md" if batch else None)},
            "followUps": dmdesk.follow_ups(today), "changes": changes(today), "couldNot": could_not(today), "cash": receipts.summary(today),
            "funnel": dmdesk.weekly(today), "rails": rails()}


def markdown(b: dict) -> str:
    c, y, t = b["cash"], b["changes"]["yesterday"], b["changes"]["today"]
    L = [f"# Money brief ({b['day']})", "",
         f"Revenue this month: ${c['revenueMTD']:.2f} from {c['receipts']} receipts" + (f" ({c['note']})" if c["note"] else "") + ". "
         "A number is here only when a receipt exists.", "", "## Three things, fifteen minutes each or less", "",
         "Ordered by how close each is to a first sale. That order is a judgment; no rail has sold yet, so nothing here is a forecast.", ""]
    for i, a in enumerate(b["actions"], 1):
        L += [f"{i}. **{a['title']}** (about {a['minutes']} min). {a['how']}", f"   Why: {a['why']}. Source: {a['source']}.", ""]
    if not b["actions"]:
        L += ["Nothing is waiting on you today.", ""]
    L += ["## Today's DMs", "", (f"{b['dms']['count']} drafts: `{b['dms']['path']}`. You send them by hand." if b["dms"]["path"]
                                 else "No drafts yet today: run `python -m faceless dm`."), "", "## Follow-ups due", ""]
    L += [f"- {d['draft_id']}: sent {d['days_since_sent']} days ago, send {d['send'].replace('_', ' ')}" for d in b["followUps"]] or ["None. Nothing is marked sent three or more days ago."]
    L += ["", "## Since yesterday", "", f"| | {b['changes']['days'][0]} | {b['changes']['days'][1]} |", "|---|---|---|"]
    for key, label in (("videosMade", "videos made"), ("passed", "passed the gauntlet"), ("held", "held"), ("failed", "failed"), ("postedTikTok", "posted on TikTok (phone lane)"),
                       ("dmsDrafted", "DMs drafted"), ("dmsSent", "DMs sent"), ("replies", "replies"), ("clicks", "clicks"), ("receipts", "receipts")):
        L.append(f"| {label} | {y[key]} | {t[key]} |")
    L += [f"| revenue | ${y['revenue']:.2f} | ${t['revenue']:.2f} |", "", f"DM funnel so far: {b['funnel']['sent']} sent, {b['funnel']['replied']} replied, "
          f"{b['funnel']['clicked']} clicked, {b['funnel']['bought']} bought. Verdict: {b['funnel']['verdict']}.", "", "## What could not be done, and why", ""]
    L += [f"- {x}" for x in b["couldNot"]]
    L += ["", "Every rail with its blocker and kill rule: `channel/empire/INCOME-RAILS.md`."]
    return "\n".join(L) + "\n"


def write(today: str | None = None) -> dict:
    b = brief(today)
    write_atomic(DIR / f"{b['day']}.md", markdown(b))
    write_atomic(RAILS_MD, rails_markdown(b["rails"], b["day"]))
    return b
