"""The marketing director: reads the whole funnel and writes one weekly brief, within the guard rails of channel/empire/MARKETING.md section 8.

It reads and reports; it never posts, prices, discounts, messages a person or spends beyond a desk cap. What it does each run:
  * guard checks: the 5-a-day floor (G1), spend against the ceiling and the weekly alarm (G3), keys present (G8), the kill switch;
  * the funnel: videos with an offer, hub and profile links, the planner's live state, sales and the net against the $100 balance gate;
  * measurement coverage (48-hour and 7-day snapshots) and median 48-hour views by pillar;
  * the experiment register (channel/empire/experiments.json): which are runnable, blocked (and by what), running, won or killed;
  * the owner's queue: at most three open decisions (G10), each with its default of status quo.
`python -m faceless marketing` prints and writes analytics/brief-<day>.md. `marketing done U01` closes a queue item; `marketing start X1` / `marketing result X1 won|killed "note"`
move an experiment. Nothing here changes a price, a listing or a post.
"""

from __future__ import annotations

import json
from datetime import timedelta

from faceless import config, ledger, offer, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

REGISTER = Paths.root / "channel" / "empire" / "experiments.json"
QUEUE = Paths.root / "channel" / "empire" / "owner_queue.json"
SALES = Paths.analytics / "sales.jsonl"
GATE_USD = 100.0                                    # Gumroad payout and Discover balance
MARKETING_PROVIDERS = ("monid", "openrouter-panel", "openrouter-decisions", "openrouter-aeo")
WEEKLY_ALARM_USD = 1.00                             # recurring model and data calls; above it the marketing desks go read-only (G3)
KEYS = {"OPENROUTER_API_KEY": "Haiku, Jev, the panel and the AEO probe", "MONID_API_KEY": "the Monid data desk"}
STATUSES = ("planned", "running", "won", "killed")


def net_per_sale(price: float) -> float:
    """What the seller keeps from a direct Gumroad card sale: 10% + $0.50 Gumroad fee plus about 2.9% + $0.30 card processing (MARKETING.md, gum:F01)."""
    return round(price - (0.129 * price + 0.80), 2)


def _load(path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path, data: dict) -> None:
    write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- guards

def scheduled_today(day: str | None = None) -> int:
    from faceless.state import all_jobs
    want = day or config.today_utc().isoformat()
    return sum(1 for j in all_jobs() if j.day == want and (j.artifacts.get("youtube") or {}).get("video_id"))


def week_spend() -> float:
    today = config.today_utc()
    return round(sum(ledger.used_usd(p, (today - timedelta(days=d)).isoformat()) + ledger.used(p, "desk_usd", (today - timedelta(days=d)).isoformat())
                     for p in MARKETING_PROVIDERS for d in range(7)), 4)


def guards(env=None) -> list[dict]:
    """[{id, state ok|warn|stop, text}] for G1, G3, G8 and the kill switch."""
    out = []
    if (why := safety.paused()):
        out.append({"id": "pause", "state": "stop", "text": f"state/PAUSE is set: {why}. Only the owner resumes it."})
    n = scheduled_today()
    out.append({"id": "G1", "state": "ok" if n >= 5 else "warn", "text": f"{n} of 5 Shorts scheduled for today" + ("" if n >= 5 else " (run post-backlog --apply; rule 15)")})
    spent, ceiling = ledger.usd_total(), safety.ceiling()
    week = week_spend()
    state = "stop" if spent >= ceiling else "warn" if week >= WEEKLY_ALARM_USD or safety.headroom() < 0.5 else "ok"
    out.append({"id": "G3", "state": state, "text": f"${spent:.2f} spent today of the ${ceiling:.2f} ceiling; marketing desks ${week:.3f} this week (alarm ${WEEKLY_ALARM_USD:.2f}); headroom ${safety.headroom():.2f}"
                + ("; marketing desks are read-only" if state != "ok" else "")})
    missing = [k for k in KEYS if not config.env(k)]
    out.append({"id": "G8", "state": "warn" if missing else "ok",
                "text": "keys present" if not missing else "degraded, missing: " + ", ".join(f"{k} ({KEYS[k]})" for k in missing)})
    return out


# ---------------------------------------------------------------- funnel

def sales_summary() -> dict:
    rows = [r for r in read_jsonl(SALES) if not r.get("refunded")]
    gross = sum(float(r.get("usd") or 0) for r in rows)
    net = sum(net_per_sale(float(r.get("usd") or 0)) for r in rows if float(r.get("usd") or 0) > 0)
    return {"sales": len(rows), "gross": round(gross, 2), "net_estimate": round(net, 2), "to_gate": round(max(0.0, GATE_USD - net), 2)}


def funnel() -> dict:
    from faceless import metrics
    from faceless.state import all_jobs
    st = offer.status()
    jobs = [j.id for j in all_jobs() if (j.artifacts.get("youtube") or {}).get("video_id")]
    snaps = read_jsonl(metrics.SNAPSHOTS)
    return {"offers": st, "planner_live": "daily-quiet-money-planner" in (config.load().get("offer", {}).get("shop_urls") or {}),
            "newsletter_form": bool((config.load().get("newsletter") or {}).get("form_action")), "sales": sales_summary(),
            "coverage": metrics.coverage(jobs, snaps), "scheduled_videos": len(jobs), "by_pillar": metrics.summary()}


# ---------------------------------------------------------------- experiments

def blockers(exp_id: str, f: dict) -> str | None:
    """Why an experiment cannot run yet, from facts the engine can read; None means runnable."""
    planner = None if f["planner_live"] else "the planner is not live (no URL in [offer] shop_urls)"
    need = {"X0": planner, "X1": planner, "X2": planner, "X9": planner, "X11": planner,
            "X3": None if f["newsletter_form"] else "no email form action in [newsletter]",
            "X4": None if f["coverage"].get(48, 0) >= 20 else f"only {f['coverage'].get(48, 0)} videos have a 48-hour snapshot (needs about 20 per arm)",
            "X7": "needs the owner's Etsy approval and ETSY_API_KEY", "X8": planner or "needs the owner's affiliate terms and pitches",
            "X5": "owner TikTok and Reels posting (owner-gated)", "X6": "needs the owner-approved Start Here video",
            "X10": "needs 50 labelled outcomes before Jev's score can be compared with views"}
    return need.get(exp_id)


def experiments(f: dict | None = None) -> list[dict]:
    f = f or funnel()
    reg = _load(REGISTER).get("experiments", [])
    out = []
    for e in reg:
        why = blockers(e["id"], f) if e.get("status") == "planned" else None
        out.append({"id": e["id"], "status": e.get("status", "planned"), "hypothesis": e["hypothesis"][:140], "autonomy": e["autonomy"], "blocked_by": why})
    return out


def set_experiment(exp_id: str, status: str, note: str = "") -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    reg = _load(REGISTER)
    for e in reg.get("experiments", []):
        if e["id"] == exp_id:
            e["status"] = status
            if status == "running":
                e["started"] = config.today_utc().isoformat()
            if note:
                e["result"] = note
            _save(REGISTER, reg)
            return e
    raise KeyError(f"no experiment {exp_id}")


# ---------------------------------------------------------------- owner queue (G10)

def owner_queue(limit: int = 3) -> list[dict]:
    return [i for i in _load(QUEUE).get("items", []) if i.get("status") == "open"][:limit]


def mark_done(item_id: str) -> dict:
    q = _load(QUEUE)
    for i in q.get("items", []):
        if i["id"] == item_id:
            i["status"] = "done"
            _save(QUEUE, q)
            return i
    raise KeyError(f"no queue item {item_id}")


# ---------------------------------------------------------------- the brief

def brief() -> str:
    f = funnel()
    g = guards()
    exps = experiments(f)
    day = config.today_utc().isoformat()
    s = f["sales"]
    lines = [f"# Marketing brief, {day}", "", "Reads only. Nothing here changes a price, a listing, a post or a message. Strategy: `channel/empire/MARKETING.md`.", "", "## Guards"]
    lines += [f"- **{x['id']}** {x['state'].upper()}: {x['text']}" for x in g]
    o = f["offers"]
    lines += ["", "## Funnel",
              f"- Offers: {o['videos']} videos in the last window, {o['draft']} waiting to be pinned, {o['pinned']} pinned, paid live: {', '.join(o['paid_live']) or 'none'}",
              f"- Planner live: {'yes' if f['planner_live'] else 'no'}; email form: {'on' if f['newsletter_form'] else 'off'}",
              f"- Sales: {s['sales']} (${s['gross']:.2f} gross, about ${s['net_estimate']:.2f} net; ${s['to_gate']:.2f} net still to the $100 balance gate; a direct sale at $17 nets ${net_per_sale(17):.2f})",
              f"- Measurement: {f['scheduled_videos']} scheduled videos; 48-hour snapshots {f['coverage'].get(48, 0)}, 7-day snapshots {f['coverage'].get(168, 0)}"]
    if f["by_pillar"]:
        lines.append("- Median 48-hour views by pillar: " + ", ".join(f"{p} {v['median_views']:.0f} (n={v['n']})" for p, v in f["by_pillar"].items()))
    lines += ["", "## Experiments"]
    for e in exps:
        tail = f" (blocked: {e['blocked_by']})" if e["blocked_by"] else " (runnable)" if e["status"] == "planned" else ""
        lines.append(f"- {e['id']} {e['status']}{tail}: {e['hypothesis']}")
    q = owner_queue()
    lines += ["", "## Owner queue (at most three; silence for seven days means status quo, never approval)"]
    lines += [f"{n}. [{i['id']}] {i['ask'][:400]}" for n, i in enumerate(q, 1)] or ["- nothing open"]
    return "\n".join(lines) + "\n"


def write_brief() -> str:
    text = brief()
    path = Paths.analytics / f"brief-{config.today_utc().isoformat()}.md"
    write_atomic(path, text)
    return text
